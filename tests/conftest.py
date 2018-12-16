import sys
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from aiohttp import web
from atoolbox.test_utils import DummyServer, create_dummy_server

ROOT_DIR = Path(__file__).parent / '..'
sys.path.append(str(ROOT_DIR))


async def osm_image(request):
    stream = BytesIO()
    image = Image.new('RGBA', (256, 256), (50, 100, 150))
    image.save(stream, format='png')
    return web.Response(body=stream.getvalue())


@pytest.fixture(name='dummy_server')
async def _fix_dummy_server(loop, aiohttp_server):
    urls = [
        web.get('/osm/{zoom:\d+}/{x:\d+}/{y:\d+}.png', osm_image)
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
