import typing as t

from aiopath import AsyncPath
from environment import AsyncEnvironment
from jinja2.exceptions import TemplateNotFound
from jinja2.utils import internalcode
from jinja2.environment import Template


class AsyncBaseLoader:
    has_source_access = True
    loaders: list = None

    def __init__(self, path: AsyncPath):
        self.path = path

    async def get_source(
        self, environment: "AsyncEnvironment", template: str
    ) -> [t.Tuple[str, t.Optional[str], t.Optional[t.Callable[[], bool]]], str]:
        if not self.has_source_access:
            raise RuntimeError(
                f"{type(self).__name__} cannot provide access to the source"
            )
        raise TemplateNotFound(template)

    async def list_templates(self) -> t.List[str]:
        raise TypeError("this loader cannot iterate over all templates")

    @internalcode
    async def load(
        self,
        environment: "AsyncEnvironment",
        name: str,
        globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ) -> "Template":
        code = None
        if globals is None:
            globals = {}
        source, filename, uptodate = await self.get_source(environment, name)
        bcc = environment.bytecode_cache
        bucket = None
        if bcc is not None:
            bucket = await bcc.get_bucket(environment, name, filename, source)
            code = bucket.code
        if code is None:
            code = environment.compile(source, name, filename)
        if bcc is not None and bucket.code is None:
            bucket.code = code
            await bcc.set_bucket(bucket)
        return environment.template_class.from_code(
            environment, code, globals, uptodate
        )
