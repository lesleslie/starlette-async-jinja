import typing as t
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anyio import Path as AsyncPath
from jinja2.environment import Template
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.testclient import TestClient
from starlette_async_jinja.responses import AsyncJinja2Templates, JsonResponse


class MockAsyncJinja2Templates(AsyncJinja2Templates):
    """A version of AsyncJinja2Templates with mocked methods."""

    def __init__(
        self,
        directory,
        mock_get_template_func=None,
        mock_render_fragment_func=None,
        **kwargs,
    ):
        super().__init__(directory, **kwargs)
        self._mock_get_template_func = mock_get_template_func
        self._mock_render_fragment_func = mock_render_fragment_func

    async def get_template_async(self, name: str):
        if self._mock_get_template_func:
            result = self._mock_get_template_func(name)
            # If the result is a coroutine, await it, otherwise return as-is
            if hasattr(result, "__await__"):
                return await result
            return result
        return await super().get_template_async(name)

    async def render_fragment(self, template_name: str, block_name: str, **kwargs):
        if self._mock_render_fragment_func:
            result = self._mock_render_fragment_func(
                template_name, block_name, **kwargs
            )
            # If the result is a coroutine, await it, otherwise return as-is
            if hasattr(result, "__await__"):
                return await result
            return result
        return await super().render_fragment(template_name, block_name, **kwargs)


@pytest.mark.asyncio
async def test_full_application_integration() -> None:
    """Test integration with a full Starlette application using mocks."""
    # Create mock templates
    mock_home_template = MagicMock(spec=Template)
    mock_home_template.render_async = AsyncMock(
        return_value="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Home Page</title>
        </head>
        <body>
            <header>
                <h1>Test Application</h1>
                <nav>
                    <a href="http://testserver/">Home</a>
                    <a href="http://testserver/api/data">API</a>
                </nav>
            </header>
            <main>
                <h2>Welcome to the Test Application</h2>
                <p>This is a test of the AsyncJinja2Templates.</p>

                <div id="dynamic-content">
                    <div class="user-info">
                        <h3>User Information</h3>
                        <p>Username: testuser</p>
                        <p>Email: test@example.com</p>
                    </div>
                </div>
            </main>
            <footer>
                &copy; 2023 Test Application
            </footer>
        </body>
        </html>
    """
    )

    # Create context processor
    def context_processor(request: Request) -> dict[str, t.Any]:
        return {
            "app_name": "Test Application",
            "version": "1.0.0",
        }

    # Create templates with mocked methods using our mock class
    def mock_get_template_func(name: str):
        return mock_home_template

    async def mock_render_fragment_func(template_name: str, block_name: str, **kwargs):
        return (
            """<div class="product-info">
            <h3>Test Product</h3>
            <p>Price: $99.99</p>
            <p>Description: This is a test product</p>
        </div>"""
            if block_name == "product_info"
            else """<div class="user-info">
            <h3>User Information</h3>
            <p>Username: testuser</p>
            <p>Email: test@example.com</p>
        </div>"""
            if block_name == "user_info"
            else "Unknown block"
        )

    MockAsyncJinja2Templates(
        directory=AsyncPath("templates"),
        mock_get_template_func=mock_get_template_func,
        mock_render_fragment_func=mock_render_fragment_func,
    )

    # Create templates with context processor
    templates_with_processor = MockAsyncJinja2Templates(
        directory=AsyncPath("templates"),
        context_processors=[context_processor],
        mock_get_template_func=mock_get_template_func,
        mock_render_fragment_func=mock_render_fragment_func,
    )

    # Create routes
    async def homepage(request: Request) -> t.Any:
        user = {"username": "testuser", "email": "test@example.com"}
        return await templates_with_processor.TemplateResponse(
            request, "home.html", {"user": user}
        )

    async def get_data(request: Request) -> t.Any:
        data = {
            "items": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
                {"id": 3, "name": "Item 3"},
            ]
        }
        return JsonResponse(data)

    async def get_fragment(request: Request) -> t.Any:
        product = {
            "name": "Test Product",
            "price": 99.99,
            "description": "This is a test product",
        }
        fragment = await templates_with_processor.render_fragment(
            "fragments.html", "product_info", product=product
        )
        return JSONResponse({"html": fragment})

    # Create API routes
    api_routes = [
        Route("/data", get_data, name="data"),
        Route("/fragment", get_fragment, name="fragment"),
    ]

    # Create main routes
    routes = [
        Route("/", homepage, name="homepage"),
        Mount("/api", routes=api_routes, name="api"),
    ]

    # Create app
    app = Starlette(routes=routes)

    # Create test client
    client = TestClient(app)

    # Test homepage
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to the Test Application" in response.text
    assert "Username: testuser" in response.text
    assert "Email: test@example.com" in response.text

    # Test API data endpoint
    response = client.get("/api/data")
    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"},
        ]
    }

    # Test fragment endpoint
    response = client.get("/api/fragment")
    assert response.status_code == 200
    fragment = response.json()["html"]
    assert "Test Product" in fragment
    assert "Price: $99.99" in fragment
    assert "This is a test product" in fragment


@pytest.mark.asyncio
async def test_context_processors() -> None:
    """Test that context processors are applied correctly."""
    # Create mock template
    mock_template = MagicMock(spec=Template)
    mock_template.render_async = AsyncMock(return_value="<h1>Test Page</h1>")

    # Create a context processor
    def context_processor(request: Request) -> dict[str, t.Any]:
        return {
            "app_name": "Test App",
            "version": "1.0.0",
            "user": {"is_authenticated": True},
        }

    # Create templates with context processor
    AsyncJinja2Templates(
        directory=AsyncPath("templates"),
        context_processors=[context_processor],
    )

    # Create a mock request
    mock_request = MagicMock(spec=Request)

    # Create a new templates instance using our mock class
    def mock_get_template_func(name: str):
        return mock_template

    templates_mock_cls = MockAsyncJinja2Templates(
        directory=AsyncPath("templates"),
        context_processors=[context_processor],
        mock_get_template_func=mock_get_template_func,
    )

    with patch(
        "starlette_async_jinja.responses._TemplateResponse"
    ) as mock_response_class:
        # Create a response
        await templates_mock_cls.TemplateResponse(
            request=mock_request,
            name="test.html",
            context={"title": "Test Page"},
        )

        # Get the context that was passed to _TemplateResponse
        context_arg = mock_response_class.call_args[0][1]

        # Check that the context processor values were added to the context
        assert "app_name" in context_arg
        assert "version" in context_arg
        assert "user" in context_arg
        assert "title" in context_arg
        assert "request" in context_arg

        assert context_arg["app_name"] == "Test App"
        assert context_arg["version"] == "1.0.0"
        assert context_arg["user"]["is_authenticated"] is True
        assert context_arg["title"] == "Test Page"
        assert context_arg["request"] == mock_request
