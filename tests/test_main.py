from io import BytesIO

from PIL import Image
from pytest_toolbox.comparison import RegexStr


async def test_index(cli):
    r = await cli.get('/')
    text = await r.text()
    assert r.status == 200, text
    assert 'Generator of map images.' in text


async def test_robots_txt(cli):
    r = await cli.get('/robots.txt')
    text = await r.text()
    assert r.status == 200, text
    assert text.startswith('User-agent: *')


async def test_map_success(cli):
    r = await cli.get('/map.jpg?lat=51&lng=-2&width=20&height=10')
    content = await r.read()
    assert r.status == 200, content
    image = Image.open(BytesIO(content))
    assert image.size == (20, 10)


async def test_map_invalid_args(cli):
    r = await cli.get('/map.jpg?lat=51')
    text = await r.text()
    assert r.status == 400, text
    assert text == (
        'Invalid get parameters:\n'
        '  lng: field required\n'
    )


async def test_osm_error(cli, dummy_server, caplog):
    r = await cli.get('/map.jpg?lat=45&lng=0&zoom=6&width=20&height=10')
    content = await r.read()
    assert r.status == 200, content
    image = Image.open(BytesIO(content))
    assert image.size == (20, 10)
    assert len(caplog.records) == 9
    r = caplog.records[0]
    assert r.getMessage() == RegexStr(r"unexpected status 429 from 'http://localhost:\d+/osm/6/\d\d/\d\d\.png'")
