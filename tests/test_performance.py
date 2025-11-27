"""Performance and benchmarking tests for starlette-async-jinja."""

import typing as t
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anyio import Path as AsyncPath
from jinja2.environment import Template
from starlette_async_jinja.responses import AsyncJinja2Templates


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_template_rendering_large_context(benchmark) -> None:
    """Benchmark template rendering with large contexts."""
    templates = AsyncJinja2Templates(directory=AsyncPath("templates"))

    # Create a large context
    large_context = {f"key_{i}": f"value_{i}" for i in range(1000)}

    # Create mock template
    mock_template = MagicMock(spec=Template)
    mock_template.render_async = AsyncMock(return_value="<h1>Test</h1>")

    async def render_template():
        with patch.object(
            templates, "get_template_async", AsyncMock(return_value=mock_template)
        ):
            return await templates.TemplateResponse(
                MagicMock(), "test.html", large_context
            )

    # Run benchmark
    result = await benchmark(render_template)
    assert result is not None


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_fragment_rendering_nested_blocks(benchmark) -> None:
    """Benchmark fragment rendering with nested blocks."""
    templates = AsyncJinja2Templates(directory=AsyncPath("templates"))

    # Create mock template with nested blocks
    mock_template = MagicMock(spec=Template)
    mock_template.blocks = {"outer": MagicMock(), "inner": MagicMock()}
    mock_template.new_context = MagicMock(return_value={})

    # Mock block functions
    async def outer_generator(ctx: t.Any) -> t.AsyncIterator[str]:
        yield "<div class='outer'>"
        yield "<div class='inner'>Content</div>"
        yield "</div>"

    async def inner_generator(ctx: t.Any) -> t.AsyncIterator[str]:
        yield "<div class='inner'>Content</div>"

    mock_template.blocks["outer"].return_value = outer_generator({})
    mock_template.blocks["inner"].return_value = inner_generator({})

    async def render_fragment():
        with patch.object(
            templates, "get_template_async", AsyncMock(return_value=mock_template)
        ):
            with patch.object(
                templates.env, "concat", return_value="<div>Content</div>"
            ):
                return await templates.render_fragment("test.html", "outer")

    # Run benchmark
    result = await benchmark(render_fragment)
    assert result is not None


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_context_processor_performance(benchmark) -> None:
    """Benchmark context processor performance with complex processors."""

    # Create a complex context processor
    def complex_context_processor(request: t.Any) -> dict[str, t.Any]:
        # Simulate complex processing
        result = {}
        for i in range(100):
            result[f"computed_{i}"] = f"value_{i}"
        return result

    templates = AsyncJinja2Templates(
        directory=AsyncPath("templates"), context_processors=[complex_context_processor]
    )

    # Create mock template
    mock_template = MagicMock(spec=Template)
    mock_template.render_async = AsyncMock(return_value="<h1>Test</h1>")

    # Create mock request
    mock_request = MagicMock()
    mock_request.url.path = "/test"
    mock_request.method = "GET"

    async def process_context():
        with patch.object(
            templates, "get_template_async", AsyncMock(return_value=mock_template)
        ):
            return await templates.TemplateResponse(mock_request, "test.html", {})

    # Run benchmark
    result = await benchmark(process_context)
    assert result is not None


@pytest.mark.benchmark
def test_benchmark_memory_usage_context_pooling(benchmark) -> None:
    """Benchmark memory usage with context pooling."""
    templates = AsyncJinja2Templates(
        directory=AsyncPath("templates"),
        context_pool_size=100,  # Large pool size
    )

    # Test context pooling performance
    def test_pooling():
        contexts = []
        # Get contexts from pool
        for i in range(50):
            ctx = templates._get_pooled_context({"key": f"value_{i}"})
            contexts.append(ctx)

        # Return contexts to pool
        for ctx in contexts:
            templates._return_to_pool(ctx)

        return len(templates._context_pool)

    # Run benchmark
    result = benchmark(test_pooling)
    assert result >= 0


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_cache_performance_under_load(benchmark) -> None:
    """Benchmark cache performance under high load."""
    templates = AsyncJinja2Templates(
        directory=AsyncPath("templates"),
        context_cache_size=1000,
        fragment_cache_size=1000,
    )

    # Create mock template
    mock_template = MagicMock(spec=Template)
    mock_template.blocks = {}
    mock_template.new_context = MagicMock(return_value={})

    # Add blocks to template - rebuild the entire blocks dict
    blocks_dict = {}
    for i in range(100):
        blocks_dict[f"block_{i}"] = MagicMock()
    mock_template.blocks = blocks_dict

    async def high_load_test():
        with patch.object(
            templates, "get_template_async", AsyncMock(return_value=mock_template)
        ):
            with patch.object(templates.env, "concat", return_value="test content"):
                # Simulate high cache usage
                for i in range(100):
                    await templates.render_fragment("test.html", f"block_{i}")

        return len(templates._block_cache)

    # Run benchmark
    result = await benchmark(high_load_test)
    assert result >= 0


