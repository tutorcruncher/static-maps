import asyncio
import io
import logging
import math
import random
from pathlib import Path
from statistics import mean
from time import time

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

FONT_FILE = str(THIS_DIR / 'HelveticaNeue.ttf')
COPYRIGHT_MSG = '© OpenStreetMap contributors'

MARKER_FILE = THIS_DIR / 'marker.png'
MARKER_WIDTH, MARKER_HEIGHT = 44, 73


class BuildMap:
    __slots__ = ('app', 'url_template', 'lat', 'lng', 'zoom', 'w', 'h', 'no_tiles', 'tiles', 'times', 'headers',
                 'marker', 'scale')

    def __init__(self, app, referrer, *, lat: float, lng: float, zoom: int,
                 width: int, height: int, marker: bool, scale: int):
        self.app = app
        self.url_template = app['settings'].osm_root + '/{zoom:d}/{x:d}/{y:d}.png'
        self.lat = lat
        self.lng = lng
        self.zoom = zoom
        self.w = width * scale
        self.h = height * scale
        self.marker = marker
        self.scale = scale
        self.no_tiles = 2 ** self.zoom

        self.tiles = set()
        self.times = []
        self.headers = dict(HEADERS)
        if referrer:
            self.headers['Referer'] = referrer

    async def run(self) -> bytes:
        x_tile = self.no_tiles * (self.lng + 180) / 360

        lat_rad = math.radians(self.lat)
        y_tile = self.no_tiles * (1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2

        x_range, x_correction = self.range_correction(x_tile, self.w)
        y_range, y_correction = self.range_correction(y_tile, self.h)

        await asyncio.gather(*self.get_tiles(x_range, x_correction, y_range, y_correction))

        logger.info('lat=%0.6f lng=%0.6f zoom=%d tiles=%d avg-download-time=%0.3fs', self.lat, self.lng, self.zoom,
                    len(self.times), mean(self.times))
        return await self.app.loop.run_in_executor(self.app['thread_pool'], self.build_image)

    @staticmethod
    def range_correction(tile_no, size):
        half_t = size / 2 / TILE_SIZE  # half the width/height in tiles
        min_, max_ = int(math.floor(tile_no - half_t)), int(math.ceil(tile_no + half_t))
        correction = (tile_no - min_) * TILE_SIZE - size / 2
        return range(min_, max_), intr(correction)

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
        async with self.app['osm_semaphore']:
            async with self.app['http_client'].get(url, headers=self.headers) as r:
                content = await r.read()
        self.times.append(time() - start)
        if r.status != 200:
            data = {'content': content, 'response_headers': dict(r.headers)}
            print(content.decode())
            logger.warning('unexpected status %d from %r', r.status, url, extra={'data': data})
        else:
            self.tiles.add((content, image_x, image_y))

    def build_image(self):
        img_bg = Image.new('RGBA', (self.w, self.h), (255, 255, 255, 255))

        for content, x, y in self.tiles:
            img_bg.paste(Image.open(io.BytesIO(content)), (x, y))

        img_fg = Image.new('RGBA', img_bg.size, (0, 0, 0, 0))
        rect_box = self.w - 205 * self.scale, self.h - 20 * self.scale, self.w, self.h
        ImageDraw.Draw(img_fg).rectangle(rect_box, fill=(255, 255, 255, 128))
        text_pos = self.w - 200 * self.scale, self.h - 20 * self.scale
        font = ImageFont.truetype(FONT_FILE, 14 * self.scale)
        ImageDraw.Draw(img_fg).text(text_pos, COPYRIGHT_MSG, fill=(0, 0, 0), font=font)

        if self.marker:
            with MARKER_FILE.open('rb') as f:
                img_m = Image.open(f)
                mw, mh = MARKER_WIDTH * self.scale / 4, MARKER_HEIGHT * self.scale / 4
                if self.scale != 4:
                    img_m = img_m.resize((intr(mw), intr(mh)))

                img_fg.paste(img_m, (intr(self.w / 2 - mw / 2), intr(self.h / 2 - mh)))

        bio = io.BytesIO()
        Image.alpha_composite(img_bg, img_fg).convert('RGB').save(bio, format='jpeg', quality=95, optimize=True)
        return bio.getvalue()


def intr(v):
    return int(round(v))
