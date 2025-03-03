from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiopath import AsyncPath
from starlette.background import BackgroundTask
from starlette.datastructures import URL
from starlette.requests import Request

from starlette_async_jinja.responses import (_TemplateResponse, AsyncJinja2Templates,
                                             BlockNotFoundError, JsonResponse)


@pytest.fixture
def template_dir(tmp_path: Path) -> AsyncPath:
    """Fixture for a temporary template directory."""
    template_path = tmp_path / "templates"
    template_path.mkdir()
    return AsyncPath(template_path)


@pytest.fixture
def templates(template_dir: AsyncPath) -> AsyncJinja2Templates:
    """Fixture for an AsyncJinja2Templates instance."""
    return AsyncJinja2Templates(directory=template_dir)


@pytest.fixture
def mock_request() -> MagicMock:
    """Fixture for a mock request."""
    mock_request = MagicMock(spec=Request)
    mock_request.url_for.return_value = URL("http://testserver/test")
    return mock_request


@pytest.mark.asyncio
async def test_json_response_render() -> None:
    """Test that JsonResponse.render encodes content as JSON."""
    data = {"key": "value"}
    response = JsonResponse(data)
    rendered = response.render(data)
    assert rendered == b'{"key":"value"}'

@pytest.mark.asyncio
async def test_template_response_init() -> None:
    """Test the initialization of _TemplateResponse."""
    mock_template = MagicMock()
    context = {"key": "value"}
    content = "<html></html>"
    response = _TemplateResponse(mock_template, context, content)
    assert response.template == mock_template
    assert response.context == context
    assert response.body == b"<html></html>"
    assert response.status_code == 200
    assert response.media_type == "text/html"

@pytest.mark.asyncio
async def test_template_response_call_with_debug_extension() -> None:
    """Test _TemplateResponse.__call__ with the debug extension."""
    mock_template = MagicMock()
    context = {"request": {"extensions": {"http.response.debug": {}}}}
    content = "<html></html>"
    response = _TemplateResponse(mock_template, context, content)

    scope = {"type": "http", "extensions": {"http.response.debug": {}}}
    receive = AsyncMock()
    send = AsyncMock()
    await response(scope, receive, send)
    send.assert_awaited()
    assert send.await_count == 2
    send_calls = send.await_args_list
    assert send_calls[0].args[0]["type"] == "http.response.debug"
    assert send_calls[0].args[0]["info"]["template"] == mock_template
    assert send_calls[0].args[0]["info"]["context"] == context
    assert send_calls[1].args[0]["type"] == "http.response.start"

@pytest.mark.asyncio
async def test_async_jinja2_templates_init(template_dir: AsyncPath) -> None:
    """Test the initialization of AsyncJinja2Templates."""
    templates = AsyncJinja2Templates(directory=template_dir)
    assert templates.env is not None
    assert templates.env.loader is not None
    assert templates.env.autoescape is True
    assert templates.env.is_async

@pytest.mark.asyncio
async def test_async_jinja2_templates_create_env(template_dir: AsyncPath) -> None:
    """Test _create_env method."""
    templates = AsyncJinja2Templates(directory=template_dir)
    env = templates._create_env(template_dir)
    assert env is not None
    assert "render_block" in env.globals
    assert "url_for" in env.globals
    assert env.autoescape is True
    assert env.is_async

@pytest.mark.asyncio
async def test_async_jinja2_templates_render_block(
    templates: AsyncJinja2Templates, template_dir: AsyncPath
) -> None:
    """Test the render_block method."""
    (template_dir / "test.html").write_text("{% block my_block %}Test Block{% endblock %}")
    result = await templates.render_block("test.html", my_block="my block")
    assert result == "Test Block"

    result = await templates.render_block("test.html", my_block="my block", markup=False)
    assert result == "Test Block"

@pytest.mark.asyncio
async def test_async_jinja2_templates_generate_render_partial(
    templates: AsyncJinja2Templates, template_dir: AsyncPath
) -> None:
    """Test the generate_render_partial method."""
    (template_dir / "test.html").write_text("{% block my_block %}Test Block{% endblock %}")
    partial_renderer = templates.generate_render_partial(templates.renderer)
    result = await partial_renderer("test.html", my_block="my block")
    assert result == "Test Block"

