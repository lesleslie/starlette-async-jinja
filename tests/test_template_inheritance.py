"""Tests for Jinja2 template inheritance in async environment.

These tests verify that:
1. Child templates can extend parent templates
2. Parent templates are loaded correctly
3. Blocks from parent templates work properly
4. The async environment handles inheritance correctly
5. Multiple levels of inheritance work (grandparent -> parent -> child)
"""

from pathlib import Path

import pytest
from jinja2_async_environment import AsyncEnvironment, AsyncFileSystemLoader


@pytest.mark.asyncio
async def test_simple_inheritance(tmp_path: Path):
    """Test basic template inheritance (child extends parent)."""
    # Create parent template with a block
    parent = tmp_path / "parent.html"
    parent.write_text("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{% block title %}Default Title{% endblock %}</title>
    </head>
    <body>
        {% block content %}Default Content{% endblock %}
    </body>
    </html>
    """)

    # Create child template that extends parent
    child = tmp_path / "child.html"
    child.write_text("""
    {% extends "parent.html" %}

    {% block title %}Custom Title{% endblock %}
    {% block content %}<h1>Custom Content</h1>{% endblock %}
    """)

    # Create async environment and load child template
    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    template = await env.get_template_async("child.html")
    result = await template.render_async()

    # Verify blocks were overridden
    assert "Custom Title" in result
    assert "<h1>Custom Content</h1>" in result
    assert "Default Title" not in result
    assert "Default Content" not in result


@pytest.mark.asyncio
async def test_parent_template_with_defaults(tmp_path: Path):
    """Test that parent template defaults work when child doesn't override."""
    # Create parent template
    parent = tmp_path / "base.html"
    parent.write_text("""
    <!DOCTYPE html>
    <html>
    <head><title>{% block title %}Default{% endblock %}</title></head>
    <body>
        <header>{% block header %}Default Header{% endblock %}</header>
        <main>{% block content %}{% endblock %}</main>
        <footer>{% block footer %}Default Footer{% endblock %}</footer>
    </body>
    </html>
    """)

    # Create child template that only overrides some blocks
    child = tmp_path / "page.html"
    child.write_text("""
    {% extends "base.html" %}

    {% block title %}My Page{% endblock %}
    {% block content %}<p>Page Content</p>{% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    template = await env.get_template_async("page.html")
    result = await template.render_async()

    # Verify overridden blocks
    assert "My Page" in result
    assert "<p>Page Content</p>" in result

    # Verify default blocks from parent
    assert "Default Header" in result
    assert "Default Footer" in result


@pytest.mark.asyncio
async def test_super_inheritance(tmp_path: Path):
    """Test that {{ super() }} works to call parent block."""
    # Create parent template
    parent = tmp_path / "parent.html"
    parent.write_text("""
    {% block content %}
        <p>Parent Content</p>
    {% endblock %}
    """)

    # Create child template that uses super()
    child = tmp_path / "child.html"
    child.write_text("""
    {% extends "parent.html" %}

    {% block content %}
        {{ super() }}
        <p>Additional Child Content</p>
    {% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    template = await env.get_template_async("child.html")
    result = await template.render_async()

    # Verify both parent and child content
    assert "Parent Content" in result
    assert "Additional Child Content" in result


@pytest.mark.asyncio
async def test_multi_level_inheritance(tmp_path: Path):
    """Test inheritance across multiple levels (grandparent -> parent -> child)."""
    # Create grandparent template
    grandparent = tmp_path / "grandparent.html"
    grandparent.write_text("""
    <!DOCTYPE html>
    <html>
    <head><title>{% block title %}Grandparent{% endblock %}</title></head>
    <body>
        {% block header %}<header>Grandparent Header</header>{% endblock %}
        {% block content %}<main>Grandparent Content</main>{% endblock %}
    </body>
    </html>
    """)

    # Create parent template that extends grandparent
    parent = tmp_path / "parent.html"
    parent.write_text("""
    {% extends "grandparent.html" %}

    {% block title %}Parent{% endblock %}
    {% block header %}{{ super() }} <nav>Parent Nav</nav>{% endblock %}
    """)

    # Create child template that extends parent
    child = tmp_path / "child.html"
    child.write_text("""
    {% extends "parent.html" %}

    {% block title %}Child{% endblock %}
    {% block content %}<main>Child Content</main>{% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    template = await env.get_template_async("child.html")
    result = await template.render_async()

    # Verify inheritance chain
    assert "Child" in result  # Child overrides parent's title
    assert "Grandparent Header" in result  # From grandparent
    assert "Parent Nav" in result  # Parent added to header
    assert "Child Content" in result  # Child overrides content
    assert "Grandparent Content" not in result  # Overridden by child


@pytest.mark.asyncio
async def test_multiple_blocks_in_child(tmp_path: Path):
    """Test child template overriding multiple blocks."""
    # Create parent template
    parent = tmp_path / "base.html"
    parent.write_text("""
    <html>
    <head><title>{% block title %}Base Title{% endblock %}</title></head>
    <body>
        <header>{% block header %}Base Header{% endblock %}</header>
        <main>{% block content %}Base Content{% endblock %}</main>
        <footer>{% block footer %}Base Footer{% endblock %}</footer>
    </body>
    </html>
    """)

    # Create child template that overrides multiple blocks
    child = tmp_path / "page.html"
    child.write_text("""
    {% extends "base.html" %}

    {% block title %}Page Title{% endblock %}
    {% block header %}Page Header{% endblock %}
    {% block content %}Page Content{% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    template = await env.get_template_async("page.html")
    result = await template.render_async()

    # Verify all overridden blocks
    assert "Page Title" in result
    assert "Page Header" in result
    assert "Page Content" in result
    # Footer should use parent's default
    assert "Base Footer" in result


@pytest.mark.asyncio
async def test_nested_blocks(tmp_path: Path):
    """Test nested blocks within blocks."""
    # Create parent template with nested blocks
    parent = tmp_path / "parent.html"
    parent.write_text("""
    {% block outer %}
        <div class="outer">
            <h2>Outer Start</h2>
            {% block inner %}
                <p>Inner Default</p>
            {% endblock %}
            <h2>Outer End</h2>
        </div>
    {% endblock %}
    """)

    # Create child template that overrides inner block
    child = tmp_path / "child.html"
    child.write_text("""
    {% extends "parent.html" %}

    {% block outer %}
        {{ super() }}
    {% endblock %}

    {% block inner %}
        <p>Inner Custom</p>
    {% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    template = await env.get_template_async("child.html")
    result = await template.render_async()

    # Verify nested blocks work
    assert "Outer Start" in result
    assert "Outer End" in result
    assert "Inner Custom" in result
    assert "Inner Default" not in result


@pytest.mark.asyncio
async def test_inheritance_with_context(tmp_path: Path):
    """Test that context variables work correctly with inheritance."""
    # Create parent template
    parent = tmp_path / "base.html"
    parent.write_text("""
    <!DOCTYPE html>
    <html>
    <head><title>{{ page_title }} - {% block title %}Site{% endblock %}</title></head>
    <body>
        <h1>{{ page_title }}</h1>
        {% block content %}{% endblock %}
    </body>
    </html>
    """)

    # Create child template
    child = tmp_path / "page.html"
    child.write_text("""
    {% extends "base.html" %}

    {% block title %}{{ page_title }}{% endblock %}
    {% block content %}
        <p>{{ page_description }}</p>
    {% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    template = await env.get_template_async("page.html")
    result = await template.render_async(
        page_title="My Page",
        page_description="My Description"
    )

    # Verify context variables propagate through inheritance
    assert "My Page - My Page" in result  # Both title blocks use context
    assert "<h1>My Page</h1>" in result
    assert "My Description" in result


@pytest.mark.asyncio
async def test_dynamic_inheritance(tmp_path: Path):
    """Test dynamic template inheritance (template name in variable)."""
    # Create parent templates
    parent1 = tmp_path / "parent1.html"
    parent1.write_text("""
    <div class="parent1">
        {% block content %}Parent 1 Content{% endblock %}
    </div>
    """)

    parent2 = tmp_path / "parent2.html"
    parent2.write_text("""
    <div class="parent2">
        {% block content %}Parent 2 Content{% endblock %}
    </div>
    """)

    # Create child that chooses parent dynamically
    child_template = """
    {% extends parent_template %}

    {% block content %}Child Content for {{ parent_template }}{% endblock %}
    """

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)
    template = env.from_string(child_template)

    # Test with parent1
    result1 = await template.render_async(parent_template="parent1.html")
    assert "parent1" in result1
    assert "Child Content for parent1.html" in result1

    # Test with parent2
    result2 = await template.render_async(parent_template="parent2.html")
    assert "parent2" in result2
    assert "Child Content for parent2.html" in result2


@pytest.mark.asyncio
async def test_inheritance_with_macros(tmp_path: Path):
    """Test that macros work correctly with template inheritance."""
    # Create parent template with macro
    parent = tmp_path / "base.html"
    parent.write_text("""
    {% macro render_button(label) %}
        <button>{{ label }}</button>
    {% endmacro %}

    <!DOCTYPE html>
    <html>
    <body>
        {% block content %}{% endblock %}
    </body>
    </html>
    """)

    # Create child template that uses parent's macro
    child = tmp_path / "page.html"
    child.write_text("""
    {% extends "base.html" %}

    {% block content %}
        {{ render_button("Click Me") }}
    {% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    template = await env.get_template_async("page.html")
    result = await template.render_async()

    # Verify macro from parent is accessible in child
    assert '<button>Click Me</button>' in result


@pytest.mark.asyncio
async def test_sibling_template_inheritance(tmp_path: Path):
    """Test multiple siblings extending the same parent."""
    # Create parent template
    parent = tmp_path / "base.html"
    parent.write_text("""
    <!DOCTYPE html>
    <html>
    <head><title>{% block title %}Base{% endblock %}</title></head>
    <body>
        <nav>{% block nav %}Base Nav{% endblock %}</nav>
        <main>{% block content %}Base Content{% endblock %}</main>
    </body>
    </html>
    """)

    # Create two sibling templates
    sibling1 = tmp_path / "page1.html"
    sibling1.write_text("""
    {% extends "base.html" %}
    {% block title %}Page 1{% endblock %}
    {% block content %}<h1>Page 1 Content</h1>{% endblock %}
    """)

    sibling2 = tmp_path / "page2.html"
    sibling2.write_text("""
    {% extends "base.html" %}
    {% block title %}Page 2{% endblock %}
    {% block content %}<h1>Page 2 Content</h1>{% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    # Render first sibling
    template1 = await env.get_template_async("page1.html")
    result1 = await template1.render_async()
    assert "Page 1" in result1
    assert "Page 1 Content" in result1
    assert "Base Nav" in result1  # Parent's default

    # Render second sibling
    template2 = await env.get_template_async("page2.html")
    result2 = await template2.render_async()
    assert "Page 2" in result2
    assert "Page 2 Content" in result2
    assert "Base Nav" in result2  # Parent's default


@pytest.mark.asyncio
async def test_conditional_inheritance(tmp_path: Path):
    """Test inheritance with conditional blocks."""
    # Create parent template
    parent = tmp_path / "base.html"
    parent.write_text("""
    <div class="container">
        {% block content %}{% endblock %}
        {% block footer %}
            {% if show_footer %}
                <footer>Site Footer</footer>
            {% endif %}
        {% endblock %}
    </div>
    """)

    # Create child template with conditional footer
    child = tmp_path / "page.html"
    child.write_text("""
    {% extends "base.html" %}

    {% block content %}
        <h1>Page Content</h1>
    {% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    template = await env.get_template_async("page.html")

    # Test with footer shown
    result_with_footer = await template.render_async(show_footer=True)
    assert "Page Content" in result_with_footer
    assert "Site Footer" in result_with_footer

    # Test with footer hidden
    result_without_footer = await template.render_async(show_footer=False)
    assert "Page Content" in result_without_footer
    assert "Site Footer" not in result_without_footer


@pytest.mark.asyncio
async def test_filter_in_inheritance(tmp_path: Path):
    """Test that filters work correctly across inheritance."""
    # Create parent template
    parent = tmp_path / "base.html"
    parent.write_text("""
    <div class="base">
        <h1>{{ title|upper }}</h1>
        {% block content %}{% endblock %}
    </div>
    """)

    # Create child template that uses filters
    child = tmp_path / "page.html"
    child.write_text("""
    {% extends "base.html" %}

    {% block content %}
        <p>{{ content|lower }}</p>
    {% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    template = await env.get_template_async("page.html")
    result = await template.render_async(title="hello world", content="HELLO WORLD")

    # Verify filters work in both parent and child
    assert "<h1>HELLO WORLD</h1>" in result  # Parent's filter
    assert "<p>hello world</p>" in result  # Child's filter


@pytest.mark.asyncio
async def test_loop_in_inheritance(tmp_path: Path):
    """Test that loops work correctly in inherited templates."""
    # Create parent template
    parent = tmp_path / "base.html"
    parent.write_text("""
    <ul>
        {% block items %}{% endblock %}
    </ul>
    """)

    # Create child template with loop
    child = tmp_path / "page.html"
    child.write_text("""
    {% extends "base.html" %}

    {% block items %}
        {% for item in items %}
            <li>{{ item }}</li>
        {% endfor %}
    {% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    template = await env.get_template_async("page.html")
    result = await template.render_async(items=["Apple", "Banana", "Cherry"])

    # Verify loop works
    assert "<li>Apple</li>" in result
    assert "<li>Banana</li>" in result
    assert "<li>Cherry</li>" in result


@pytest.mark.slow
@pytest.mark.asyncio
async def test_inheritance_performance(tmp_path: Path):
    """Test that inheritance doesn't cause performance issues."""
    import time

    # Create parent template
    parent = tmp_path / "base.html"
    parent.write_text("""
    <!DOCTYPE html>
    <html>
    <head><title>{% block title %}Base{% endblock %}</title></head>
    <body>
        {% block content %}{% endblock %}
    </body>
    </html>
    """)

    # Create child template
    child = tmp_path / "child.html"
    child.write_text("""
    {% extends "base.html" %}

    {% block title %}Child{% endblock %}
    {% block content %}<p>Content</p>{% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    env = AsyncEnvironment(loader=loader, autoescape=False, enable_async=True)

    # Measure template loading time
    start = time.perf_counter()
    template = await env.get_template_async("child.html")
    load_time = time.perf_counter() - start

    # Measure rendering time (multiple iterations)
    iterations = 100
    start = time.perf_counter()
    for _ in range(iterations):
        await template.render_async()
    render_time = time.perf_counter() - start

    # Performance assertions
    assert load_time < 0.1, f"Template loading took {load_time:.3f}s, expected < 0.1s"
    assert render_time / iterations < 0.01, f"Average render time {render_time/iterations:.4f}s, expected < 0.01s"


@pytest.mark.asyncio
async def test_cache_invalidation_with_inheritance(tmp_path: Path):
    """Test that template cache is honored across inheritance.

    Verifies that once a child template (with a parent via {% extends %})
    has been loaded and rendered, subsequent fetches of the same template
    return the cached compiled version. Changes to the parent template
    on disk MUST NOT leak into rendered output until the cache is
    explicitly invalidated or the environment is reloaded.

    The parent exposes two blocks. The child overrides only one of them
    (``content``) and lets the second block (``footer``) fall through.
    We mutate the parent on disk after the first render -- if the cache
    is honored, the original footer text must still appear in the second
    render; if the cache is broken and the parent is re-read from disk,
    the mutated footer would leak through.
    """
    # Parent exposes two blocks; "footer" is what we will mutate.
    parent = tmp_path / "base.html"
    parent.write_text("""
    {% block content %}Base Content{% endblock %}
    {% block footer %}Original Footer{% endblock %}
    """)

    # Child overrides only "content" and inherits "footer" from parent.
    child = tmp_path / "child.html"
    child.write_text("""
    {% extends "base.html" %}
    {% block content %}Child Content{% endblock %}
    """)

    loader = AsyncFileSystemLoader(tmp_path)
    # auto_reload=False ensures Jinja2 will NOT re-stat the parent template
    # between renders. That's the cache regime under test.
    env = AsyncEnvironment(
        loader=loader, autoescape=False, enable_async=True, auto_reload=False
    )
    template = await env.get_template_async("child.html")
    result1 = await template.render_async()
    assert "Child Content" in result1
    assert "Original Footer" in result1

    # Mutate BOTH parent blocks on disk AFTER the cache has been warmed.
    # The mutated footer is the load-bearing signal -- it can only appear
    # in the next render if the parent was re-read from disk instead of
    # served from cache.
    parent.write_text("""
    {% block content %}Modified Base Content{% endblock %}
    {% block footer %}Mutated Footer{% endblock %}
    """)

    # Second fetch + render must come from cache.
    template2 = await env.get_template_async("child.html")
    result2 = await template2.render_async()

    # Cache honored: child override still wins for "content"...
    assert "Child Content" in result2
    # ...the inherited block keeps its ORIGINAL parent text...
    assert "Original Footer" in result2
    # ...and the post-cache mutation of the parent is invisible.
    assert "Mutated Footer" not in result2
    assert "Modified Base Content" not in result2
