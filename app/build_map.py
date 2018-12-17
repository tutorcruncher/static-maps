import asyncio
import io
import logging
import math
import random

from PIL import Image

logger = logging.getLogger('app.build')
SHARDS = 'a', 'b', 'c'
TILE_SIZE = 256

__all__ = 'BuildMap',


class BuildMap:
    __slots__ = 'http_client', 'url_template', 'lat', 'lng', 'zoom', 'w', 'h', 'tiles_x', 'tiles_y', 'image'

    def __init__(self, app, *, lat, lng, zoom, width, height):
        self.http_client = app['http_client']
        self.url_template = app['settings'].osm_root + '/{zoom}/{x}/{y}.png'
        self.lat = lat
        self.lng = lng
        self.zoom = zoom
        self.w = width
        self.h = height

        self.tiles_x = int(math.ceil(self.w / TILE_SIZE)) + 2
        self.tiles_y = int(math.ceil(self.h / TILE_SIZE)) + 2

        self.image = Image.new('RGB', (self.tiles_x * TILE_SIZE, self.tiles_y * TILE_SIZE), (0, 0, 0, 0))

    async def run(self) -> bytes:
        tiles = 2 ** self.zoom
        x_tiles = tiles * (self.lng + 180) / 360
        y = (1 - math.log(math.tan(math.radians(self.lat)) + (1/math.cos(math.radians(self.lat)))) / math.pi) / 2
        y_tiles = tiles * y
        x_offset, y_offset = int(x_tiles), int(y_tiles)

        rows = range(-int(math.floor(self.tiles_x / 2)), int(math.ceil(self.tiles_x / 2)))
        columns = range(-int(math.floor(self.tiles_y / 2)), int(math.ceil(self.tiles_y / 2)))

        await asyncio.gather(*self.get_tiles(columns, rows, x_offset, y_offset))

        x_left = rows.index(0) * TILE_SIZE + int((x_tiles - x_offset) * TILE_SIZE)
        y_top = columns.index(0) * TILE_SIZE + int((y_tiles - y_offset) * TILE_SIZE)

        crop_size = (
            x_left - (self.w / 2),
            y_top - (self.h / 2),
            x_left + (self.w / 2),
            y_top + (self.h / 2),
        )
        bio = io.BytesIO()
        self.image.crop([int(v) for v in crop_size]).save(bio, format='jpeg')
        return bio.getvalue()

    def get_tiles(self, columns, rows, x_offset, y_offset):
        for col_offset, y in enumerate(columns):
            for row_offset, x in enumerate(rows):
                yield self.get_tile(x_offset + x, y_offset + y, row_offset, col_offset)

    async def get_tile(self, x, y, row_offset, col_offset):
        url = self.url_template.format(zoom=self.zoom, x=x, y=y, shard=random.choice(SHARDS))
        # debug(url)
        async with self.http_client.get(url) as r:
            content = await r.read()
        if r.status != 200:
            data = {'content': content, 'response_headers': dict(r.headers)}
            logger.warning('unexpected status %d from %r', r.status, url, extra={'data': data})
        else:
            image = Image.open(io.BytesIO(content))
            self.image.paste(image, (row_offset * TILE_SIZE, col_offset * TILE_SIZE))