@pytest.mark.asyncio
async def test_benchmark_stringio_vs_concat_performance() -> None:
    """Test StringIO vs concat performance for different fragment sizes."""
    templates = AsyncJinja2Templates(
        directory=AsyncPath("templates"), fragment_stringio_threshold=1024
    )

    # Create mock template
    mock_template = MagicMock(spec=Template)
    mock_template.blocks = {"test_block": MagicMock()}
    mock_template.new_context = MagicMock(return_value={})

    # Test with small content (should use concat)
    async def small_content_test():
        async def small_generator(ctx: t.Any) -> t.AsyncIterator[str]:
            yield "Small "
            yield "content"

        mock_template.blocks["test_block"].return_value = small_generator({})

        with patch.object(
            templates, "get_template_async", AsyncMock(return_value=mock_template)
        ):
            with patch.object(
                templates.env, "concat", return_value="Small content"
            ) as mock_concat:
                result = await templates.render_fragment(
                    "test.html", "test_block", small_data="tiny"
                )
                mock_concat.assert_called_once()
                return result

    # Test with large content (should use StringIO)
    async def large_content_test():
        async def large_generator(ctx: t.Any) -> t.AsyncIterator[str]:
            for i in range(100):
                yield f"Large content chunk {i} "

        mock_template.blocks["test_block"].return_value = large_generator({})

        with patch.object(
            templates, "get_template_async", AsyncMock(return_value=mock_template)
        ):
            result = await templates.render_fragment(
                "test.html",
                "test_block",
                large_data="x" * 2000,  # Triggers StringIO
            )
            return result

    # Run tests
    result1 = await small_content_test()
    result2 = await large_content_test()

    assert result1 is not None
    assert result2 is not None


@pytest.mark.asyncio
async def test_memory_usage_context_pooling_detailed() -> None:
    """Detailed test for context pooling memory usage."""
    templates = AsyncJinja2Templates(
        directory=AsyncPath("templates"), context_pool_size=50
    )

    # Fill the pool
    contexts = []
    for i in range(30):
        ctx = templates._get_pooled_context({"index": i, "data": f"value_{i}"})
        contexts.append(ctx)

    # Return contexts to pool
    for ctx in contexts:
        pool_size_before = len(templates._context_pool)
        templates._return_to_pool(ctx)
        pool_size_after = len(templates._context_pool)
        # Pool size should increase or stay the same
        assert pool_size_after >= pool_size_before

    # Pool should not exceed the limit
    assert len(templates._context_pool) <= 50

    # Get contexts from pool - they should be reused
    reused_context = templates._get_pooled_context({"new": "data"})
    # Check that it's a reused context (cleared and updated)
    assert "new" in reused_context
    assert len(templates._context_pool) < 50


@pytest.mark.asyncio
async def test_concurrent_template_rendering() -> None:
    """Test concurrent template rendering performance."""
    templates = AsyncJinja2Templates(directory=AsyncPath("templates"))

    # Create mock template
    mock_template = MagicMock(spec=Template)
    mock_template.render_async = AsyncMock(return_value="<h1>Concurrent Test</h1>")

    import asyncio

    async def render_template(index: int):
        with patch.object(
            templates, "get_template_async", AsyncMock(return_value=mock_template)
        ):
            return await templates.TemplateResponse(
                MagicMock(), "test.html", {"index": index}
            )

    # Render multiple templates concurrently
    tasks = [render_template(i) for i in range(20)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 20
    # All should complete successfully
    for result in results:
        assert result.status_code == 200


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_benchmark_cache_hit_vs_miss(benchmark) -> None:
    """Benchmark cache hit vs miss performance."""
    templates = AsyncJinja2Templates(
        directory=AsyncPath("templates"),
        fragment_cache_ttl=0.1,  # Short TTL for testing
    )

    # Create mock template
    mock_template = MagicMock(spec=Template)
    mock_template.blocks = {"test_block": MagicMock()}
    mock_template.new_context = MagicMock(return_value={})

    async def cache_test():
        with patch.object(
            templates, "get_template_async", AsyncMock(return_value=mock_template)
        ):
            with patch.object(templates.env, "concat", return_value="test content"):
                # First call - cache miss
                result1 = await templates.render_fragment("test.html", "test_block")

                # Second call - cache hit
                result2 = await templates.render_fragment("test.html", "test_block")

                return (result1, result2)

    # Run benchmark
    result = await benchmark(cache_test)
    assert result is not None
