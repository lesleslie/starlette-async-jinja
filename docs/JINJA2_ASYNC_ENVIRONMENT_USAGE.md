# jinja2-async-environment Usage Pattern for starlette-async-jinja

**Date**: 2025-10-26
**Component**: starlette-async-jinja AsyncJinja2Templates
**Status**: Critical Action Required
**Priority**: High (affects template inheritance - core functionality)

## Summary

The `AsyncJinja2Templates` class uses Jinja2's standard `template.render_async()` API in two critical methods, which is **incompatible with template inheritance** when using jinja2-async-environment.

## Current Implementation - Affected Methods

### 1. General Renderer (Lines 226-231)

**File**: `starlette_async_jinja/responses.py`

```python
async def renderer(self, template_name: str, **data: t.Any) -> str:
    try:
        template = await self.get_template_async(template_name)
        return await template.render_async(**data)  # ❌ LINE 229 - BROKEN
    except Exception as e:
        raise RuntimeError(f"Error rendering template '{template_name}': {e}")
```

**Used by**: `render_block()` method (line 214), which is registered as a global template function (`env.globals["render_block"]` on line 111).

**Impact**: Any template using the `render_block()` global function will fail with inheritance.

### 2. TemplateResponse Method (Lines 381-405)

**File**: `starlette_async_jinja/responses.py`

```python
async def TemplateResponse(self, *args: t.Any, **kwargs: t.Any) -> _TemplateResponse:
    name = "<unknown>"
    try:
        request, name, context, status_code, headers, media_type, background = (
            self._parse_template_args(*args, **kwargs)
        )

        context = self._prepare_template_context(context, request)

        template = await self.get_template_async(name)
        content = await template.render_async(context)  # ❌ LINE 393 - BROKEN

        return _TemplateResponse(
            template,
            context,
            content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )
    except Exception as e:
        raise RuntimeError(f"Error creating template response for '{name}': {e}")
```

**Used by**: Primary public API for Starlette template responses (line 407 aliases this as `render_template`).

**Impact**: **This is the main API** - ALL templates with inheritance will fail.

## The Good News: Correct Pattern Already Exists! ✅

The library **already implements the correct pattern** in `render_fragment()` (lines 268-286):

```python
async def _render_block_content(
    self,
    block_render_func: t.Callable[..., t.Any],
    template_ctx: t.Any,
    estimated_size: int,
) -> str:
    if self._should_use_stringio(estimated_size):
        output = io.StringIO()
        try:
            chunk_generator = block_render_func(template_ctx)
            async for chunk in chunk_generator:  # ✅ CORRECT PATTERN
                output.write(str(chunk))
            return output.getvalue()
        finally:
            output.close()
    else:
        chunk_generator = block_render_func(template_ctx)
        chunks = [chunk async for chunk in chunk_generator]  # ✅ CORRECT PATTERN
        return t.cast(str, self.env.concat(chunks))
```

This pattern:

- Gets the template's block function as an async generator
- Iterates with `async for` to collect chunks
- Properly handles jinja2-async-environment's architecture

**We just need to apply this same pattern to the two broken methods!**

## Root Cause

Same issue as ACB and FastBlocks:

jinja2-async-environment generates templates as **async generators** that must be iterated with `async for`. Jinja2's standard `render_async()` method doesn't properly handle jinja2-async-environment's async generator pattern for **template inheritance**.

**Impact**:

- ✅ **Simple templates work fine** (no inheritance)
- ❌ **Templates with inheritance fail** with `TypeError: 'async for' requires an object with __aiter__ method, got coroutine`
- ❌ **All Starlette responses using inherited templates fail**

## Recommended Fixes

### Fix #1: Update `renderer()` Method ✅ REQUIRED

**Lines 226-231** - Change to use root_render_func pattern:

**Before**:

```python
async def renderer(self, template_name: str, **data: t.Any) -> str:
    try:
        template = await self.get_template_async(template_name)
        return await template.render_async(**data)  # ❌ BROKEN
    except Exception as e:
        raise RuntimeError(f"Error rendering template '{template_name}': {e}")
```

**After** (using existing \_render_block_content pattern):

```python
async def renderer(self, template_name: str, **data: t.Any) -> str:
    """Render template using jinja2-async-environment compatible pattern.

    Uses root_render_func() directly for template inheritance support.
    """
    try:
        template = await self.get_template_async(template_name)

        # Use root_render_func directly for jinja2-async-environment compatibility
        ctx = template.new_context(data)
        chunk_generator = template.root_render_func(ctx)

        # Use same pattern as _render_block_content
        chunks = [chunk async for chunk in chunk_generator]
        return t.cast(str, self.env.concat(chunks))

    except Exception as e:
        raise RuntimeError(f"Error rendering template '{template_name}': {e}")
```

