# starlette-async-jinja

[![Code style: crackerjack](https://img.shields.io/badge/code%20style-crackerjack-000042)](https://github.com/lesleslie/crackerjack)

### Jinja2 is_async template support for Starlette +

## About

- Provides AsyncJinja2Templates class which enables use of the is_async Jinja environment flag with
Startlette and Starlette based applications like FastAPI
- Integrated [Jinja Partials](https://github.com/mikeckennedy/jinja_partials)
  and [Jinja Fragments](https://github.com/sponsfreixes/jinja2-fragments)
- Supports asynchronous template loaders (examples [here](https://github.com/lesleslie/jinja2-async-environment/blob/main/jinja2_async_environment/loaders.py))

## Issues

- Only [asynchronous template loaders](https://github.com/lesleslie/jinja2-async-environment/blob/main/jinja2_async_environment/loaders.py)
  (not yet tested but should work) are currently supported

- The Jinja bytecodecache requires an asynchronous Redis backend

## Usage

Import AsyncJinja2Templates:
```python
from starlette_async_jinja import AsyncJinja2Templates
```

Replace Jinja2Templates with AsyncJinja2Templates:
```python
templates = AsyncJinja2Templates(directory='templates')
```

Render the async template in the response:
```python
async def homepage(request: Request):
    return await templates.TemplateResponse(request, 'index.html')
```

or:
```python
async def homepage(request: Request):
    return await templates.render_template(request, 'index.html')
```


## Acknowledgements


## License

BSD-3-Clause
