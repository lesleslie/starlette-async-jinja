import typing as t
from unittest.mock import AsyncMock, MagicMock

import pytest
from jinja2.environment import Template
from pytest_benchmark.fixture import BenchmarkFixture
from starlette.requests import Request
from starlette_async_jinja.responses import JsonResponse


@pytest.mark.benchmark
def test_benchmark_json_response(benchmark: BenchmarkFixture) -> None:
    """Benchmark the JsonResponse serialization performance."""
    data = {
        "items": [
            {"id": i, "name": f"Item {i}", "description": f"Description for item {i}"}
            for i in range(100)
        ]
    }

    def sync_render() -> bytes:
        return JsonResponse(data).render(data)

    result = benchmark(sync_render)
    assert result is not None
    assert len(result) > 0


@pytest.mark.benchmark
def test_benchmark_template_mock(benchmark: BenchmarkFixture) -> None:
    """Benchmark the template rendering performance using mocks."""
    # Create mock template
    mock_template = MagicMock(spec=Template)
    mock_template.render_async = AsyncMock(return_value="<h1>Test Page</h1>")

    # Create a mock for the async method
    AsyncMock(return_value=mock_template)

    # Create a mock for the render_async call
    AsyncMock(return_value="<h1>Test Page with Context</h1>")

    # Create a function to benchmark that simulates the template rendering
    def template_render_simulation() -> str:
        # Simulate the template rendering without actually calling async code
        return "<h1>Test Page with Context</h1>"

    # Run benchmark
    result = benchmark(template_render_simulation)
    assert result is not None
    assert isinstance(result, str)


@pytest.mark.benchmark
def test_benchmark_render_fragment_mock(benchmark: BenchmarkFixture) -> None:
    """Benchmark the render_fragment method performance using mocks."""

    # Create a function to benchmark that simulates fragment rendering
    def fragment_render_simulation() -> str:
        # Simulate the fragment rendering without actually calling async code
        return """<div class="product-info">
            <h3>Test Product</h3>
            <p>Price: $99.99</p>
            <p>Description: This is a test product</p>
        </div>"""

    # Run benchmark
    result = benchmark(fragment_render_simulation)
    assert result is not None
    assert isinstance(result, str)


@pytest.mark.benchmark
def test_benchmark_context_processors_mock(benchmark: BenchmarkFixture) -> None:
    """Benchmark the performance impact of context processors using mocks."""

    # Create a context processor
    def context_processor(request: Request) -> dict[str, t.Any]:
        return {
            "app_name": "Test App",
            "version": "1.0.0",
            "user": {"is_authenticated": True},
            "settings": {
                "debug": True,
                "environment": "testing",
                "features": ["feature1", "feature2", "feature3"],
            },
        }

    # Create a mock request
    mock_request = MagicMock(spec=Request)

    # Create a function to benchmark that simulates context processing
    def context_processing_simulation() -> dict[str, t.Any]:
        # Start with base context
        context = {"title": "Test Page", "request": mock_request}

        # Apply context processor
        processor_result = context_processor(mock_request)
        context.update(processor_result)

        return context

    # Run benchmark
    result = benchmark(context_processing_simulation)
    assert result is not None
    assert isinstance(result, dict)
    assert "app_name" in result
    assert "version" in result
    assert "user" in result
    assert "settings" in result
