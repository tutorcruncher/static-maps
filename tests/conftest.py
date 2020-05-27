import sys
from io import BytesIO
from pathlib import Path

import pytest
from aiohttp import web
from atoolbox.test_utils import DummyServer, create_dummy_server
from PIL import Image

APP_DIR = Path(__file__).parent / '../app'
sys.path.append(str(APP_DIR))


async def osm_image(request):
    zoom = int(request.match_info['zoom'])
    if zoom == 6:
        return web.Response(text='bad', status=429)
    assert 'static-maps' in request.headers['User-Agent']
    stream = BytesIO()
    image = Image.new('RGBA', (256, 256), (50, 100, 150))
    image.save(stream, format='png')
    request.app['log'][-1] = (int(zoom), int(request.match_info['x']), int(request.match_info['y']),
                              request.headers.get('Referer'))
    return web.Response(body=stream.getvalue())


@pytest.fixture(name='dummy_server')
async def _fix_dummy_server(loop, aiohttp_server):
    urls = [
        web.get(r'/osm/{zoom:\d+}/{x:\d+}/{y:\d+}.png', osm_image)
    ]
    return await create_dummy_server(aiohttp_server, extra_routes=urls)


@pytest.fixture(name='settings')
def _fix_settings(dummy_server: DummyServer, request):
    from app.settings import Settings
    return Settings(osm_root=f'{dummy_server.server_name}/osm')


@pytest.fixture(name='cli')
async def _fix_cli(settings, aiohttp_client, loop):
    from app.main import create_app
    app = await create_app(settings=settings)
    return await aiohttp_client(app)


class LogSortKey:
    """
    Used to sort dummy_servers log to accept different types in the list when sorting
    """
    __slots__ = ("value", "typestr")

    def __init__(self, value):
        self.value = value
        self.typestr = sys.intern(type(value).__name__)

    def __lt__(self, other):
        try:
            return self.value < other.value
        except TypeError:
            return self.typestr < other.typestr
