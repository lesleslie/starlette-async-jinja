# Gemini Code Assistant Context

This document provides context for the Gemini Code Assistant to understand the `starlette-async-jinja` project.

## Project Overview

`starlette-async-jinja` is a Python library that provides an asynchronous Jinja2 template integration for Starlette and FastAPI. It is built on top of the `jinja2-async-environment` package and offers several features to improve performance and developer experience.

**Main Technologies:**

*   **Python 3.13+**
*   **Starlette:** The ASGI framework for building high-performance services.
*   **FastAPI:** A modern, fast (high-performance), web framework for building APIs with Python 3.13+ based on standard Python type hints.
*   **Jinja2:** A modern and designer-friendly templating engine for Python.
*   **jinja2-async-environment:** A package that provides an asynchronous environment for Jinja2.
*   **anyio:** An asynchronous networking and concurrency library.
*   **msgspec:** A fast and memory-efficient JSON and MessagePack library.

**Architecture:**

The core of the library is the `AsyncJinja2Templates` class, which provides an interface for rendering Jinja2 templates asynchronously. It integrates with Starlette and FastAPI's request/response cycle and provides features like:

*   **Asynchronous template rendering:** Load and render templates asynchronously.
*   **Template fragments:** Render specific blocks from templates.
*   **Template partials:** Include sub-templates with their own context.
*   **Fast JSON responses:** Enhanced JSON responses using `msgspec` for faster serialization.
*   **Context processors:** Add global context to all templates.
*   **Performance optimizations:** Context processor caching, fragment caching, and memory pooling.

## Building and Running

This is a library project, so there is no main application to run. However, there are scripts for building, testing, and linting the project.

**Key Commands:**

*   **Installation:**
    ```bash
    pip install -e .[dev]
    ```
*   **Running Tests:**
    ```bash
    pytest
    ```
*   **Linting and Formatting:**
    ```bash
    ruff check .
    ```
*   **Type Checking:**
    ```bash
    pyright
    ```

## Development Conventions

*   **Coding Style:** The project uses `ruff` for linting and formatting, with a line length of 88 characters.
*   **Testing:** The project uses `pytest` for testing. Tests are located in the `tests/` directory and are organized by functionality.
*   **Type Hinting:** The project is fully typed with Python's type annotations and is compatible with static type checkers like `mypy` and `pyright`.
*   **Commit Style:** The project follows the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.
*   **Dependency Management:** The project uses `uv` for dependency management.
