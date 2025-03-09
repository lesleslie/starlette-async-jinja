# starlette-async-jinja

[![Code style: crackerjack](https://img.shields.io/badge/code%20style-crackerjack-000042)](https://github.com/lesleslie/crackerjack)

An asynchronous Jinja2 template integration for Starlette, built on top of the `jinja2-async-environment` package.

## Features

- **Fully async template rendering** - Load templates and render them asynchronously
- **Seamless Starlette integration** - Works with Starlette's request/response cycle
- **Template fragments** - Render specific blocks from templates
- **Template partials** - Include sub-templates with their own context using `render_block`

## Installation

```bash
pip install starlette-async-jinja
```

## Basic Usage

Import AsyncJinja2Templates:
```python
from starlette.applications import Starlette
from starlette.routing import Route
from aiopath import AsyncPath
from starlette_async_jinja import AsyncJinja2Templates

app = Starlette()
templates = AsyncJinja2Templates(directory=AsyncPath("templates"))

async def homepage(request):
    return await templates.TemplateResponse(request, "index.html", {"message": "Hello, world!"})

# Or using the alias
async def about(request):
    return await templates.render_template(request, "about.html", {"message": "About page"})

app.routes = [
    Route("/", homepage),
    Route("/about", about)
]
```

## Using Template Partials with `render_block`

In traditional Jinja2, macros are commonly used for reusable components. However, macros don't work properly in async templates. The `render_block` feature provides a more powerful alternative, inspired by [jinja_partials](https://github.com/mikeckennedy/jinja_partials).

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
    {{ await render_block('components/alert.html',
                          type='warning',
                          title='Attention!',
                          message='This is an important notice.',
                          dismissible=True) | safe }}

    {% for item in items %}
        {# Another component rendered with render_block #}
        {{ await render_block('components/card.html',
                             title=item.title,
                             content=item.description,
                             image_url=item.image) | safe }}
    {% endfor %}
</div>
{% endblock %}
```

### Important Notes on `render_block`

- Always use the `await` keyword when calling `render_block` within templates
- Apply the `safe` filter to prevent HTML escaping of the rendered content
- Each component only receives the variables explicitly passed to it
- `render_block` completely replaces the need for macros in async templates

## Using Template Fragments

Fragments allow you to render specific blocks from within a template.

```html
<!-- In your template (page.html) -->
{% block header %}
  <h1>Welcome to {{ site_name }}</h1>
{% endblock %}

{% block footer %}
  <footer>© {{ year }} {{ company_name }}</footer>
{% endblock %}
```

```python
# In your route handler:
async def render_header(request):
    content = await templates.render_fragment(
        "page.html", "header", site_name="My Awesome Site"
    )
    return HTMLResponse(content)
```

## JsonResponse

Enhanced JSON response using `msgspec` for faster serialization:

```python
from starlette_async_jinja import JsonResponse

async def api_endpoint(request):
    data = {"name": "John", "email": "john@example.com"}
    return JsonResponse(data)
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

- `async TemplateResponse(request, name, context={}, status_code=200, ...)` - Render a template to a response
- `async render_template(request, name, context={}, status_code=200, ...)` - Alias for TemplateResponse
- `async render_fragment(template_name, block_name, **kwargs)` - Render a specific block from a template
- `async render_block(template_name, **data)` - Render a template as a partial

### JsonResponse

Enhanced JSON response using `msgspec` for faster serialization.

### BlockNotFoundError

Exception raised when attempting to render a template block that doesn't exist.

## Acknowledgements

- [jinja_partials](https://github.com/mikeckennedy/jinja_partials)
- [jinja2-fragments](https://github.com/sponsfreixes/jinja2-fragments)
- [jinja2-async-environment](https://github.com/lesleslie/jinja2-async-environment)

## License

BSD-3-Clause
