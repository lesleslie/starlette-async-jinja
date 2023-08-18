# starlette-async-jinja

[![Code style: crackerjack](https://img.shields.io/badge/code%20style-crackerjack-000042)](https://github.com/lesleslie/crackerjack)

### Jinja2 is_async template support for Starlette +

## About

- Provides AsyncJinja2Templates class which enables use of the is_async Jinja environment flag with
Startlette and Starlette based applications like FastAPI
- Integrated [Jinja Partials](https://github.com/mikeckennedy/jinja_partials)
  and [Jinja Fragments](https://github.com/sponsfreixes/jinja2-fragments)
- Supports asynchronous template loaders (examples [here](https://github.com/lesleslie/jinja2-async-environment/blob/main/jinja2_async_environment/loaders.py))
  (not yet tested but should work)

## Issues

- Only [asynchronous template loaders](https://github.com/lesleslie/jinja2-async-environment/blob/main/jinja2_async_environment/loaders.py)
  (not yet tested but should work) are currently supported

- The Jinja bytecodecache requires an asynchronous Redis backend


## Usage

Import AsyncJinja2 Templates:
```python
from starlette_async_jinja import AsyncJinja2Templates
```

Replace Jinja2Templates with AsyncJinja2Templates:
```python
templates = Jinja2Templates(directory='templates')
```

Render the async template in the response:
```python
async def homepage(request: Request):
    return await templates.AsyncTemplateResponse('index.html', {'request': request})
```

Even simpler:
```python
async def homepage(request: Request):
    return await templates.render_template('index.html', {'request': request})
```

To render [Jinja Fragments](https://github.com/sponsfreixes/jinja2-fragments) or 'blocks':
```python
async def only_block(request: Request):
    return await templates.render_block(
        "page.html.jinja2",
        {"request": request, "magic_number": 42},
        block_name="content"
    )
```

To render [Jinja Partials](https://github.com/mikeckennedy/jinja_partials):

in a template
```python
{% for v in row %}
  <div class="col-md-3 video">
      {{ render_partial('shared/partials/video_square.html', video=v) }}
  </div>
{% endfor %}
```
or programmatically
```python
async def render_partial(template: str, **kwargs):
  return await templates.render_partial(template, **kwargs)
```



## Acknowledgements


## License

BSD-3-Clause
