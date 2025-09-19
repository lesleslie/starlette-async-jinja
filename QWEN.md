# Project Context for starlette-async-jinja

## Project Overview

This is a Python library that provides asynchronous Jinja2 template integration for Starlette and FastAPI frameworks. The library is built on top of the `jinja2-async-environment` package and offers fully async template rendering capabilities.

### Key Features

- **Fully async template rendering** - Load templates and render them asynchronously
- **Seamless framework integration** - Works with both Starlette and FastAPI request/response cycles
- **Template fragments** - Render specific blocks from templates
- **Template partials** - Include sub-templates with their own context using `render_block`
- **Fast JSON responses** - Enhanced JSON responses using `msgspec` for faster serialization
- **Context processors** - Add global context to all templates
- **Performance optimizations** - Context processor caching, fragment caching, and memory pooling
- **Configurable caching** - Fine-tune cache sizes and TTL for optimal performance

### Technologies Used

- Python 3.13+
- Starlette
- Jinja2
- jinja2-async-environment
- anyio
- msgspec

## Project Structure

```
starlette-async-jinja/
├── starlette_async_jinja/     # Main source code
│   ├── __init__.py           # Package exports
│   └── responses.py          # Core implementation
├── tests/                    # Test suite
│   ├── test_responses.py     # Unit tests for core functionality
│   ├── test_e2e.py           # End-to-end tests
│   ├── test_integration.py   # Integration tests
│   ├── test_json_response.py # JSON response tests
│   ├── conftest.py           # Test configuration and fixtures
│   └── ...                   # Other test files
├── README.md                 # Project documentation
├── pyproject.toml            # Project configuration and dependencies
└── ...                       # Other configuration files
```

## Core Components

### AsyncJinja2Templates

The main class that provides async template rendering functionality:

- `TemplateResponse()` - Render a template to an HTTP response
- `render_template()` - Alias for TemplateResponse
- `render_fragment()` - Render a specific block from a template
- `render_block()` - Render a template as a partial with optional markup escaping
- `get_template_async()` - Get a template by name

### JsonResponse

An enhanced JSON response class using `msgspec` for faster serialization compared to the default JSONResponse.

### Key Features Implementation

1. **Context Processors**: Allow adding global context to all templates with automatic caching
1. **Fragment Rendering**: Render specific named blocks from templates with caching optimizations
1. **Template Partials**: Use `render_block` to render entire template files as reusable components
1. **Performance Optimizations**:
   - Context processor caching
   - Fragment block function caching
   - Context object pooling
   - Adaptive string building (StringIO for large fragments)

## Development Workflow

### Building and Testing

This project uses standard Python tooling:

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=starlette_async_jinja

# Type checking
pyright

# Code formatting and linting
ruff check .
ruff format .
```

### Dependencies

Dependencies are managed through `pyproject.toml` using uv/pip:

- **Runtime dependencies**: anyio, jinja2, jinja2-async-environment, msgspec, starlette
- **Development dependencies**: crackerjack, httpx

### Code Quality Tools

The project uses several code quality tools configured in `pyproject.toml`:

- **Ruff**: For linting and formatting
- **Pyright**: For type checking
- **Pytest**: For testing with coverage
- **Bandit**: For security scanning
- **Vulture**: For dead code detection

## Usage Examples

### Basic Usage (Starlette)

```python
from starlette.applications import Starlette
from starlette.routing import Route
from anyio import Path as AsyncPath
from starlette_async_jinja import AsyncJinja2Templates

templates = AsyncJinja2Templates(directory=AsyncPath("templates"))


async def homepage(request):
    return await templates.TemplateResponse(
        request, "index.html", {"message": "Hello, world!"}
    )


app = Starlette(routes=[Route("/", homepage)])
```

### FastAPI Integration

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from anyio import Path as AsyncPath
from starlette_async_jinja import AsyncJinja2Templates

app = FastAPI()
templates = AsyncJinja2Templates(directory=AsyncPath("templates"))


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return await templates.TemplateResponse(
        request, "index.html", {"title": "FastAPI with Async Jinja2"}
    )
```

### Context Processors

```python
def global_context(request):
    return {"site_name": "My Awesome Site", "current_year": 2024}


templates = AsyncJinja2Templates(
    directory=AsyncPath("templates"), context_processors=[global_context]
)
```

### Template Fragments

```python
# Render a specific block from a template
content = await templates.render_fragment(
    "page.html", "header", site_name="My Awesome Site"
)
```

## Performance Optimizations

The library includes several built-in performance optimizations:

1. **Context Processor Caching**: Automatically cache context processor results
1. **Fragment Rendering Optimizations**:
   - Block function caching
   - Context object pooling
   - Adaptive string building (StringIO for large fragments)
1. **Configurable Cache Settings**:
   - `context_cache_size`: Number of cached context entries
   - `context_cache_ttl`: Cache TTL in seconds
   - `fragment_cache_size`: Max cached block functions
   - `fragment_cache_ttl`: Block cache TTL in seconds

## Development Conventions

1. **Type Safety**: Full type annotations throughout the codebase
1. **Async-First**: All operations are designed to be asynchronous
1. **Error Handling**: Proper exception handling with meaningful error messages
1. **Testing**: Comprehensive test suite with unit, integration, and end-to-end tests
1. **Documentation**: Clear docstrings and examples in README
1. **Code Quality**: Strict linting and formatting standards

## Common Development Tasks

1. **Adding new features**: Extend the AsyncJinja2Templates class in responses.py
1. **Writing tests**: Add test files in the tests/ directory following existing patterns
1. **Performance optimization**: Use the built-in caching and pooling mechanisms
1. **Documentation**: Update README.md with usage examples and API references
