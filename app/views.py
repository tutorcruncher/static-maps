import os
import re
from pathlib import Path

from aiohttp.web import FileResponse, HTTPBadRequest, Response
from pydantic import BaseModel, ValidationError, confloat, conint

from build_map import BuildMap

THIS_DIR = Path(__file__).parent
ROBOTS_TXT = THIS_DIR / 'robots.txt'


async def index(request):
    # for development:
    # path = build_index()
    # return Response(body=path.read_bytes(), content_type='text/html')
    return FileResponse(request.app['index_path'])


async def robots(request):
    return FileResponse(ROBOTS_TXT)


async def get_map(request):
    m: QueryModel = parse_request_query(request)
    builder = BuildMap(request.app, **m.dict())
    image = await builder.run()
    return Response(
        body=image,
        content_type='image/jpeg',
        headers={
            'Cache-Control': 'max-age=1209600',  # 1209600 is 14 days
            'X-Robots-Tag': 'noindex',
        }
    )


def build_index():
    ctx = {
        'COMMIT': os.getenv('COMMIT', '-'),
        'BUILD_TIME': os.getenv('BUILD_TIME', '-'),
    }
    index_html = (THIS_DIR / 'index.html').read_text()
    for key, value in ctx.items():
        index_html = re.sub(r'\{\{ ?%s ?\}\}' % key, value, index_html, flags=re.I)
    p = THIS_DIR / 'index.tmp.html'
    p.write_text(index_html)
    return p


class QueryModel(BaseModel):
    lat: confloat(ge=-90, le=90)
    lng: confloat(ge=-360, le=360)
    zoom: conint(gt=0, lt=20) = 10
    width: conint(ge=10, lt=2000) = 600
    height: conint(ge=10, lt=2000) = 400


def parse_request_query(request) -> QueryModel:
    """
    Like atoolbox.utils.parse_request_query but simplified and with a more human readable error response.
    """
    data = {}
    for k in QueryModel.__fields__.keys():
        v = request.query.get(k)
        if v is not None:
            data[k] = v

    try:
        return QueryModel(**data)
    except ValidationError as e:
        msg = 'Invalid get parameters:\n'
        for error in e.errors():
            msg += '  {loc[0]}: {msg}\n'.format(**error)
        raise HTTPBadRequest(text=msg)
