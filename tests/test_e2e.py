import typing as t
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient
from starlette_async_jinja.responses import AsyncJinja2Templates, BlockNotFoundError


@pytest.mark.asyncio
async def test_template_rendering(client: TestClient, mock_template: MagicMock) -> None:
    """Test that templates are rendered correctly."""
    # Set the expected content for this test
    mock_template.render_async.return_value = "<h1>Test Title</h1>"

    # Make the request
    response = client.get("/")

    # Verify the response
    assert response.status_code == 200
    assert "<h1>Test Title</h1>" in response.text
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_block_rendering(client: TestClient, mock_template: MagicMock) -> None:
    """Test that template blocks are rendered correctly."""
    # Set the expected content for this test
    mock_template.render_async.return_value = (
        "<html><body>This is a test block</body></html>"
    )

    # Make the request
    response = client.get("/block")

    # Verify the response
    assert response.status_code == 200
    assert "This is a test block" in response.text
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_fragment_rendering(client: TestClient, mock_template: MagicMock) -> None:
    """Test that template fragments can be rendered and included in other templates."""
    # Set the expected content for this test
    mock_template.render_async.return_value = (
        "<h1>Block Content</h1>This is a test block"
    )

    # Make the request
    response = client.get("/render-block")

    # Verify the response
    assert response.status_code == 200
    assert "<h1>Block Content</h1>" in response.text
    assert "This is a test block" in response.text
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_error_handling(mock_template: MagicMock) -> None:
    """Test error handling in template rendering."""
    from anyio import Path as AsyncPath
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.testclient import TestClient

    # Create templates with mocked methods for error testing
    templates = AsyncJinja2Templates(directory=AsyncPath("templates"))

    # Mock get_template_async to raise an exception for nonexistent template
    templates.get_template_async = AsyncMock(
        side_effect=lambda name: mock_template
        if name == "test.html"
        else RuntimeError(f"Template '{name}' not found")
    )

    # Mock render_fragment to raise BlockNotFoundError for nonexistent block
    async def mock_render_fragment(
        template_name: str, block_name: str, **kwargs: dict[str, t.Any]
    ) -> str:
        if block_name == "nonexistent_block":
            raise BlockNotFoundError(block_name, template_name)
        return "This is a test block"

    templates.render_fragment = AsyncMock(side_effect=mock_render_fragment)

    # Create routes with error cases
    async def nonexistent_template(request: t.Any) -> t.Any:
        # This should raise a RuntimeError
        return await templates.TemplateResponse(
            request, "nonexistent.html", {"title": "Test Title"}
        )

    async def nonexistent_block(request: t.Any) -> t.Any:
        # This should raise a BlockNotFoundError
        try:
            block_content = await templates.render_fragment(
                "with_block.html", "nonexistent_block"
            )
            return await templates.TemplateResponse(
                request,
                "test.html",
                {"title": "Block Content", "content": block_content},
            )
        except BlockNotFoundError as e:
            mock_template.render_async.return_value = f"<h1>Error: {e}</h1>"
            return await templates.TemplateResponse(
                request, "test.html", {"title": f"Error: {e}"}
            )

    routes = [
        Route("/nonexistent", nonexistent_template),
        Route("/nonexistent-block", nonexistent_block),
    ]

    app = Starlette(routes=routes)
    client = TestClient(app)

    # Test nonexistent template
    with pytest.raises(RuntimeError):
        client.get("/nonexistent")

    # Test nonexistent block - this should be handled and return a valid response
    response = client.get("/nonexistent-block")
    assert response.status_code == 200
    assert "Error:" in response.text
    assert "Block 'nonexistent_block' not found" in response.text
