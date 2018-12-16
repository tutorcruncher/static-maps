import os
import re
from pathlib import Path

from aiohttp import web
from atoolbox import create_default_app
from atoolbox.middleware import error_middleware

from .views import get_map, index, robots

ROOT_DIR = Path(__file__).parent


def build_index():
    ctx = {
        'COMMIT': os.getenv('COMMIT', '-'),
        'BUILD_TIME': os.getenv('BUILD_TIME', '-'),
    }
    index_html = (ROOT_DIR / 'index.html').read_text()
    for key, value in ctx.items():
        index_html = re.sub(r'\{\{ ?%s ?\}\}' % key, value, index_html, flags=re.I)
    p = ROOT_DIR / 'index.tmp.html'
    p.write_text(index_html)
    return p


async def create_app():
    routes = [
        web.get('/map.jpg', get_map, name='get-map'),
        web.get('/', index, name='index'),
        web.get('/robots.txt', robots, name='robots'),
    ]
    middleware = (error_middleware,)
    app = await create_default_app(routes=routes, middleware=middleware)
    app['index_path'] = build_index()
    return app
