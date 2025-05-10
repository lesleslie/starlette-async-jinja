# starlette-async-jinja

[![Code style: crackerjack](https://img.shields.io/badge/code%20style-crackerjack-000042)](https://github.com/lesleslie/crackerjack)
[![Python: 3.13+](https://img.shields.io/badge/python-3.13%2B-green)](https://www.python.org/downloads/)


An asynchronous Jinja2 template integration for Starlette and FastAPI, built on top of the `jinja2-async-environment` package.

## Features

- **Fully async template rendering** - Load templates and render them asynchronously
- **Seamless framework integration** - Works with Starlette and FastAPI request/response cycles
- **Template fragments** - Render specific blocks from templates
- **Template partials** - Include sub-templates with their own context using `render_block`
- **Fast JSON responses** - Enhanced JSON responses using `msgspec` for faster serialization
- **Context processors** - Add global context to all templates

## Installation

```bash
pip install starlette-async-jinja
```

## Requirements

- Python 3.13+
- Starlette
- Jinja2
- jinja2-async-environment
- anyio
- msgspec

## Basic Usage

### Starlette Example

```python
from starlette.applications import Starlette
from starlette.routing import Route
from anyio import Path as AsyncPath
from starlette_async_jinja import AsyncJinja2Templates

# Initialize templates with an async path
templates = AsyncJinja2Templates(directory=AsyncPath("templates"))

async def homepage(request):
    return await templates.TemplateResponse(request, "index.html", {"message": "Hello, world!"})

# Or using the alias
async def about(request):
    return await templates.render_template(request, "about.html", {"message": "About page"})

# Define routes
app = Starlette(routes=[
    Route("/", homepage),
    Route("/about", about)
])
```

### FastAPI Example

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from anyio import Path as AsyncPath
from starlette_async_jinja import AsyncJinja2Templates, JsonResponse

app = FastAPI()

# Initialize templates with an async path
templates = AsyncJinja2Templates(directory=AsyncPath("templates"))

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Render the homepage template."""
    return await templates.TemplateResponse(request, "index.html", {
        "title": "FastAPI with Async Jinja2",
        "message": "Welcome to FastAPI with async template rendering!"
    })

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """Render the about page template."""
    return await templates.render_template(request, "about.html", {
        "title": "About Us",
        "message": "Learn more about our company"
    })

@app.get("/api/data")
async def get_data():
    """Return JSON data using the optimized JsonResponse."""
    return JsonResponse({
        "items": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"}
        ]
    })
```

## Using Template Partials with `render_block`

In traditional Jinja2, macros are commonly used for reusable components. However, macros don't work properly in async templates.
The `render_block` feature provides a more powerful alternative, inspired by [jinja_partials](https://github.com/mikeckennedy/jinja_partials).

### Component Templates

**templates/components/alert.html**
```html
<div class="alert alert-{{ type | default('info') }}">
    <h4 class="alert-heading">{{ title }}</h4>
    <p>{{ message }}</p>
    {% if dismissible %}
    <button type="button" class="close" data-dismiss="alert">×</button>
    {% endif %}
</div>
```

### Using Components in Your Templates

**templates/index.html**
```html
{% extends "base.html" %}

{% block content %}
<div class="container">
    <h1>Welcome to {{ site_name }}</h1>

    {# Instead of a macro, use render_block #}
    {{ render_block('components/alert.html',
                     type='warning',
                     title='Attention!',
                     message='This is an important notice.',
                     dismissible=True) }}

    {% for item in items %}
        {# Another component rendered with render_block #}
        {{ render_block('components/card.html',
                         title=item.title,
                         content=item.description,
                         image_url=item.image) }}
    {% endfor %}
</div>
{% endblock %}
```

### Important Notes on `render_block`

- Each component only receives the variables explicitly passed to it
- `render_block` completely replaces the need for macros in async templates
- The `markup=True` parameter (default) ensures proper HTML escaping

## Context Processors

Context processors allow you to add global context to all templates:

```python
def global_context(request):
    return {
        "site_name": "My Awesome Site",
        "current_year": 2024
    }

templates = AsyncJinja2Templates(
    directory=AsyncPath("templates"),
    context_processors=[global_context]
)

# Now all templates will have access to site_name and current_year
```

### Context Processors with FastAPI

```python
from fastapi import FastAPI, Request
from anyio import Path as AsyncPath
from starlette_async_jinja import AsyncJinja2Templates

app = FastAPI()

# Define context processors
def global_context(request):
    return {
        "site_name": "My FastAPI App",
        "current_year": 2024,
        "version": "1.0.0"
    }

def user_context(request):
    # In a real app, you might get this from a session or JWT
    return {
        "user": {"name": "Guest User"}
    }

# Initialize templates with context processors
templates = AsyncJinja2Templates(
    directory=AsyncPath("templates"),
    context_processors=[global_context, user_context]
)

@app.get("/")
async def homepage(request: Request):
    # These variables will be automatically available in all templates:
    # - site_name
    # - current_year
    # - version
    # - user
    return await templates.TemplateResponse(request, "index.html", {
        "title": "Home Page"
    })
```

## Using Template Fragments

Fragments allow you to render specific blocks from within a template:

```html
<!-- In your template (page.html) -->
{% block header %}
  <h1>Welcome to {{ site_name }}</h1>
{% endblock %}

{% block footer %}
  <footer>© {{ year }} {{ company_name }}</footer>
{% endblock %}
```

### Starlette Example

```python
from starlette.responses import HTMLResponse

# In your route handler:
async def render_header(request):
    content = await templates.render_fragment(
        "page.html", "header", site_name="My Awesome Site"
    )
    return HTMLResponse(content)
```

### FastAPI Example

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()
templates = AsyncJinja2Templates(directory=AsyncPath("templates"))

@app.get("/header", response_class=HTMLResponse)
async def get_header(request: Request):
    """Return just the header fragment."""
    content = await templates.render_fragment(
        "page.html", "header", site_name="My FastAPI Site"
    )
    return HTMLResponse(content)

@app.get("/footer", response_class=HTMLResponse)
async def get_footer(request: Request):
    """Return just the footer fragment."""
    content = await templates.render_fragment(
        "page.html", "footer", year=2024, company_name="My Company"
    )
    return HTMLResponse(content)
```

## JsonResponse

Enhanced JSON response using `msgspec` for faster serialization:

```python
from starlette_async_jinja import JsonResponse

# Starlette example
async def api_endpoint(request):
    data = {"name": "John", "email": "john@example.com"}
    return JsonResponse(data)

# FastAPI example
@app.get("/api/user")
async def get_user():
    data = {"name": "John", "email": "john@example.com"}
    return JsonResponse(data)  # Faster than FastAPI's default JSONResponse
```

## Issues and Limitations

- Only [asynchronous template loaders](https://github.com/lesleslie/jinja2-async-environment/blob/main/jinja2_async_environment/loaders.py) are fully supported
- The Jinja bytecodecache requires an asynchronous Redis backend
- Jinja macros don't work in async mode - use `render_block` instead

## API Reference

### AsyncJinja2Templates

```python
templates = AsyncJinja2Templates(
    directory=AsyncPath("templates"),
    context_processors=[global_context],
    autoescape=True,
    # Additional Jinja2 environment options
)
```

#### Methods

- `async TemplateResponse(request, name, context={}, status_code=200, headers=None, media_type=None, background=None)` - Render a template to a response
- `async render_template(request, name, context={}, status_code=200, headers=None, media_type=None, background=None)` - Alias for TemplateResponse
- `async render_fragment(template_name, block_name, **kwargs)` - Render a specific block from a template
- `async render_block(template_name, markup=True, **data)` - Render a template as a partial with optional markup escaping (default: True)
- `async get_template_async(name)` - Get a template by name

### JsonResponse

Enhanced JSON response using `msgspec` for faster serialization.

### BlockNotFoundError

Exception raised when attempting to render a template block that doesn't exist.

## Advanced Usage

### With Redis Bytecode Caching

For production environments, you can use Redis for bytecode caching:

```python
from anyio import Path as AsyncPath
from starlette_async_jinja import AsyncJinja2Templates
from jinja2_async_environment.bccache import AsyncRedisBytecodeCache
import redis.asyncio as redis

# Create a Redis client
redis_client = redis.Redis(host="localhost", port=6379, db=0)

# Set up bytecode caching
bytecode_cache = AsyncRedisBytecodeCache(redis_client, prefix="jinja2_")

# Create templates with caching
templates = AsyncJinja2Templates(
    directory=AsyncPath("templates"),
    bytecode_cache=bytecode_cache
)
```

### Using Different Loaders

You can use different loader types from `jinja2-async-environment`:

```python
from anyio import Path as AsyncPath
from starlette_async_jinja import AsyncJinja2Templates
from jinja2_async_environment.loaders import (
    AsyncFileSystemLoader,
    AsyncPackageLoader,
    AsyncChoiceLoader
)

# Load templates from filesystem
fs_loader = AsyncFileSystemLoader('templates')

# Load templates from a Python package
package_loader = AsyncPackageLoader('your_package', 'templates')

# Create a loader that tries multiple sources
choice_loader = AsyncChoiceLoader([
    fs_loader,  # First try the filesystem
    package_loader  # Then try the package
])

# Create templates with the choice loader
templates = AsyncJinja2Templates(
    directory=AsyncPath("templates"),  # This is still required
    loader=choice_loader  # But we override the loader
)
```

## Type Annotations

This package is fully typed with Python's type annotations and is compatible with static type checkers like mypy and pyright.

## Acknowledgements

- [jinja_partials](https://github.com/mikeckennedy/jinja_partials)
- [jinja2-fragments](https://github.com/sponsfreixes/jinja2-fragments)
- [jinja2-async-environment](https://github.com/lesleslie/jinja2-async-environment)

## License

BSD-3-Clause
