from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anyio import Path as AsyncPath
from jinja2.environment import Template
from starlette_async_jinja.responses import AsyncJinja2Templates, BlockNotFoundError


@pytest.mark.asyncio
async def test_get_context_cache_key_fallback() -> None:
    """Test _get_context_cache_key with non-standard request objects."""
    templates = AsyncJinja2Templates(directory=AsyncPath("templates"))

    # Test with object that doesn't have url.path
    class MockRequest:
        def __init__(self, method: str = "GET") -> None:
            self.method = method

    mock_request = MockRequest()
    key = templates._get_context_cache_key(mock_request)
    # The key will be based on the string representation of the object
    assert key.startswith("GET:<tests.test_missing_coverage.")

    # Test with object that has method but no url
    mock_request2 = MockRequest("POST")
    key2 = templates._get_context_cache_key(mock_request2)
    assert key2.startswith("POST:<tests.test_missing_coverage.")


@pytest.mark.asyncio
async def test_get_cached_block_func_cache_eviction() -> None:
    """Test _get_cached_block_func cache eviction when cache is full."""
    templates = AsyncJinja2Templates(
        directory=AsyncPath("templates"),
        fragment_cache_size=2,  # Small cache for testing
    )

    # Create mock templates with different blocks
    mock_template1 = MagicMock(spec=Template)
    mock_template1.blocks = {"block1": MagicMock()}
    mock_template1.new_context = MagicMock(return_value={})

    mock_template2 = MagicMock(spec=Template)
    mock_template2.blocks = {"block2": MagicMock()}
    mock_template2.new_context = MagicMock(return_value={})

    mock_template3 = MagicMock(spec=Template)
    mock_template3.blocks = {"block3": MagicMock()}
    mock_template3.new_context = MagicMock(return_value={})

    # Mock get_template_async to return different templates
    template_map = {
        "template1.html": mock_template1,
        "template2.html": mock_template2,
        "template3.html": mock_template3,
    }

    async def get_template_side_effect(name: str) -> Template:
        return template_map[name]

    with patch.object(
        templates,
        "get_template_async",
        AsyncMock(side_effect=get_template_side_effect),
    ):
        # Fill cache beyond limit
        await templates._get_cached_block_func("template1.html", "block1")
        await templates._get_cached_block_func("template2.html", "block2")
        await templates._get_cached_block_func("template3.html", "block3")

        # Cache should only contain 2 entries (LRU eviction)
        assert len(templates._block_cache) == 2
        assert "template1.html:block1" not in templates._block_cache  # Oldest evicted
        assert "template2.html:block2" in templates._block_cache
        assert "template3.html:block3" in templates._block_cache


@pytest.mark.asyncio
async def test_get_block_function_and_template_cache_eviction() -> None:
    """Test _get_block_function_and_template cache eviction when cache is full."""
    templates = AsyncJinja2Templates(
        directory=AsyncPath("templates"),
        fragment_cache_size=2,  # Small cache for testing
    )

    # Create mock templates with different blocks
    mock_template1 = MagicMock(spec=Template)
    mock_template1.blocks = {"block1": MagicMock()}
    mock_template1.new_context = MagicMock(return_value={})

    mock_template2 = MagicMock(spec=Template)
    mock_template2.blocks = {"block2": MagicMock()}
    mock_template2.new_context = MagicMock(return_value={})

    mock_template3 = MagicMock(spec=Template)
    mock_template3.blocks = {"block3": MagicMock()}
    mock_template3.new_context = MagicMock(return_value={})

    # Mock get_template_async to return different templates
    template_map = {
        "template1.html": mock_template1,
        "template2.html": mock_template2,
        "template3.html": mock_template3,
    }

    async def get_template_side_effect(name: str) -> Template:
        return template_map[name]

    with patch.object(
        templates,
        "get_template_async",
        AsyncMock(side_effect=get_template_side_effect),
    ):
        # Fill cache beyond limit through _get_block_function_and_template
        await templates._get_block_function_and_template("template1.html", "block1")
        await templates._get_block_function_and_template("template2.html", "block2")
        await templates._get_block_function_and_template("template3.html", "block3")

        # Cache should only contain 2 entries (LRU eviction)
        assert len(templates._block_cache) == 2
        assert "template1.html:block1" not in templates._block_cache  # Oldest evicted
        assert "template2.html:block2" in templates._block_cache
        assert "template3.html:block3" in templates._block_cache


@pytest.mark.asyncio
async def test_render_fragment_handle_exception() -> None:
    """Test render_fragment handle_exception path."""
    templates = AsyncJinja2Templates(directory=AsyncPath("templates"))

    # Create mock template
    mock_template = MagicMock(spec=Template)
    mock_template.blocks = {"test_block": MagicMock()}
    mock_template.new_context = MagicMock(return_value={})

    # Mock block function that raises an exception
    async def mock_generator():
        raise Exception("Block rendering error")
        yield "This will never be yielded"

    mock_block_func = MagicMock()
    mock_block_func.return_value = mock_generator()

    mock_template.blocks = {"test_block": mock_block_func}

    with patch.object(
        templates, "get_template_async", AsyncMock(return_value=mock_template)
    ):
        mock_handle_exception = MagicMock(return_value="Error handled by env")
        with patch.object(templates.env, "handle_exception", mock_handle_exception):
            result = await templates.render_fragment("test.html", "test_block")
            assert result == "Error handled by env"
            mock_handle_exception.assert_called_once()


@pytest.mark.asyncio
async def test_render_fragment_block_not_found_validation() -> None:
    """Test render_fragment with block not found validation."""
    templates = AsyncJinja2Templates(directory=AsyncPath("templates"))

    # Preload template blocks to trigger validation
    mock_template = MagicMock(spec=Template)
    mock_template.blocks = {"existing_block": MagicMock()}
    templates._preload_template_blocks(mock_template, "test.html")

    # Try to render a non-existent block
    with pytest.raises(BlockNotFoundError) as exc_info:
        await templates.render_fragment("test.html", "nonexistent_block")

    assert "Block 'nonexistent_block' not found in template 'test.html'" in str(
        exc_info.value
    )
