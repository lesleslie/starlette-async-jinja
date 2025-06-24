import typing as t
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anyio import Path as AsyncPath
from jinja2.environment import Template
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette_async_jinja.responses import AsyncJinja2Templates


class MockFileSystem:
    """Mock file system for testing."""

    def __init__(self) -> None:
        self._files: dict[str, bytes] = {}

    def add_file(self, path: str, content: str) -> None:
        """Add a file to the mock file system."""
        self._files[path] = content.encode()

    async def read_bytes(self, path: str) -> bytes:
        """Read a file from the mock file system."""
        return self._files.get(path, b"")

    async def exists(self) -> bool:
        """Check if the path exists."""
        return True

    async def is_dir(self) -> bool:
        """Check if the path is a directory."""
        return True

    async def iterdir(self) -> t.AsyncIterator[AsyncPath]:
        """Iterate over the directory."""
        yield AsyncPath("mock_path")


@pytest.fixture
def mock_template() -> MagicMock:
    """Create a mock template."""
    template = MagicMock(spec=Template)
    template.render_async = AsyncMock(return_value="<h1>Mocked Content</h1>")
    template.blocks = {"test_block": MagicMock()}
    template.new_context = MagicMock(return_value={})
    return template


@pytest.fixture
def templates(mock_template: MagicMock) -> AsyncJinja2Templates:
    """Create AsyncJinja2Templates instance with mocked internals."""
    # Create a mock directory
    mock_dir = AsyncPath("templates")

    # Create templates with the mock directory
    templates = AsyncJinja2Templates(directory=mock_dir)

    # Patch the get_template_async method to return our mock template
    templates.get_template_async = AsyncMock(return_value=mock_template)

    return templates


@pytest.fixture
def app(templates: AsyncJinja2Templates) -> Starlette:
    """Create a Starlette application with template routes."""

    async def homepage(request: t.Any) -> t.Any:
        return await templates.TemplateResponse(
            request, "test.html", {"title": "Test Title"}
        )

    async def block_page(request: t.Any) -> t.Any:
        return await templates.TemplateResponse(request, "with_block.html", {})

    async def render_block(request: t.Any) -> t.Any:
        # Mock the render_fragment method to return a known string
        with patch.object(
            templates, "render_fragment", AsyncMock(return_value="This is a test block")
        ):
            block_content = await templates.render_fragment(
                "with_block.html", "test_block"
            )
            return await templates.TemplateResponse(
                request,
                "test.html",
                {"title": "Block Content", "content": block_content},
            )

    routes = [
        Route("/", homepage),
        Route("/block", block_page),
        Route("/render-block", render_block),
    ]

    return Starlette(routes=routes)


@pytest.fixture
def client(app: Starlette) -> TestClient:
    """Create a test client for the application."""
    return TestClient(app)
