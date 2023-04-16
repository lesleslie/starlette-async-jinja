import typing as t
import os

from jinja2.environment import Template
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from starlette.templating import pass_context
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send
from environment import AsyncEnvironment


class _TemplateResponse(HTMLResponse):
    def __init__(
        self,
        template: t.Any,
        context: dict,
        content: str,
        status_code: int = 200,
        headers: t.Optional[t.Mapping[str, str]] = None,
        media_type: t.Optional[str] = None,
        background: t.Optional[BackgroundTask] = None,
    ):
        self.template = template
        self.context = context
        super().__init__(content, status_code, headers, media_type, background)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = self.context.get("request", {})
        extensions = request.get("extensions", {})
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
        directory: t.Union[str, os.PathLike],
        context_processors: t.Optional[
            t.List[t.Callable[[Request], t.Dict[str, t.Any]]]
        ] = None,
        **env_options: t.Any,
    ):
        super().__init__(directory, **env_options)
        self.env_options = env_options
        self.context_processors = context_processors or []
        self.env = self._create_env(directory, **env_options)

    def _create_env(
        self, directory: t.Union[str, os.PathLike], **env_options: t.Any
    ) -> "AsyncEnvironment":
        @pass_context
        def url_for(context: dict, name: str, **path_params: t.Any) -> str:
            request = context["request"]
            return request.url_for(name, **path_params)

        env_options.setdefault("autoescape", True)
        env = AsyncEnvironment(**env_options)
        env.globals["url_for"] = url_for
        return env

    async def get_template(self, name: str) -> "Template":
        return await self.env.get_template(name)

    async def TemplateResponse(
        self,
        name: str,
        context: dict,
        status_code: int = 200,
        headers: t.Optional[t.Mapping[str, str]] = None,
        media_type: t.Optional[str] = None,
        background: t.Optional[BackgroundTask] = None,
    ) -> _TemplateResponse:
        if "request" not in context:
            raise ValueError('context must include a "request" key')
        request = t.cast(Request, context["request"])
        for context_processor in self.context_processors:
            context.update(context_processor(request))
        template = await self.get_template(name)
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
