from asyncio import Semaphore
from concurrent.futures.thread import ThreadPoolExecutor

from aiohttp import web
from atoolbox import create_default_app
from atoolbox.middleware import error_middleware

from settings import Settings
from views import build_index, get_map, index, robots


async def pool_shutdown(app):
    app['thread_pool'].shutdown()


async def create_app(settings=None):
    settings = settings or Settings()
    routes = [
        web.get('/map.jpg', get_map, name='get-map'),
        web.get('/', index, name='index'),
        web.get('/robots.txt', robots, name='robots'),
    ]
    middleware = (error_middleware,)
    app = await create_default_app(settings=settings, routes=routes, middleware=middleware)
    app['index_path'] = build_index()
    app.update(
        index_page=build_index(),
        osm_semaphore=Semaphore(value=32),
        thread_pool=ThreadPoolExecutor(),
    )
    app.on_cleanup.append(pool_shutdown)
    return app
