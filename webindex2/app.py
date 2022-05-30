from pathlib import Path
import asyncio

from aiohttp import web
import aiohttp_jinja2
import jinja2
import natsort
from async_timeout import timeout

from .filesystem import Filesystem, Mount, Item
from .utils import partition
from .zipstream import zipstream

class PrefixingTable(web.RouteTableDef):
    def __init__(self, prefix='/webindex'):
        self._prefix = prefix
        super().__init__()

    def route(self, method, path, **kwargs):
        path = self._prefix + path
        return super().route(method, path, **kwargs)

    def static(self, prefix, path, **kwargs):
        prefix = self._prefix + prefix
        return super().static(prefix, path, **kwargs)


routes = PrefixingTable()
routes.static('/static', (Path(__file__).resolve().parent / 'static'), name='static')


@routes.get('/')
async def root(request):
    """Redirect the base url to /listing/
    """
    location = request.app.router['index'].url_for()
    raise web.HTTPFound(location=location)


@routes.get('/listing/{path:.+}', name="listing")
@routes.get('/listing/', name='index')
@aiohttp_jinja2.template('listing.html')
async def index(request):
    try:
        plo = request.app['fs'].navigate(request.match_info.get('path', ''))
    except FileNotFoundError:
        raise web.HTTPNotFound
    paths = [(await Item.from_path(x)) async for x in plo.iterdir()]
    dirs, files = partition(paths, lambda p: p.is_dir)
    dirs = natsort.os_sorted(dirs, key=lambda x: x.name)
    files = natsort.os_sorted(files, key=lambda x: x.name)
    crumbs = plo.crumbs
    return {'paths': dirs+files, 'cwd': plo.url, 'crumbs': crumbs}


@routes.get('/download/{path:.+}', name='download')
async def download(request):
    try:
        plo = request.app['fs'].navigate(request.match_info.get('path', ''))
    except FileNotFoundError:
        raise web.HTTPNotFound
    if await plo.is_dir():
        raise web.HTTPForbidden
    plo_item = await Item.from_path(plo)
    resp =  web.Response(content_type=plo_item.mimetype)
    resp.headers['X-Accel-Redirect'] = str(plo.x_accel_redirect_url)
    resp.headers['Content-Disposition'] = f'attachment; filename="{plo.name}"'
    return resp


@routes.get('/download-zip/{path:.+}.zip', name='download-zip')
async def download_zip(request):
    try:
        plo = request.app['fs'].navigate(request.match_info.get('path', ''))
    except FileNotFoundError:
        raise web.HTTPNotFound
    if not await plo.is_dir():
        raise web.HTTPForbidden
    osp = plo.os_path
    try:
        async with timeout(10):
            paths = osp.rglob('*')
    except asyncio.TimeoutError as e:
        raise web.HTTPInternalServerError from e
    files = [
        (p, str(p.relative_to(osp)))
        async for p in paths
    ]

    zstream = zipstream(files)
    response = web.StreamResponse(
        status=200,
        reason='OK',
        headers={'Content-Type': 'application/zip'},
    )
    await response.prepare(request)
    async for chunk in zstream:
        await response.write(chunk)
    await response.write_eof()
    return response


def init(argv=None):
    app = web.Application()
    env = aiohttp_jinja2.setup(
        app,
        loader=jinja2.PackageLoader('webindex2'),
        extensions=["jinja2_humanize_extension.HumanizeExtension"],
    )
    fs = Filesystem([
        Mount('books', r"x:\finished", '/books_protected'),
    ])
    app['fs'] = fs
    app.add_routes(routes)
    return app

if __name__ == '__main__':
    web.run_app(init())