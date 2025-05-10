import typing as t
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anyio import Path as AsyncPath
from jinja2.environment import Template
from markupsafe import Markup
from starlette.background import BackgroundTask
from starlette.datastructures import URL
from starlette.requests import Request
from starlette_async_jinja.responses import (
    AsyncJinja2Templates,
    BlockNotFoundError,
    JsonResponse,
    _TemplateResponse,
)


@pytest.fixture
def template_dir(tmp_path: Path) -> AsyncPath:
    template_path = tmp_path / "templates"
    template_path.mkdir()
    return AsyncPath(template_path)


@pytest.fixture
def templates(template_dir: AsyncPath) -> AsyncJinja2Templates:
    return AsyncJinja2Templates(directory=template_dir)


@pytest.fixture
def mock_template() -> MagicMock:
    template = MagicMock(spec=Template)
    template.render_async = AsyncMock(return_value="<h1>Mocked Content</h1>")
    template.blocks = {"my_block": MagicMock()}
    template.new_context = MagicMock(return_value={})
    return template


@pytest.fixture
def mock_request() -> MagicMock:
    mock_request = MagicMock(spec=Request)
    mock_request.url_for.return_value = URL("http://testserver/test")
    return mock_request


@pytest.mark.asyncio
async def test_json_response_render() -> None:
    data: dict[str, t.Any] = {"key": "value"}
    rendered = JsonResponse(data).render(data)
    assert rendered == b'{"key":"value"}'

    nested_data: dict[str, t.Any] = {"nested": {"key": ["value1", "value2"]}}
    rendered = JsonResponse(nested_data).render(nested_data)
    assert rendered == b'{"nested":{"key":["value1","value2"]}}'


@pytest.mark.asyncio
async def test_template_response_init() -> None:
    mock_template = MagicMock()
    context: dict[str, t.Any] = {"key": "value"}
    content = "<html></html>"
    response = _TemplateResponse(mock_template, context, content)
    assert response.template == mock_template
    assert response.context == context
    assert response.body == b"<html></html>"
    assert response.status_code == 200
    assert response.media_type == "text/html"


@pytest.mark.asyncio
async def test_template_response_call_with_debug_extension() -> None:
    mock_template = MagicMock()
    context: dict[str, t.Any] = {"request": {"extensions": {"http.response.debug": {}}}}
    content = "<html></html>"
    response = _TemplateResponse(mock_template, context, content)

    scope: dict[str, t.Any] = {
        "type": "http",
        "extensions": {"http.response.debug": {}},
    }
    receive = AsyncMock()
    send = AsyncMock()
    await response(scope, receive, send)
    send.assert_awaited()
    assert send.await_count == 3
    send_calls = send.await_args_list
    assert send_calls[0].args[0]["type"] == "http.response.debug"
    assert send_calls[0].args[0]["info"]["template"] == mock_template
    assert send_calls[0].args[0]["info"]["context"] == context
    assert send_calls[1].args[0]["type"] == "http.response.start"


@pytest.mark.asyncio
async def test_async_jinja2_templates_init(template_dir: AsyncPath) -> None:
    templates = AsyncJinja2Templates(directory=template_dir)
    assert templates.env is not None
    assert templates.env.loader is not None
    assert templates.env.autoescape is True
    assert hasattr(templates.env, "enable_async")
    assert getattr(templates.env, "enable_async") is True


@pytest.mark.asyncio
async def test_async_jinja2_templates_init_with_options(
    template_dir: AsyncPath,
) -> None:
    templates = AsyncJinja2Templates(
        directory=template_dir, autoescape=False, trim_blocks=True
    )
    assert templates.env is not None
    assert templates.env.autoescape is False
    assert templates.env.trim_blocks is True
    assert hasattr(templates.env, "enable_async")
    assert getattr(templates.env, "enable_async") is True


@pytest.mark.asyncio
async def test_async_jinja2_templates_create_env(template_dir: AsyncPath) -> None:
    env = AsyncJinja2Templates(directory=template_dir)._create_env(template_dir)
    assert env is not None
    assert "render_block" in env.globals
    assert "url_for" in env.globals
    assert env.autoescape is True
    assert hasattr(env, "enable_async")
    assert getattr(env, "enable_async") is True


