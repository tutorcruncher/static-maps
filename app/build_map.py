import asyncio
import io
import logging
import math
import random
from asyncio import Semaphore
from pathlib import Path
from statistics import mean
from time import time

from aiohttp import ClientSession
from aiohttp.http import SERVER_SOFTWARE
from PIL import Image, ImageDraw, ImageFont

__all__ = 'THIS_DIR', 'BuildMap'

logger = logging.getLogger('app.build')
SHARDS = 'a', 'b', 'c'
TILE_SIZE = 256
HEADERS = {
    'User-Agent': f'{SERVER_SOFTWARE} https://github.com/tutorcruncher/static-maps'
}
THIS_DIR = Path(__file__).parent
font = ImageFont.truetype(str(THIS_DIR / 'HelveticaNeue.ttf'), 14)


class BuildMap:
    __slots__ = ('http_client', 'url_template', 'sem', 'lat', 'lng', 'zoom', 'width', 'height', 'no_tiles',
                 'image', 'times', 'headers')

    def __init__(self, app, referrer, *, lat, lng, zoom, width, height):
        self.http_client: ClientSession = app['http_client']
        self.url_template = app['settings'].osm_root + '/{zoom:d}/{x:d}/{y:d}.png'
        self.sem: Semaphore = app['osm_semaphore']
        self.lat = lat
        self.lng = lng
        self.zoom = zoom
        self.width = width
        self.height = height
        self.no_tiles = 2 ** self.zoom

        self.image = Image.new('RGB', (width, height), (255, 255, 255))
        self.times = []
        self.headers = dict(HEADERS)
        if referrer:
            self.headers['Referer'] = referrer

    async def run(self) -> bytes:
        x_tile = self.no_tiles * (self.lng + 180) / 360

        lat_rad = math.radians(self.lat)
        y_tile = self.no_tiles * (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2

        x_range, x_correction = self.range_correction(x_tile, self.width)
        y_range, y_correction = self.range_correction(y_tile, self.height)

        await asyncio.gather(*self.get_tiles(x_range, x_correction, y_range, y_correction))

        pos = self.width - 200, self.height - 20
        ImageDraw.Draw(self.image).text(pos, '© OpenStreetMap contributors', fill=(0, 0, 0), font=font)
        bio = io.BytesIO()
        self.image.save(bio, format='jpeg')
        logger.info('lat=%0.6f lng=%0.6f zoom=%d tiles=%d avg-download-time=%0.3fs', self.lat, self.lng, self.zoom,
                    len(self.times), mean(self.times))
        return bio.getvalue()

    @staticmethod
    def range_correction(tile_no, size):
        half_t = size / 2 / TILE_SIZE  # half the width/height in tiles
        min_, max_ = int(math.floor(tile_no - half_t)), int(math.ceil(tile_no + half_t))
        correction = (tile_no - min_) * TILE_SIZE - size / 2
        return range(min_, max_), int(round(correction))

    def get_tiles(self, x_range, x_correction, y_range, y_correction):
        for col, x in enumerate(x_range):
            for row, y in enumerate(y_range):
                yield self.get_tile(x, y, col * TILE_SIZE - x_correction, row * TILE_SIZE - y_correction)

    async def get_tile(self, osm_x, osm_y, image_x, image_y):
        if not 0 <= osm_y < self.no_tiles:
            return
        # wraps map around at edges
        osm_x = osm_x % self.no_tiles
        url = self.url_template.format(zoom=self.zoom, x=osm_x, y=osm_y, shard=random.choice(SHARDS))
        # debug(url, osm_x, osm_y, image_x, image_y)
        start = time()
        async with self.sem:
            async with self.http_client.get(url, headers=self.headers) as r:
                content = await r.read()
        self.times.append(time() - start)
        if r.status != 200:
            data = {'content': content, 'response_headers': dict(r.headers)}
            print(content.decode())
            logger.warning('unexpected status %d from %r', r.status, url, extra={'data': data})
        else:
            image = Image.open(io.BytesIO(content)).convert('RGB')
            # for testing
            # ImageDraw.Draw(image).rectangle((1, 1, 255, 255), outline=(0, 0, 0))
            # ImageDraw.Draw(image).text((20, 20), f'{osm_x}, {osm_y}', fill=(0, 0, 0))
            self.image.paste(image, (image_x, image_y))
