"""Tests for Jinja2 macro support in async templates."""

from pathlib import Path

import pytest
from anyio import Path as AsyncPath
from starlette_async_jinja.responses import AsyncJinja2Templates


@pytest.mark.asyncio
async def test_render_block_with_macro_calls(tmp_path: Path) -> None:
    """Test render_block works with templates containing macro calls."""
    template_dir = AsyncPath(tmp_path / "templates")
    await template_dir.mkdir()

    # Create template with macros
    template_content = """
{% macro alert(type, message) -%}
<div class="alert alert-{{ type }}">{{ message }}</div>
{%- endmacro %}

<h1>Page Title</h1>
{{ alert('info', 'Welcome message') }}
<p>Content here</p>
"""
    template_file = template_dir / "page_with_macros.html"
    await template_file.write_text(template_content)

    templates = AsyncJinja2Templates(directory=template_dir, enable_async=True)

    # Test render_block with macro-containing template
    result = await templates.render_block("page_with_macros.html")

    assert "<h1>Page Title</h1>" in result
    assert '<div class="alert alert-info">Welcome message</div>' in result
    assert "<p>Content here</p>" in result


@pytest.mark.asyncio
async def test_direct_macro_access_basic(tmp_path: Path) -> None:
    """Test basic direct access to macros via template module."""
    template_dir = AsyncPath(tmp_path / "templates")
    await template_dir.mkdir()

    # Create simple template with one macro
    macro_content = """
{% macro greeting(name) -%}
Hello, {{ name }}!
{%- endmacro %}
"""
    macro_file = template_dir / "simple_macro.html"
    await macro_file.write_text(macro_content)

    templates = AsyncJinja2Templates(directory=template_dir, enable_async=True)

    # Test direct macro access
    template = await templates.env.get_template_async("simple_macro.html")
    module = await template.make_module_async()

    # Test greeting macro exists and is callable
    assert hasattr(module, "greeting")
    greeting_coro = module.greeting("World")  # type: ignore[attr-defined]

    # Macro returns a coroutine that needs to be awaited
    greeting_result = await greeting_coro
    assert greeting_result == "Hello, World!"


@pytest.mark.asyncio
async def test_macro_compilation_basic(tmp_path: Path) -> None:
    """Test that basic macros compile correctly in async environment."""
    template_dir = AsyncPath(tmp_path / "templates")
    await template_dir.mkdir()

    # Simple macro that should compile without issues
    simple_macro_content = """
{% macro button(text) -%}
<button>{{ text }}</button>
{%- endmacro %}

{{ button('Click Me') }}
"""
    simple_file = template_dir / "simple_button.html"
    await simple_file.write_text(simple_macro_content)

    templates = AsyncJinja2Templates(directory=template_dir, enable_async=True)

    # Test compilation and rendering
    result = await templates.render_block("simple_button.html")

    assert "<button>Click Me</button>" in result


@pytest.mark.asyncio
async def test_macro_error_handling(tmp_path: Path) -> None:
    """Test error handling with malformed macros."""
    template_dir = AsyncPath(tmp_path / "templates")
    await template_dir.mkdir()

    # Template with syntax error in macro
    bad_macro_content = """
{% macro broken_macro(param %}
This macro has a syntax error
{% endmacro %}
"""
    bad_file = template_dir / "bad_macros.html"
    await bad_file.write_text(bad_macro_content)

    templates = AsyncJinja2Templates(directory=template_dir, enable_async=True)

    # Should raise an error when trying to load template
    with pytest.raises(Exception):  # Jinja2 will raise TemplateSyntaxError
        await templates.env.get_template_async("bad_macros.html")


@pytest.mark.unit
def test_macro_support_in_environment_creation(tmp_path: Path) -> None:
    """Test that AsyncJinja2Templates enables async mode for macro support."""
    template_dir = AsyncPath(tmp_path)

    templates = AsyncJinja2Templates(directory=template_dir, enable_async=True)

    # Verify async environment is created with proper settings
    assert templates.env.enable_async is True
    assert hasattr(templates.env, "get_template_async")
    # Note: compile_async is not a standard method, so we check the core async capability


@pytest.mark.asyncio
async def test_macro_with_parameters(tmp_path: Path) -> None:
    """Test macros with parameters work correctly."""
    template_dir = AsyncPath(tmp_path / "templates")
    await template_dir.mkdir()

    # Template with macro that takes parameters
    template_content = """
{% macro show_greeting(name) -%}
Hello, {{ name }}!
{%- endmacro %}

{{ show_greeting('World') }}
"""
    template_file = template_dir / "param_macro.html"
    await template_file.write_text(template_content)

    templates = AsyncJinja2Templates(directory=template_dir, enable_async=True)

    # Test macro with parameters
    result = await templates.render_block("param_macro.html")
    assert "Hello, World!" in result