@pytest.mark.asyncio
async def test_async_jinja2_templates_renderer(
    templates: AsyncJinja2Templates, template_dir: AsyncPath
) -> None:
    """Test the renderer method."""
    (template_dir / "test.html").write_text("<h1>{{ title }}</h1>")
    result = await templates.renderer("test.html", title="Test Title")
    assert result == "<h1>Test Title</h1>"

@pytest.mark.asyncio
async def test_async_jinja2_templates_render_fragment(
    templates: AsyncJinja2Templates, template_dir: AsyncPath
) -> None:
    """Test the render_fragment method."""
    (template_dir / "test.html").write_text("{% block my_block %}Test Block{% endblock %}")
    result = await templates.render_fragment("test.html", "my_block")
    assert result == "Test Block"

@pytest.mark.asyncio
async def test_async_jinja2_templates_render_fragment_block_not_found(
    templates: AsyncJinja2Templates, template_dir: AsyncPath
) -> None:
    """Test render_fragment when the block is not found."""
    (template_dir / "test.html").write_text("")
    with pytest.raises(BlockNotFoundError) as exc_info:
        await templates.render_fragment("test.html", "my_block")
    assert "Block 'my_block' not found in template 'test.html'" in str(exc_info.value)

@pytest.mark.asyncio
async def test_async_jinja2_templates_get_template(
    templates: AsyncJinja2Templates, template_dir: AsyncPath
) -> None:
    """Test the get_template method."""
    (template_dir / "test.html").write_text("Test Template")
    template = await templates.get_template("test.html")
    assert template is not None
    assert await template.render_async() == "Test Template"


@pytest.mark.asyncio
async def test_async_jinja2_templates_template_response(
        templates: AsyncJinja2Templates, template_dir: AsyncPath,
        mock_request: MagicMock
) -> None:
    """Test the TemplateResponse method."""
    (template_dir / "test.html").write_text("<h1>{{ title }}</h1>")
    response = await templates.TemplateResponse(
        mock_request, "test.html", context={"title": "Test Title"}
    )
    assert response.status_code == 200
    assert response.media_type == "text/html"
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert b"<h1>Test Title</h1>" in response.body

@pytest.mark.asyncio
async def test_async_jinja2_templates_template_response_kwargs(
    templates: AsyncJinja2Templates, template_dir: AsyncPath, mock_request: MagicMock
) -> None:
    """Test the TemplateResponse method with kwargs."""
    (template_dir / "test.html").write_text("<h1>{{ title }}</h1>")
    response = await templates.TemplateResponse(
        name="test.html", context={"title": "Test Title"}, request=mock_request
    )
    assert response.status_code == 200
    assert response.media_type == "text/html"
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert b"<h1>Test Title</h1>" in response.body

@pytest.mark.asyncio
async def test_async_jinja2_templates_template_response_context_processors(
    template_dir: AsyncPath, mock_request: MagicMock
):
    """Test the TemplateResponse method with context processors."""
    def context_processor(request: Request):
        return {"from_processor": "processed"}

    templates = AsyncJinja2Templates(
        directory=template_dir, context_processors=[context_processor]
    )
    (template_dir / "test.html").write_text("<h1>{{ from_processor }}</h1>")
    response = await templates.TemplateResponse(
        request=mock_request,
        name="test.html",
        context={},
    )
    assert response.status_code == 200
    assert b"<h1>processed</h1>" in response.body

@pytest.mark.asyncio
async def test_async_jinja2_templates_template_response_other_args(
    templates: AsyncJinja2Templates, template_dir: AsyncPath, mock_request: MagicMock
) -> None:
    """Test the TemplateResponse method with other args."""
    (template_dir / "test.html").write_text("<h1>{{ title }}</h1>")
    response = await templates.TemplateResponse(
        mock_request, "test.html", {"title": "Test Title"}, 201, {"custom-header": "value"}, "application/custom", BackgroundTask(lambda: None)
    )
    assert response.status_code == 201
    assert response.media_type == "application/custom"
    assert response.headers["content-type"] == "application/custom; charset=utf-8"
    assert response.headers["custom-header"] == "value"
    assert b"<h1>Test Title</h1>" in response.body
    assert response.background is not None






