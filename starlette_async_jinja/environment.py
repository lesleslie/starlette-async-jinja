from weakref import ref
import typing as t

from jinja2.environment import Template
from jinja2.utils import internalcode
from jinja2 import Environment
from loaders import AsyncBaseLoader
from compiler import AsyncCodeGenerator
from bccache import AsyncRedisBytecodeCache


class AsyncEnvironment(Environment):
    code_generator_class = AsyncCodeGenerator
    loader: AsyncBaseLoader = None
    bytecode_cache: AsyncRedisBytecodeCache = None

    def __init__(self, **env_options):
        super().__init__(**env_options)

    @internalcode
    async def get_template(
        self,
        name: t.Union[str, "Template"],
        parent: t.Optional[str] = None,
        jinja_globals: t.Optional[t.MutableMapping[str, t.Any]] = None,
    ) -> "Template":
        if isinstance(name, Template):
            return name
        if parent is not None:
            name = self.join_path(name, parent)
        return await self._load_template(name, jinja_globals)

    @internalcode
    async def _load_template(
        self, name: str, jinja_globals: t.Optional[t.MutableMapping[str, t.Any]]
    ) -> "Template":
        if self.loader is None:
            raise TypeError("no loader for this environment specified")
        cache_key = (ref(self.loader), name)
        if self.cache is not None:
            template = self.cache.get(cache_key)
            if template is not None and (
                not self.auto_reload or await template.is_up_to_date
            ):
                if jinja_globals:
                    template.globals.update(jinja_globals)
                return template
        template = await self.loader.load(self, name, self.make_globals(jinja_globals))
        if self.cache is not None:
            self.cache[cache_key] = template
        return template