### Fix #2: Update `TemplateResponse()` Method ✅ REQUIRED

**Lines 381-405** - Change to use root_render_func pattern:

**Before**:

```python
async def TemplateResponse(self, *args: t.Any, **kwargs: t.Any) -> _TemplateResponse:
    name = "<unknown>"
    try:
        request, name, context, status_code, headers, media_type, background = (
            self._parse_template_args(*args, **kwargs)
        )

        context = self._prepare_template_context(context, request)

        template = await self.get_template_async(name)
        content = await template.render_async(context)  # ❌ BROKEN

        return _TemplateResponse(
            template,
            context,
            content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )
    except Exception as e:
        raise RuntimeError(f"Error creating template response for '{name}': {e}")
```

**After**:

```python
async def TemplateResponse(self, *args: t.Any, **kwargs: t.Any) -> _TemplateResponse:
    """Create Starlette TemplateResponse with jinja2-async-environment support.

    Uses root_render_func() for template inheritance compatibility.
    """
    name = "<unknown>"
    try:
        request, name, context, status_code, headers, media_type, background = (
            self._parse_template_args(*args, **kwargs)
        )

        context = self._prepare_template_context(context, request)

        template = await self.get_template_async(name)

        # Use root_render_func directly for jinja2-async-environment compatibility
        template_ctx = template.new_context(context)
        chunk_generator = template.root_render_func(template_ctx)
        chunks = [chunk async for chunk in chunk_generator]
        content = t.cast(str, self.env.concat(chunks))

        return _TemplateResponse(
            template,
            context,
            content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )
    except Exception as e:
        raise RuntimeError(f"Error creating template response for '{name}': {e}")
```

## Alternative: Create Helper Method (Optional Refactoring)

Since both methods need the same pattern, consider extracting it:

```python
async def _render_template_content(
    self, template: Template, context: dict[str, t.Any]
) -> str:
    """Internal helper to render template with jinja2-async-environment support.

    Uses root_render_func() directly for template inheritance compatibility.
    """
    template_ctx = template.new_context(context)
    chunk_generator = template.root_render_func(template_ctx)
    chunks = [chunk async for chunk in chunk_generator]
    return t.cast(str, self.env.concat(chunks))
```

Then both methods become:

```python
async def renderer(self, template_name: str, **data: t.Any) -> str:
    try:
        template = await self.get_template_async(template_name)
        return await self._render_template_content(template, data)
    except Exception as e:
        raise RuntimeError(f"Error rendering template '{template_name}': {e}")


async def TemplateResponse(self, *args: t.Any, **kwargs: t.Any) -> _TemplateResponse:
    name = "<unknown>"
    try:
        request, name, context, status_code, headers, media_type, background = (
            self._parse_template_args(*args, **kwargs)
        )
        context = self._prepare_template_context(context, request)
        template = await self.get_template_async(name)
        content = await self._render_template_content(template, context)

        return _TemplateResponse(
            template,
            context,
            content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )
    except Exception as e:
        raise RuntimeError(f"Error creating template response for '{name}': {e}")
```

## Testing Requirements

### 1. Template Inheritance Tests

Create comprehensive inheritance test suite:

```python
import pytest
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
from starlette_async_jinja import AsyncJinja2Templates
from anyio import Path as AsyncPath

# templates/base.html
"""
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Default Title{% endblock %}</title>
</head>
<body>
    <header>{% block header %}Default Header{% endblock %}</header>
    <main>{% block content %}{% endblock %}</main>
    <footer>{% block footer %}Default Footer{% endblock %}</footer>
</body>
</html>
"""

# templates/child.html
"""
{% extends "base.html" %}

{% block title %}{{ page_title }}{% endblock %}

{% block content %}
<h1>{{ heading }}</h1>
<p>{{ message }}</p>
{% endblock %}
"""


@pytest.mark.asyncio
async def test_template_response_with_inheritance(tmp_path):
    # Setup templates
    template_dir = AsyncPath(tmp_path / "templates")
    await template_dir.mkdir()

    base = template_dir / "base.html"
    await base.write_text(BASE_TEMPLATE)

    child = template_dir / "child.html"
    await child.write_text(CHILD_TEMPLATE)

    # Create templates instance
    templates = AsyncJinja2Templates(directory=template_dir)

    # Test TemplateResponse
    from unittest.mock import Mock

    request = Mock()
    request.url = Mock()
    request.url.path = "/test"
    request.method = "GET"

    response = await templates.TemplateResponse(
        request=request,
        name="child.html",
        context={
            "page_title": "Test Page",
            "heading": "Welcome",
            "message": "Inheritance works!",
        },
    )

    content = response.body.decode()

    # Verify inheritance worked
    assert "<title>Test Page</title>" in content
    assert "<h1>Welcome</h1>" in content
    assert "<p>Inheritance works!</p>" in content
    assert "Default Header" in content  # Parent block
    assert "Default Footer" in content  # Parent block


@pytest.mark.asyncio
async def test_renderer_with_inheritance(tmp_path):
    # Setup same templates
    template_dir = AsyncPath(tmp_path / "templates")
    await template_dir.mkdir()
    # ... (same template setup)

    templates = AsyncJinja2Templates(directory=template_dir)

    # Test renderer() method
    result = await templates.renderer(
        "child.html",
        page_title="Test Page",
        heading="Welcome",
        message="Renderer works!",
    )

    assert "<title>Test Page</title>" in result
    assert "<h1>Welcome</h1>" in result


@pytest.mark.asyncio
async def test_nested_inheritance(tmp_path):
    """Test 3-level inheritance: grandparent -> parent -> child"""
    # ... test nested inheritance
    pass


@pytest.mark.asyncio
async def test_multiple_blocks(tmp_path):
    """Test template with multiple overridden blocks"""
    # ... test multiple blocks
    pass


@pytest.mark.asyncio
async def test_super_calls(tmp_path):
    """Test {{ super() }} calls to parent blocks"""
    # ... test super() functionality
    pass
```

### 2. Regression Tests

Ensure existing functionality still works:

```python
@pytest.mark.asyncio
async def test_simple_template_still_works(tmp_path):
    """Verify simple templates without inheritance still work"""
    template_dir = AsyncPath(tmp_path / "templates")
    await template_dir.mkdir()

    simple = template_dir / "simple.html"
    await simple.write_text("<h1>{{ title }}</h1>")

    templates = AsyncJinja2Templates(directory=template_dir)
    result = await templates.renderer("simple.html", title="Hello")

    assert result == "<h1>Hello</h1>"


@pytest.mark.asyncio
async def test_render_fragment_still_works(tmp_path):
    """Verify fragment rendering (which already uses correct pattern) still works"""
    # ... test fragment rendering
    pass
```

## Performance Impact

**None expected**. The `root_render_func()` pattern:

- Is actually **more direct** than `render_async()`
- Eliminates compatibility layer overhead
- Matches how `render_fragment()` already works (proven performance)
- Uses the same chunk collection pattern as existing code

## Breaking Changes

**None**. This is a **purely internal change**:

- Public API remains identical (`TemplateResponse()` and `renderer()` signatures unchanged)
- Behavior remains identical for simple templates
- **Fixes broken behavior** for inherited templates (was failing before)
- No changes to Starlette integration or response objects

## Implementation Priority

**High Priority** - This affects the core functionality of the library:

- `TemplateResponse()` is the **primary public API** (line 407 aliases it as `render_template`)
- Template inheritance is a **fundamental Jinja2 feature**
- Current implementation **silently breaks** when users try to use inheritance
- The fix is **simple and low-risk** (proven pattern already exists in codebase)

## Related Issues

This issue was discovered while fixing:

1. ACB templates adapter (same issue, same fix applied)
1. FastBlocks templates adapter (same issue, documentation created)
1. jinja2-async-environment itself (codegen bug fixed)

**Related Documentation**:

- jinja2-async-environment bug analysis: `/Users/les/Projects/jinja2-async-environment/docs/TEMPLATE_INHERITANCE_BUG_ANALYSIS.md`
- ACB templates adapter: `/Users/les/Projects/acb/acb/adapters/templates/jinja2.py` (fixed implementation)
- FastBlocks documentation: `/Users/les/Projects/fastblocks/docs/JINJA2_ASYNC_ENVIRONMENT_USAGE.md`

## Conclusion

**Recommendation**: **Immediately implement both fixes** (renderer + TemplateResponse methods)

**Time Estimate**: 20-30 minutes for implementation + testing
**Risk**: Very Low (pattern already proven in `render_fragment()`)
**Impact**: Critical (enables core Jinja2 feature that's currently broken)

**The fix is simple, proven, and necessary for proper jinja2-async-environment support.**

## Proposed Implementation PR Checklist

- [ ] Update `renderer()` method (lines 226-231)
- [ ] Update `TemplateResponse()` method (lines 381-405)
- [ ] Optional: Extract `_render_template_content()` helper for DRY
- [ ] Add template inheritance tests
- [ ] Add regression tests for simple templates
- [ ] Update documentation/docstrings
- [ ] Test with real Starlette application
- [ ] Verify no breaking changes to public API