@pytest.mark.asyncio
async def test_async_jinja2_templates_render_block(
    templates: AsyncJinja2Templates, template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    with patch.object(templates, "get_template_async", return_value=mock_template):
        with patch.object(templates, "renderer", AsyncMock(return_value="Test Block")):
            result = await templates.render_block("test.html", my_block="my block")
            assert result == "Test Block"


@pytest.mark.asyncio
async def test_async_jinja2_templates_generate_render_partial(
    templates: AsyncJinja2Templates, template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    mock_renderer = AsyncMock(return_value="Test Block")
    with patch.object(templates, "get_template_async", return_value=mock_template):
        partial_renderer = templates.generate_render_partial(mock_renderer)
        result = await partial_renderer("test.html", my_block="my block")
        assert result == "Test Block"
        mock_renderer.assert_awaited_once_with("test.html", my_block="my block")


@pytest.mark.asyncio
async def test_async_jinja2_templates_renderer(
    templates: AsyncJinja2Templates, template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    mock_template.render_async.return_value = "<h1>Test Title</h1>"
    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        result = await templates.renderer("test.html", title="Test Title")
        assert result == "<h1>Test Title</h1>"
        mock_template.render_async.assert_awaited_once_with(title="Test Title")


@pytest.mark.asyncio
async def test_async_jinja2_templates_render_fragment(
    templates: AsyncJinja2Templates, template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        with patch.object(templates.env, "concat", return_value="Test Block"):
            with patch.object(
                mock_template.blocks["my_block"], "__call__", return_value=[]
            ):
                result = await templates.render_fragment("test.html", "my_block")
                assert result == "Test Block"


@pytest.mark.asyncio
async def test_async_jinja2_templates_render_fragment_with_context(
    templates: AsyncJinja2Templates, template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        with patch.object(templates.env, "concat", return_value="Hello World"):
            with patch.object(
                mock_template.blocks["my_block"], "__call__", return_value=[]
            ):
                result = await templates.render_fragment(
                    "test.html", "my_block", message="Hello World"
                )
                assert result == "Hello World"


@pytest.mark.asyncio
async def test_async_jinja2_templates_render_fragment_block_not_found(
    templates: AsyncJinja2Templates, template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    mock_template.blocks = {}

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        with pytest.raises(BlockNotFoundError) as exc_info:
            await templates.render_fragment("test.html", "my_block")
        assert "Block 'my_block' not found in template 'test.html'" in str(
            exc_info.value
        )


@pytest.mark.asyncio
async def test_async_jinja2_templates_get_template(
    templates: AsyncJinja2Templates, template_dir: AsyncPath
) -> None:
    with patch.object(
        templates.env, "get_template_async", AsyncMock()
    ) as mock_get_template:
        mock_template = MagicMock()
        mock_get_template.return_value = mock_template

        template = await templates.get_template_async("test.html")
        assert template is mock_template
        mock_get_template.assert_awaited_once_with("test.html")


@pytest.mark.asyncio
async def test_async_jinja2_templates_get_template_not_found(
    templates: AsyncJinja2Templates,
) -> None:
    with patch.object(
        templates.env,
        "get_template_async",
        AsyncMock(side_effect=Exception("Template not found")),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            await templates.get_template_async("nonexistent.html")
        assert "Error loading template 'nonexistent.html'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_jinja2_templates_template_response(
    templates: AsyncJinja2Templates,
    template_dir: AsyncPath,
    mock_request: MagicMock,
    mock_template: MagicMock,
) -> None:
    mock_template.render_async.return_value = "<h1>Test Title</h1>"

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        response = await templates.TemplateResponse(
            mock_request, "test.html", context={"title": "Test Title"}
        )
        assert response.status_code == 200
        assert response.media_type == "text/html"
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert b"<h1>Test Title</h1>" in response.body


@pytest.mark.asyncio
async def test_async_jinja2_templates_template_response_kwargs(
    templates: AsyncJinja2Templates,
    template_dir: AsyncPath,
    mock_request: MagicMock,
    mock_template: MagicMock,
) -> None:
    mock_template.render_async.return_value = "<h1>Test Title</h1>"

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        response = await templates.TemplateResponse(
            name="test.html", context={"title": "Test Title"}, request=mock_request
        )
        assert response.status_code == 200
        assert response.media_type == "text/html"
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert b"<h1>Test Title</h1>" in response.body


@pytest.mark.asyncio
async def test_async_jinja2_templates_template_response_context_processors(
    template_dir: AsyncPath, mock_request: MagicMock, mock_template: MagicMock
) -> None:
    def context_processor(request: Request) -> dict[str, str]:
        return {"from_processor": "processed"}

    templates = AsyncJinja2Templates(
        directory=template_dir, context_processors=[context_processor]
    )

    mock_template.render_async.return_value = "<h1>processed</h1>"

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        response = await templates.TemplateResponse(
            request=mock_request,
            name="test.html",
            context={},
        )
        assert response.status_code == 200
        assert b"<h1>processed</h1>" in response.body

        context_with_processor = {
            "request": mock_request,
            "from_processor": "processed",
        }
        mock_template.render_async.assert_awaited_once_with(context_with_processor)


@pytest.mark.asyncio
async def test_async_jinja2_templates_template_response_other_args(
    templates: AsyncJinja2Templates,
    template_dir: AsyncPath,
    mock_request: MagicMock,
    mock_template: MagicMock,
) -> None:
    mock_template.render_async.return_value = "<h1>Test Title</h1>"

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        response = await templates.TemplateResponse(
            mock_request,
            "test.html",
            {"title": "Test Title"},
            201,
            {"custom-header": "value"},
            "application/custom",
            BackgroundTask(lambda: None),
        )
        assert response.status_code == 201
        assert response.media_type == "application/custom"
        assert "application/custom" in response.headers["content-type"]
        assert response.headers["custom-header"] == "value"
        assert b"<h1>Test Title</h1>" in response.body
        assert response.background is not None


@pytest.mark.asyncio
async def test_render_template_alias(
    templates: AsyncJinja2Templates,
    template_dir: AsyncPath,
    mock_request: MagicMock,
    mock_template: MagicMock,
) -> None:
    mock_template.render_async.return_value = "<h1>Test Title</h1>"

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        response = await templates.render_template(
            mock_request, "test.html", context={"title": "Test Title"}
        )
        assert response.status_code == 200
        assert response.media_type == "text/html"
        assert b"<h1>Test Title</h1>" in response.body
        assert response.headers["content-type"] == "text/html; charset=utf-8"


@pytest.mark.asyncio
async def test_render_block_error_handling(
    templates: AsyncJinja2Templates, template_dir: AsyncPath
) -> None:
    async def failing_renderer(template_name: str, **data: t.Any) -> str:
        raise ValueError("Test renderer error")

    with pytest.raises(RuntimeError) as exc_info:
        await templates.render_block("test.html", renderer=failing_renderer)

    assert "Error rendering block in template 'test.html'" in str(exc_info.value)
    assert "Test renderer error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_template_response_with_none_context(
    templates: AsyncJinja2Templates,
    template_dir: AsyncPath,
    mock_request: MagicMock,
    mock_template: MagicMock,
) -> None:
    mock_template.render_async.return_value = "<h1>Test</h1>"

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        response = await templates.TemplateResponse(
            mock_request, "test.html", context=None
        )

        assert response.status_code == 200
        assert response.media_type == "text/html"
        assert b"<h1>Test</h1>" in response.body
        assert "request" in response.context
        assert response.context["request"] == mock_request


@pytest.mark.asyncio
async def test_async_jinja2_templates_renderer_error_handling(
    templates: AsyncJinja2Templates, template_dir: AsyncPath
) -> None:
    with patch.object(
        templates,
        "get_template_async",
        AsyncMock(side_effect=ValueError("Template rendering error")),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            await templates.renderer("test.html", title="Test Title")
        assert "Error rendering template 'test.html'" in str(exc_info.value)
        assert "Template rendering error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_jinja2_templates_render_fragment_exception_handling(
    templates: AsyncJinja2Templates, template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    with patch.object(
        templates,
        "get_template_async",
        AsyncMock(side_effect=Exception("Template loading error")),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            await templates.render_fragment("test.html", "my_block")
        assert "Error rendering fragment 'my_block' in template 'test.html'" in str(
            exc_info.value
        )
        assert "Template loading error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_jinja2_templates_template_response_error_handling(
    templates: AsyncJinja2Templates, mock_request: MagicMock
) -> None:
    with patch.object(
        templates,
        "get_template_async",
        AsyncMock(side_effect=ValueError("Template loading error")),
    ):
        with pytest.raises(RuntimeError) as exc_info:
            await templates.TemplateResponse(mock_request, "test.html", {})
        assert "Error creating template response for 'test.html'" in str(exc_info.value)
        assert "Template loading error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_jinja2_templates_render_block_no_markup(
    templates: AsyncJinja2Templates, template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    with patch.object(templates, "get_template_async", return_value=mock_template):
        with patch.object(templates, "renderer", AsyncMock(return_value="Test Block")):
            result = await templates.render_block(
                "test.html", markup=False, my_block="my block"
            )
            assert result == "Test Block"
            assert not isinstance(result, Markup)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data,expected",
    [
        ({"key": "value"}, b'{"key":"value"}'),
        (
            {"nested": {"key": ["value1", "value2"]}},
            b'{"nested":{"key":["value1","value2"]}}',
        ),
        ([], b"[]"),
        ({}, b"{}"),
        (None, b"null"),
        (123, b"123"),
        ("string", b'"string"'),
        (True, b"true"),
    ],
)
async def test_json_response_render_parametrized(data: t.Any, expected: bytes) -> None:
    rendered = JsonResponse(data).render(data)
    assert rendered == expected


@pytest.mark.asyncio
async def test_async_jinja2_templates_render_fragment_handle_exception(
    templates: AsyncJinja2Templates, template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    async def mock_generator():
        raise Exception("Block rendering error")
        yield "This will never be yielded"

    mock_block_func = MagicMock()
    mock_block_func.return_value = mock_generator()

    mock_template.blocks = {"my_block": mock_block_func}

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        mock_handle_exception = MagicMock(return_value="Error handled")
        with patch.object(templates.env, "handle_exception", mock_handle_exception):
            result = await templates.render_fragment("test.html", "my_block")
            assert result == "Error handled"
            mock_handle_exception.assert_called_once()
