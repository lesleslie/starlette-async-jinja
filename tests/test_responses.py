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
async def test_context_processor_caching(
    template_dir: AsyncPath, mock_request: MagicMock, mock_template: MagicMock
) -> None:
    call_count = 0

    def expensive_context_processor(request: Request) -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        return {"call_count": str(call_count), "expensive_data": "computed"}

    templates = AsyncJinja2Templates(
        directory=template_dir,
        context_processors=[expensive_context_processor],
        context_cache_ttl=1.0,  # 1 second TTL for testing
    )

    mock_template.render_async.return_value = "<h1>cached content</h1>"

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        # First call - should execute context processor
        await templates.TemplateResponse(
            request=mock_request, name="test.html", context={}
        )
        assert call_count == 1

        # Second call - should use cached result
        await templates.TemplateResponse(
            request=mock_request, name="test.html", context={}
        )
        assert call_count == 1  # No additional call

        # Wait for cache to expire and call again
        import time

        time.sleep(1.1)
        await templates.TemplateResponse(
            request=mock_request, name="test.html", context={}
        )
        assert call_count == 2  # New call after cache expiry


@pytest.mark.asyncio
async def test_context_processor_cache_key_generation(template_dir: AsyncPath) -> None:
    templates = AsyncJinja2Templates(directory=template_dir)

    # Mock request with URL and method
    mock_request1 = MagicMock()
    mock_request1.url.path = "/home"
    mock_request1.method = "GET"

    mock_request2 = MagicMock()
    mock_request2.url.path = "/about"
    mock_request2.method = "GET"

    mock_request3 = MagicMock()
    mock_request3.url.path = "/home"
    mock_request3.method = "POST"

    key1 = templates._get_context_cache_key(mock_request1)
    key2 = templates._get_context_cache_key(mock_request2)
    key3 = templates._get_context_cache_key(mock_request3)

    assert key1 == "GET:/home"
    assert key2 == "GET:/about"
    assert key3 == "POST:/home"
    assert key1 != key2
    assert key1 != key3


