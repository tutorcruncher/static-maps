from io import BytesIO

from PIL import Image


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
