import io
import time
import typing as t
from functools import partial

from anyio import Path as AsyncPath
from jinja2.environment import Template
from jinja2_async_environment import AsyncEnvironment, AsyncFileSystemLoader
from markupsafe import Markup
from msgspec import json
from starlette.background import BackgroundTask
from starlette.datastructures import URL
from starlette.responses import HTMLResponse, JSONResponse
from starlette.templating import pass_context
from starlette.types import Receive, Scope, Send

ContextProcessor: t.TypeAlias = t.Callable[[t.Any], dict[str, t.Any]]
RenderFunction: t.TypeAlias = t.Callable[..., t.Awaitable[t.Any]]


class JsonResponse(JSONResponse):
    def render(self, content: t.Any) -> bytes:  # type: ignore
        return json.encode(content)


class BlockNotFoundError(Exception):
    def __init__(
        self, block_name: str, template_name: str, message: str | None = None
    ) -> None:
        self.block_name = block_name
        self.template_name = template_name
        super().__init__(
            message
            or f"Block {self.block_name!r} not found in template {self.template_name!r}"
        )


class _TemplateResponse(HTMLResponse):
    @t.override
    def __init__(
        self,
        template: Template,
        context: dict[str, t.Any],
        content: str,
        status_code: int = 200,
        headers: t.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        self.template = template
        self.context = context
        super().__init__(content, status_code, headers, media_type, background)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        extensions = self.context.get("request", {}).get("extensions", {})
        if "http.response.debug" in extensions:
            await send(
                {
                    "type": "http.response.debug",
                    "info": {
                        "template": self.template,
                        "context": self.context,
                    },
                }
            )
        await super().__call__(scope, receive, send)


class AsyncJinja2Templates:
    @t.override
    def __init__(
        self,
        directory: AsyncPath,
        context_processors: list[ContextProcessor] | None = None,
        context_cache_size: int = 128,
        context_cache_ttl: float = 300.0,
        fragment_cache_size: int = 64,
        fragment_cache_ttl: float = 600.0,
        context_pool_size: int = 10,
        fragment_stringio_threshold: int = 1024,
        **env_options: t.Any,
    ) -> None:
        self.env_options = env_options
        self.context_processors = context_processors or []
        self.context_cache_size = context_cache_size
        self.context_cache_ttl = context_cache_ttl
        self._context_cache: dict[str, tuple[float, dict[str, t.Any]]] = {}

        self.fragment_cache_size = fragment_cache_size
        self.fragment_cache_ttl = fragment_cache_ttl
        self.context_pool_size = context_pool_size
        self.fragment_stringio_threshold = fragment_stringio_threshold
        self._block_cache: dict[str, tuple[float, t.Callable[..., t.Any]]] = {}
        self._template_blocks: dict[str, set[str]] = {}
        self._context_pool: list[dict[str, t.Any]] = []

        self.env = self._create_env(directory, **env_options)

    def _create_env(
        self, directory: AsyncPath, **env_options: t.Any
    ) -> AsyncEnvironment:
        @pass_context  # type: ignore[misc]
        def url_for(context: dict[str, t.Any], name: str, **path_params: t.Any) -> URL:
            return context["request"].url_for(name, **path_params)

        loader = AsyncFileSystemLoader(directory)
        env_options.setdefault("loader", loader)
        env_options.setdefault("autoescape", True)

        env = AsyncEnvironment(**env_options)
        env.globals["render_block"] = self.generate_render_partial(self.renderer)  # type: ignore[assignment]
        env.globals["url_for"] = url_for  # type: ignore[assignment]
        return env

    def _get_context_cache_key(self, request: t.Any) -> str:
        if hasattr(request, "url") and hasattr(request.url, "path"):
            path = request.url.path
        else:
            path = str(request)
        method = getattr(request, "method", "GET")
        return f"{method}:{path}"

    def _is_context_cacheable(self, context: dict[str, t.Any]) -> bool:
        for value in context.values():
            if hasattr(value, "method") and hasattr(value, "url"):
                return False
        return True

    def _get_processed_context(self, request: t.Any) -> dict[str, t.Any]:
        if not self.context_processors:
            return {}
        cache_key = self._get_context_cache_key(request)
        current_time = time.time()
        if cache_key in self._context_cache:
            cached_time, cached_context = self._context_cache[cache_key]
            if current_time - cached_time < self.context_cache_ttl:
                return cached_context.copy()
        context = {}
        for context_processor in self.context_processors:
            processor_result = context_processor(request)
            if processor_result:
                context.update(processor_result)
        if self._is_context_cacheable(context):
            if len(self._context_cache) >= self.context_cache_size:
                oldest_key = min(
                    self._context_cache.keys(), key=lambda k: self._context_cache[k][0]
                )
                del self._context_cache[oldest_key]
            self._context_cache[cache_key] = (current_time, context.copy())

        return context

    def _get_pooled_context(self, data: dict[str, t.Any]) -> dict[str, t.Any]:
        if self._context_pool:
            ctx = self._context_pool.pop()
            ctx.clear()
            ctx.update(data)
            return ctx
        return data.copy()

    def _return_to_pool(self, ctx: dict[str, t.Any]) -> None:
        if len(self._context_pool) < self.context_pool_size:
            ctx.clear()
            self._context_pool.append(ctx)

    async def _get_cached_block_func(
        self, template_name: str, block_name: str
    ) -> t.Callable[..., t.Any]:
        cache_key = f"{template_name}:{block_name}"
        current_time = time.time()

        if cache_key in self._block_cache:
            cached_time, block_func = self._block_cache[cache_key]
            if current_time - cached_time < self.fragment_cache_ttl:
                return block_func

        template = await self.get_template_async(template_name)
        if block_name not in template.blocks:
            raise BlockNotFoundError(block_name, template_name)

        block_func = template.blocks[block_name]

        if len(self._block_cache) >= self.fragment_cache_size:
            oldest_key = min(
                self._block_cache.keys(), key=lambda k: self._block_cache[k][0]
            )
            del self._block_cache[oldest_key]

        self._block_cache[cache_key] = (current_time, block_func)
        return block_func

    def _preload_template_blocks(self, template: Template, template_name: str) -> None:
        if template_name not in self._template_blocks:
            self._template_blocks[template_name] = set(template.blocks.keys())

    def _validate_block_exists(self, template_name: str, block_name: str) -> bool:
        if template_name in self._template_blocks:
            return block_name in self._template_blocks[template_name]
        return True

    def _should_use_stringio(self, estimated_size: int = 0) -> bool:
        return estimated_size > self.fragment_stringio_threshold

    async def render_block(
        self,
        template_name: str,
        renderer: RenderFunction | None = None,
        markup: bool = True,
        **data: t.Any,
    ) -> Markup | str:
        renderer = renderer or self.renderer
        try:
            if markup:
                return Markup(await renderer(template_name, **data))
            return await renderer(template_name, **data)
        except Exception as e:
            raise RuntimeError(
                f"Error rendering block in template '{template_name}': {e}"
            )

    def generate_render_partial(
        self, renderer: RenderFunction
    ) -> t.Callable[..., t.Awaitable[Markup | str]]:
        return partial(self.render_block, renderer=renderer)

    async def renderer(self, template_name: str, **data: t.Any) -> str:
        try:
            template = await self.get_template_async(template_name)
            return await template.render_async(**data)
        except Exception as e:
            raise RuntimeError(f"Error rendering template '{template_name}': {e}")

    async def _get_block_function_and_template(
        self, template_name: str, block_name: str
    ) -> tuple[t.Callable[..., t.Any], Template]:
        cache_key = f"{template_name}:{block_name}"
        current_time = time.time()
        block_render_func = None
        template = None

        if cache_key in self._block_cache:
            cached_time, cached_func = self._block_cache[cache_key]
            if current_time - cached_time < self.fragment_cache_ttl:
                block_render_func = cached_func

        if block_render_func is None:
            template = await self.get_template_async(template_name)
            self._preload_template_blocks(template, template_name)

            if block_name not in template.blocks:
                raise BlockNotFoundError(block_name, template_name)

            block_render_func = template.blocks[block_name]

            if len(self._block_cache) >= self.fragment_cache_size:
                oldest_key = min(
                    self._block_cache.keys(),
                    key=lambda k: self._block_cache[k][0],
                )
                del self._block_cache[oldest_key]
            self._block_cache[cache_key] = (current_time, block_render_func)

        if template is None:
            template = await self.get_template_async(template_name)

        return block_render_func, template

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
                async for chunk in chunk_generator:  # type: ignore[misc]
                    output.write(str(chunk))
                return output.getvalue()
            finally:
                output.close()
        else:
            chunk_generator = block_render_func(template_ctx)
            chunks = [chunk async for chunk in chunk_generator]  # type: ignore[misc]
            return self.env.concat(chunks)

    async def render_fragment(
        self,
        template_name: str,
        block_name: str,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> str:
        if not self._validate_block_exists(template_name, block_name):
            raise BlockNotFoundError(block_name, template_name)

        try:
            ctx_data = dict(*args, **kwargs)
            ctx = self._get_pooled_context(ctx_data)

            try:
                (
                    block_render_func,
                    template,
                ) = await self._get_block_function_and_template(
                    template_name, block_name
                )

                template_ctx = template.new_context(ctx)

                estimated_size = len(str(ctx_data))
                return await self._render_block_content(
                    block_render_func, template_ctx, estimated_size
                )

            except Exception:
                return self.env.handle_exception()
            finally:
                self._return_to_pool(ctx)

        except BlockNotFoundError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Error rendering fragment '{block_name}' in template '{template_name}': {e}"
            )

    async def get_template_async(self, name: str) -> Template:
        try:
            template = await self.env.get_template_async(name)
            return template
        except Exception:
            raise RuntimeError(f"Error loading template '{name}'")

    def _parse_template_args(
        self, *args: t.Any, **kwargs: t.Any
    ) -> tuple[t.Any, str, dict[str, t.Any], int, t.Any, t.Any, t.Any]:
        if args:
            return self._parse_positional_args(args, kwargs)
        return self._parse_keyword_args(kwargs)

    def _parse_positional_args(
        self, args: tuple[t.Any, ...], kwargs: dict[str, t.Any]
    ) -> tuple[t.Any, str, dict[str, t.Any], int, t.Any, t.Any, t.Any]:
        request = args[0]
        name = args[1] if len(args) > 1 else kwargs["name"]
        context = args[2] if len(args) > 2 else kwargs.get("context", {})
        status_code = args[3] if len(args) > 3 else kwargs.get("status_code", 200)
        headers = args[4] if len(args) > 4 else kwargs.get("headers")
        media_type = args[5] if len(args) > 5 else kwargs.get("media_type")
        background = args[6] if len(args) > 6 else kwargs.get("background")
        return request, name, context, status_code, headers, media_type, background

    def _parse_keyword_args(
        self, kwargs: dict[str, t.Any]
    ) -> tuple[t.Any, str, dict[str, t.Any], int, t.Any, t.Any, t.Any]:
        context = kwargs.get("context", {})
        request = kwargs.get("request", context.get("request"))
        name = t.cast(str, kwargs["name"])
        status_code = kwargs.get("status_code", 200)
        headers = kwargs.get("headers")
        media_type = kwargs.get("media_type")
        background = kwargs.get("background")
        return request, name, context, status_code, headers, media_type, background

    def _prepare_template_context(
        self, context: dict[str, t.Any] | None, request: t.Any
    ) -> dict[str, t.Any]:
        if context is None:
            context = {}

        context.setdefault("request", request)

        processed_context = self._get_processed_context(request)
        if processed_context:
            context.update(processed_context)

        return context

    async def TemplateResponse(
        self, *args: t.Any, **kwargs: t.Any
    ) -> _TemplateResponse:
        name = "<unknown>"
        try:
            request, name, context, status_code, headers, media_type, background = (
                self._parse_template_args(*args, **kwargs)
            )

            context = self._prepare_template_context(context, request)

            template = await self.get_template_async(name)
            content = await template.render_async(context)

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

    render_template = TemplateResponse