@pytest.mark.asyncio
async def test_context_processor_cache_size_limit(
    template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    templates = AsyncJinja2Templates(
        directory=template_dir,
        context_processors=[lambda req: {"static": "data"}],
        context_cache_size=2,  # Small cache for testing
    )

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        # Create multiple requests with different paths
        requests = []
        for i in range(3):
            mock_req = MagicMock()
            mock_req.url.path = f"/page{i}"
            mock_req.method = "GET"
            requests.append(mock_req)

        # Fill cache beyond limit
        for req in requests:
            templates._get_processed_context(req)

        # Cache should only contain 2 entries (newest ones)
        assert len(templates._context_cache) == 2

        # First entry should be evicted (LRU behavior)
        assert "GET:/page0" not in templates._context_cache
        assert "GET:/page1" in templates._context_cache
        assert "GET:/page2" in templates._context_cache


@pytest.mark.asyncio
async def test_context_processor_no_caching_with_request_in_context(
    template_dir: AsyncPath, mock_request: MagicMock
) -> None:
    def context_processor_with_request(request: Request) -> dict[str, t.Any]:
        # This context contains request, so should not be cached
        return {"request_specific": request, "data": "value"}

    templates = AsyncJinja2Templates(
        directory=template_dir, context_processors=[context_processor_with_request]
    )

    # Process context
    context = templates._get_processed_context(mock_request)

    # Should not be cached due to request object
    assert not templates._context_cache
    assert context["data"] == "value"
    assert context["request_specific"] == mock_request


@pytest.mark.asyncio
async def test_fragment_block_function_caching(
    template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    templates = AsyncJinja2Templates(
        directory=template_dir,
        fragment_cache_ttl=1.0,  # 1 second TTL for testing
    )

    # Mock block function
    mock_block_func = MagicMock()
    mock_template.blocks = {"test_block": mock_block_func}
    mock_template.new_context = MagicMock(return_value={})

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        # First call - should cache block function
        await templates._get_cached_block_func("test.html", "test_block")
        assert len(templates._block_cache) == 1

        # Second call - should use cached function
        cached_func = await templates._get_cached_block_func("test.html", "test_block")
        assert cached_func == mock_block_func

        # Wait for cache to expire
        import time

        time.sleep(1.1)

        # Third call - should reload after expiry
        await templates._get_cached_block_func("test.html", "test_block")
        # Cache should still contain the entry but with updated timestamp


@pytest.mark.asyncio
async def test_fragment_block_cache_size_limit(
    template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    templates = AsyncJinja2Templates(
        directory=template_dir,
        fragment_cache_size=2,  # Small cache for testing
    )

    # Create different block functions
    mock_template.blocks = {
        "block1": MagicMock(),
        "block2": MagicMock(),
        "block3": MagicMock(),
    }
    mock_template.new_context = MagicMock(return_value={})

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        # Fill cache beyond limit
        await templates._get_cached_block_func("test.html", "block1")
        await templates._get_cached_block_func("test.html", "block2")
        await templates._get_cached_block_func("test.html", "block3")

        # Cache should only contain 2 entries (LRU eviction)
        assert len(templates._block_cache) == 2
        assert "test.html:block1" not in templates._block_cache  # Oldest evicted
        assert "test.html:block2" in templates._block_cache
        assert "test.html:block3" in templates._block_cache


@pytest.mark.asyncio
async def test_context_pooling(template_dir: AsyncPath) -> None:
    templates = AsyncJinja2Templates(directory=template_dir, context_pool_size=2)

    # Get contexts from pool
    ctx1 = templates._get_pooled_context({"key1": "value1"})
    ctx2 = templates._get_pooled_context({"key2": "value2"})

    assert ctx1 == {"key1": "value1"}
    assert ctx2 == {"key2": "value2"}
    assert not templates._context_pool  # Pool empty

    # Return contexts to pool
    templates._return_to_pool(ctx1)
    templates._return_to_pool(ctx2)

    assert len(templates._context_pool) == 2

    # Get context from pool - should reuse
    ctx3 = templates._get_pooled_context({"key3": "value3"})
    assert ctx3 == {"key3": "value3"}
    assert len(templates._context_pool) == 1  # One removed from pool

    # Test pool size limit
    templates._return_to_pool(ctx3)
    extra_ctx = templates._get_pooled_context({"extra": "data"})
    templates._return_to_pool(extra_ctx)

    # Should not exceed pool size limit
    assert len(templates._context_pool) == 2


@pytest.mark.asyncio
async def test_template_blocks_preloading(
    template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    templates = AsyncJinja2Templates(directory=template_dir)

    mock_template.blocks = {"header": MagicMock(), "footer": MagicMock()}

    # Preload blocks
    templates._preload_template_blocks(mock_template, "test.html")

    assert "test.html" in templates._template_blocks
    assert templates._template_blocks["test.html"] == {"header", "footer"}

    # Test validation
    assert templates._validate_block_exists("test.html", "header")
    assert not templates._validate_block_exists("test.html", "nonexistent")
    assert templates._validate_block_exists("unknown.html", "any")  # Unknown template


@pytest.mark.asyncio
async def test_stringio_threshold_logic(template_dir: AsyncPath) -> None:
    templates = AsyncJinja2Templates(
        directory=template_dir, fragment_stringio_threshold=100
    )

    # Small size - should not use StringIO
    assert not templates._should_use_stringio(50)

    # Large size - should use StringIO
    assert templates._should_use_stringio(200)

    # Exact threshold - should use StringIO
    assert not templates._should_use_stringio(100)
    assert templates._should_use_stringio(101)


@pytest.mark.asyncio
async def test_optimized_render_fragment_with_stringio(
    template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    templates = AsyncJinja2Templates(
        directory=template_dir,
        fragment_stringio_threshold=10,  # Low threshold to trigger StringIO
    )

    # Mock block function that yields chunks
    async def mock_block_generator(ctx: t.Any) -> t.AsyncIterator[str]:
        yield "Hello "
        yield "World "
        yield "from StringIO!"

    mock_block_func = MagicMock(side_effect=mock_block_generator)
    mock_template.blocks = {"test_block": mock_block_func}
    mock_template.new_context = MagicMock(return_value={})

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        result = await templates.render_fragment(
            "test.html",
            "test_block",
            large_data="x" * 50,  # Triggers StringIO
        )

        assert result == "Hello World from StringIO!"
        assert len(templates._context_pool) == 1  # Context returned to pool


@pytest.mark.asyncio
async def test_optimized_render_fragment_with_concat(
    template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    templates = AsyncJinja2Templates(
        directory=template_dir,
        fragment_stringio_threshold=1000,  # High threshold to use concat
    )

    # Mock block function
    async def mock_block_generator(ctx: t.Any) -> t.AsyncIterator[str]:
        yield "Small "
        yield "output"

    mock_block_func = MagicMock(side_effect=mock_block_generator)
    mock_template.blocks = {"test_block": mock_block_func}
    mock_template.new_context = MagicMock(return_value={})

    with (
        patch.object(
            templates, "get_template_async", AsyncMock(return_value=mock_template)
        ),
        patch.object(
            templates.env, "concat", return_value="Small output"
        ) as mock_concat,
    ):
        result = await templates.render_fragment(
            "test.html", "test_block", small_data="tiny"
        )

        assert result == "Small output"
        mock_concat.assert_called_once()
        assert len(templates._context_pool) == 1  # Context returned to pool


@pytest.mark.asyncio
async def test_fragment_cache_integration(
    template_dir: AsyncPath, mock_template: MagicMock
) -> None:
    call_count = 0

    def get_template_side_effect(name: str):
        nonlocal call_count
        call_count += 1
        return mock_template

    templates = AsyncJinja2Templates(directory=template_dir)

    mock_template.blocks = {"cached_block": MagicMock()}
    mock_template.new_context = MagicMock(return_value={})

    with (
        patch.object(
            templates,
            "get_template_async",
            AsyncMock(side_effect=get_template_side_effect),
        ),
        patch.object(templates.env, "concat", return_value="cached result"),
    ):
        # First call - should load template and cache block
        result1 = await templates.render_fragment("test.html", "cached_block")
        assert result1 == "cached result"
        assert call_count == 1

        # Second call - should use cached block, but still load template for context
        result2 = await templates.render_fragment("test.html", "cached_block")
        assert result2 == "cached result"
        assert call_count == 2  # Template still loaded for context creation

        # Block should be cached
        assert len(templates._block_cache) == 1
        assert "test.html:cached_block" in templates._block_cache


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
