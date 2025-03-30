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
        **env_options: t.Any,
    ) -> None:
        self.env_options = env_options
        self.context_processors = context_processors or []
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

    async def render_fragment(
        self,
        template_name: str,
        block_name: str,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> str:
        try:
            template = await self.get_template_async(template_name)
            try:
                block_render_func = template.blocks[block_name]
            except KeyError:
                raise BlockNotFoundError(block_name, template_name)

            ctx = template.new_context(dict(*args, **kwargs))
            try:
                return self.env.concat(
                    [n async for n in block_render_func(ctx)]  # type: ignore[attr-defined]
                )
            except Exception:
                return self.env.handle_exception()
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

    async def TemplateResponse(
        self, *args: t.Any, **kwargs: t.Any
    ) -> _TemplateResponse:
        name = "<unknown>"
        try:
            if args:
                request = args[0]
                name = args[1] if len(args) > 1 else kwargs["name"]
                context = args[2] if len(args) > 2 else kwargs.get("context", {})
                status_code = (
                    args[3] if len(args) > 3 else kwargs.get("status_code", 200)
                )
                headers = args[4] if len(args) > 4 else kwargs.get("headers")
                media_type = args[5] if len(args) > 5 else kwargs.get("media_type")
                background = args[6] if len(args) > 6 else kwargs.get("background")
            else:
                context = kwargs.get("context", {})
                request = kwargs.get("request", context.get("request"))
                name = t.cast(str, kwargs["name"])
                status_code = kwargs.get("status_code", 200)
                headers = kwargs.get("headers")
                media_type = kwargs.get("media_type")
                background = kwargs.get("background")

            if context is None:
                context = {}

            context.setdefault("request", request)
            for context_processor in self.context_processors:
                processor_result = context_processor(request)
                if processor_result:
                    context.update(processor_result)

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
