from pathlib import Path

from aiohttp.web import Response, FileResponse, HTTPBadRequest
from pydantic import BaseModel, conint, confloat, ValidationError

from .build_map import BuildMap

THIS_DIR = Path(__file__).parent
ROBOTS_TXT = THIS_DIR / 'robots.txt'


async def index(request):
    return FileResponse(request.app['index_path'])


async def robots(request):
    return FileResponse(ROBOTS_TXT)


class QueryModel(BaseModel):
    lat: confloat(ge=-90, le=90)
    lng: confloat(ge=-360, le=360)
    zoom: conint(gt=0, lt=20) = 17
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
