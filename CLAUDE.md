# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `starlette-async-jinja`, an asynchronous Jinja2 template integration for Starlette and FastAPI. The package provides fully async template rendering with performance optimizations including context processor caching, fragment block caching, memory pooling, and fast JSON responses.

## Core Architecture

- **Main Package**: `starlette_async_jinja/` - Contains the core implementation
  - `responses.py` - Main implementation with `AsyncJinja2Templates`, `JsonResponse`, and `BlockNotFoundError`
  - `__init__.py` - Public API exports
- **Key Dependencies**: Uses `jinja2-async-environment` for async template loading, `anyio` for async filesystem operations, `msgspec` for fast JSON serialization
- **Template System**: Built around `AsyncJinja2Templates` class which wraps `AsyncEnvironment` from `jinja2-async-environment`

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m benchmark     # Benchmark tests only

# Run single test file
pytest tests/test_responses.py

# Run with coverage
pytest --cov=starlette_async_jinja --cov-report=term
```

### Code Quality
```bash
# Format and lint code
ruff check
ruff format

# Type checking
pyright

# Security scanning
bandit -c pyproject.toml

# Check for unused code
vulture

# Check for unnecessary dependencies
creosote
```

### Pre-commit Hooks
Pre-commit hooks are configured and include:
- File structure validation (trailing whitespace, YAML/TOML validation)
- Package management (UV lock file management)
- Security checks (detect-secrets, bandit)
- Code quality (ruff, vulture, creosote, refurb)
- Type checking (pyright, autotyping)

## Key Implementation Details

### Template Rendering Pipeline
1. `AsyncJinja2Templates` creates an `AsyncEnvironment` with `AsyncFileSystemLoader`
2. Templates are loaded asynchronously via `get_template_async()`
3. Context processors are applied to add global context
4. Templates rendered via `render_async()` method

### Special Features
- **render_block**: Renders entire template files as reusable components
- **render_fragment**: Renders specific blocks from templates with caching optimizations
- **Context processors**: Functions that add global context to all templates with smart caching
- **JsonResponse**: Uses `msgspec` for faster JSON serialization than standard responses
- **Macro support**: Full Jinja2 macro support with `jinja2-async-environment>=0.13`

### Performance Optimizations
- **Context processor caching**: Caches processor results by request path/method to avoid recomputation
- **Fragment block caching**: Caches compiled block functions to avoid re-extraction from templates
- **Context object pooling**: Reuses context dictionaries to reduce memory allocations
- **Adaptive string building**: Uses StringIO vs concat based on estimated fragment size
- **LRU cache management**: Automatic cache size limits with oldest-first eviction

### Test Structure
- Tests use mocked filesystem and templates for isolation
- `conftest.py` provides fixtures for `AsyncJinja2Templates`, Starlette app, and test client
- Test categories: unit, integration, benchmark (marked with pytest markers)
- Coverage target: 42% minimum

## Architecture Patterns

### Async-First Design
All template operations are async - loading, rendering, and fragment extraction use `await`. The package depends on `anyio.Path` for async filesystem operations.

### Error Handling
Custom exceptions like `BlockNotFoundError` provide specific error information. All methods wrap lower-level exceptions in `RuntimeError` with descriptive messages.

### Extensibility
- Context processors allow global template context injection with configurable caching
- Template loaders can be customized (AsyncFileSystemLoader, AsyncPackageLoader, etc.)
- Environment options can be passed through to underlying Jinja2 environment
- Performance tuning via cache sizes, TTL settings, and memory pool configuration

## Performance Configuration

### Constructor Parameters
```python
AsyncJinja2Templates(
    directory=AsyncPath("templates"),
    context_cache_size=128,           # Context processor cache entries
    context_cache_ttl=300.0,          # Context cache TTL (seconds)
    fragment_cache_size=64,           # Fragment block cache entries
    fragment_cache_ttl=600.0,         # Fragment cache TTL (seconds)
    context_pool_size=10,             # Context object pool size
    fragment_stringio_threshold=1024, # StringIO threshold (bytes)
)
```

### Performance Tuning
- **Increase cache sizes** for applications with many unique templates/contexts
- **Decrease TTL values** for applications with frequently changing context data
- **Adjust pool size** based on concurrent template rendering load
- **Tune StringIO threshold** based on typical fragment output sizes

## Task Completion Requirements

**MANDATORY: Before marking any task as complete, AI assistants MUST:**

1. **Run crackerjack verification**: Execute `python -m crackerjack -t --ai-agent` to run all quality checks and tests with AI-optimized output
2. **Fix any issues found**: Address all formatting, linting, type checking, and test failures
3. **Re-run verification**: Ensure crackerjack passes completely (all hooks pass, all tests pass)
4. **Document verification**: Mention that crackerjack verification was completed successfully

**Why this is critical:**
- Ensures all code meets project quality standards
- Prevents broken code from being committed
- Maintains consistency with project development workflow
- Catches issues early before they become problems

**Never skip crackerjack verification** - it's the project's standard quality gate.