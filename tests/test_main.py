from io import BytesIO

from PIL import Image
from pytest_toolbox.comparison import RegexStr

from tests.conftest import LogSortKey


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
    r = await cli.get('/map.jpg?lat=51&lng=-2&width=200&height=100')
    content = await r.read()
    assert r.status == 200, content
    image = Image.open(BytesIO(content))
    assert image.size == (200, 100)


async def test_map_invalid_args(cli):
    r = await cli.get('/map.jpg?lat=51')
    text = await r.text()
    assert r.status == 400, text
    assert text == (
        'Invalid get parameters:\n'
        '  lng: field required\n'
    )


async def test_osm_error(cli, dummy_server, caplog):
    r = await cli.get('/map.jpg?lat=45&lng=0&zoom=6&width=200&height=100')
    content = await r.read()
    assert r.status == 200, content
    image = Image.open(BytesIO(content))
    assert image.size == (200, 100)
    assert len(caplog.records) == 4
    r = caplog.records[0]
    assert r.getMessage() == RegexStr(r"unexpected status 429 from 'http://localhost:\d+/osm/6/\d\d/\d\d\.png'")


async def test_map_images(cli, dummy_server):
    r = await cli.get('/map.jpg?lat=85&lng=0&width=300&height=100')
    content = await r.read()
    assert r.status == 200, content
    image = Image.open(BytesIO(content))
    assert image.size == (300, 100)
    assert sorted(dummy_server.log, key=LogSortKey) == ['GET /osm/10/512/1.png > 200', (10, 512, 1, None)]


async def test_x_wrapped(cli, dummy_server):
    r = await cli.get('/map.jpg?lat=45&lng=-180&width=800&height=100')
    content = await r.read()
    assert r.status == 200, content
    image = Image.open(BytesIO(content))
    assert image.size == (800, 100)
    ds_log = sorted(dummy_server.log, key=LogSortKey)
    r = ds_log.pop(0)
    assert ds_log == [(10, 0, 368, None), (10, 1, 368, None), (10, 1023, 368, None)]
    assert '200' in r


async def test_not_y_cut(cli, dummy_server):
    r = await cli.get('/map.jpg?lat=0&lng=20&width=200&height=800&zoom=3')
    content = await r.read()
    assert r.status == 200, content
    image = Image.open(BytesIO(content))
    assert image.size == (200, 800)
    assert len(dummy_server.log) == 4


async def test_y_cut(cli, dummy_server):
    r = await cli.get('/map.jpg?lat=85&lng=20&width=200&height=800&zoom=3')
    content = await r.read()
    assert r.status == 200, content
    image = Image.open(BytesIO(content))
    assert image.size == (200, 800)
    assert len(dummy_server.log) == 2
    assert sorted(dummy_server.log, key=LogSortKey) == ['GET /osm/3/4/1.png > 200', (3, 4, 1, None)]


async def test_with_referer(cli, dummy_server):
    r = await cli.get('/map.jpg?lat=51&lng=-2', headers={'Referer': 'https://www.example.com/page/'})
    content = await r.read()
    assert r.status == 200, content
    image = Image.open(BytesIO(content))
    assert image.size == (600, 400)
    assert len(dummy_server.log) == 6
    assert dummy_server.log[0][3] == 'https://www.example.com/page/'


async def test_marker(cli):
    r = await cli.get('/map.jpg?lat=45&lng=0&marker=0&width=200&height=100')
    content = await r.read()
    assert r.status == 200, content
    image = Image.open(BytesIO(content))
    rgb = image.getpixel((100, 45))
    assert rgb[0] < 100

    r = await cli.get('/map.jpg?lat=45&lng=0&marker=1&width=200&height=100')
    content = await r.read()
    assert r.status == 200, content
    image = Image.open(BytesIO(content))
    rgb = image.getpixel((100, 45))
    assert rgb[0] > 100  # pixel is now "red" since it's on the marker


async def test_scale(cli):
    r = await cli.get('/map.jpg?lat=51&lng=-2&width=200&height=100&scale=2')
    content = await r.read()
    assert r.status == 200, content
    image = Image.open(BytesIO(content))
    assert image.size == (400, 200)
