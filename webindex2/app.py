from pathlib import Path
import asyncio
from sys import prefix

from aiohttp import web
import aiohttp_jinja2
import jinja2
import natsort
from async_timeout import timeout

from .filesystem import Filesystem, Mount, Item
from .utils import partition, read_file
from .zipstream import zipstream

routes = web.RouteTableDef()
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
    accelflag = plo.x_accel_redirect_url is not None
    response = web.StreamResponse()
    response.headers['Content-Type'] = plo_item.mimetype
    response.headers['Content-Disposition'] = f'attachment; filename="{plo.name}"'
    if accelflag:
        response.headers['X-Accel-Redirect'] = str(plo.x_accel_redirect_url)
    await response.prepare(request)
    if not accelflag:
        async for chunk in read_file(plo.os_path):
            await response.write(chunk)
    await response.write_eof()
    return response


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
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = f'attachment; filename="{plo.name}.zip"'
    await response.prepare(request)
    async for chunk in zstream:
        await response.write(chunk)
    await response.write_eof()
    return response


def url_rewriter(prefix=None):
    url_for = aiohttp_jinja2.GLOBAL_HELPERS['url']
    if prefix is None:
        return url_for
    @jinja2.pass_context
    def _url_for(*args, **kwargs):
        url = url_for(*args, **kwargs)
        return url.with_path(f'{prefix}{url.path}')
    return _url_for

def route_rewriter(routes, prefix=None):
    if prefix is None:
        return routes
    newroutes = []
    for item in routes:
        if isinstance(item, web.RouteDef):
            newroutes.append(web.RouteDef(
                method=item.method,
                path=f'{prefix}{item.path}',
                handler=item.handler,
                kwargs=item.kwargs
            ))
        elif isinstance(item, web.StaticDef):
            newroutes.append(web.StaticDef(
                prefix=f'{prefix}{item.prefix}',
                path=item.path,
                kwargs=item.kwargs,
            ))
    return newroutes

def init(argv=None):
    app = web.Application()
    env = aiohttp_jinja2.setup(
        app,
        loader=jinja2.PackageLoader('webindex2'),
        extensions=["jinja2_humanize_extension.HumanizeExtension"],
    )
    env.globals['url'] = url_rewriter(prefix=None)
    # fs = Filesystem([
    #     Mount('books', r"x:\finished", '/books_protected'),
    # ])
    fs = Filesystem([
        Mount('books', r"x:\finished", None),
    ])
    app['fs'] = fs
    app.add_routes(route_rewriter(routes, prefix='/webindex'))
    return app

if __name__ == '__main__':
    web.run_app(init())