import typing as t
from functools import partial

from aiopath import AsyncPath
from jinja2.environment import Template
from jinja2_async_environment import AsyncEnvironment
from jinja2_async_environment import FileSystemLoader
from markupsafe import Markup
from msgspec import json
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.responses import JSONResponse
from starlette.templating import Jinja2Templates
from starlette.templating import pass_context
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send


class JsonResponse(JSONResponse):
    async def render(self, content: str) -> bytes:
        return json.encode(content)


class BlockNotFoundError(Exception):
    def __init__(
        self, block_name: str, template_name: str, message: t.Optional[str] = None
    ) -> None:
        self.block_name = block_name
        self.template_name = template_name
        super().__init__(
            message
            or f"Block {self.block_name!r} not found in template {self.template_name!r}"
        )


class _AsyncTemplateResponse(HTMLResponse):
    def __init__(
        self,
        template: Template,
        context: dict[str, str],
        content: str,
        status_code: int = 200,
        headers: t.Optional[t.Mapping[str, str]] = None,
        media_type: t.Optional[str] = None,
        background: t.Optional[BackgroundTask] = None,
    ) -> None:
        self.template = template
        self.context = context
        super().__init__(content, status_code, headers, media_type, background)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request: dict = self.context.get("request", {})
        extensions: dict[str, str] = request.get("extensions", {})
        if "http.response.debug" in extensions:
            await send(
                {
                    "type": "http.response.debug",
                    "info": {"template": self.template, "context": self.context},
                }
            )
        await super().__call__(scope, receive, send)


class AsyncJinja2Templates(Jinja2Templates):
    def __init__(
        self,
        directory: AsyncPath,
        context_processors: t.Optional[
            t.List[t.Callable[[Request], t.Dict[str, t.Any]]]
        ] = None,
        **env_options: t.Any,
    ) -> None:
        super().__init__(directory, **env_options)
        self.env_options = env_options
        self.context_processors = context_processors or []
        self.env = self._create_env(directory, **env_options)

    def _create_env(
        self, directory: AsyncPath, **env_options: dict[str, str] | bool
    ) -> "AsyncEnvironment":
        @pass_context
        def url_for(
            context: dict[str, t.Any], name: str, **path_params: dict[str, str | bool]
        ) -> str:
            request = context["request"]
            return request.url_for(name, **path_params)

        loader = FileSystemLoader(directory)
        env_options.setdefault("loader", loader)  # type: ignore
        env_options.setdefault("autoescape", True)
        env = AsyncEnvironment(**env_options)
        env.globals["render_partial"] = self.generate_render_partial(self.renderer)
        env.globals["url_for"] = url_for
        return env

    # Partials - https://github.com/mikeckennedy/jinja_partials
    async def render_partial(
        self,
        template_name: str,
        renderer: t.Optional[t.Callable[..., t.Any]] = None,
        **data: t.Any,
    ) -> Markup:
        return Markup(await renderer(template_name, **data))

    def generate_render_partial(
        self, renderer: t.Callable[..., t.Any]
    ) -> t.Callable[..., Markup]:
        return partial(self.render_partial, renderer=renderer)

    async def renderer(self, template_name: str, **data: t.Any) -> str:
        return await (await self.get_template(template_name)).render_async(**data)

    # Fragments - https://github.com/sponsfreixes/jinja2-fragments
    async def render_block(
        self,
        template: "Template",
        block_name: str,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> str:
        try:
            block_render_func = template.blocks[block_name]
        except KeyError:
            raise BlockNotFoundError(block_name, template.name)

        ctx = template.new_context(dict(*args, **kwargs))
        try:
            return self.env.concat(  # type: ignore
                [n async for n in block_render_func(ctx)]  # type: ignore
            )
        except Exception:
            return self.env.handle_exception()

    async def get_template(self, name: str) -> "Template":
        return await self.env.get_template(name)

    async def AsyncTemplateResponse(
        self,
        name: str,
        context: dict[str, str],
        status_code: int = 200,
        headers: t.Optional[t.Mapping[str, str]] = None,
        media_type: t.Optional[str] = None,
        background: t.Optional[BackgroundTask] = None,
        *,
        block_name: t.Optional[str] = None,
    ) -> "_AsyncTemplateResponse" | str:
        if "request" not in context:
            raise ValueError('context must include a "request" key')
        request = t.cast(Request, context["request"])
        for context_processor in self.context_processors:
            context.update(context_processor(request))
        template = await self.get_template(name)

        if block_name:
            return await self.render_block(
                template,
                block_name,
                context,
            )

        content = await template.render_async(context)
        return _AsyncTemplateResponse(
            template,
            context,
            content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

    render_template = AsyncTemplateResponse
