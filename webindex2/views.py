from asyncio import TimeoutError
from pathlib import Path

from aiohttp import web
from aiohttp_jinja2 import template
from async_timeout import timeout
from natsort import os_sorted

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
@template('listing.html')
async def index(request):
    try:
        plo = await request.app['fs'].navigate(request.match_info.get('path', ''))
    except FileNotFoundError:
        raise web.HTTPNotFound
    paths = [x async for x in plo.iterdir()]
    dirs, files = partition(paths, lambda p: p.is_dir)
    dirs = os_sorted(dirs, key=lambda x: x.name)
    files = os_sorted(files, key=lambda x: x.name)
    crumbs = await plo.crumbs
    return {'paths': dirs+files, 'cwd': plo.url, 'crumbs': crumbs}


@routes.get('/download/{path:.+}', name='download')
async def download(request):
    try:
        plo = await request.app['fs'].navigate(request.match_info.get('path', ''))
    except FileNotFoundError:
        raise web.HTTPNotFound
    if plo.is_dir:
        raise web.HTTPForbidden
    accelflag = plo.x_accel_redirect_url != ''
    response = web.StreamResponse()
    response.headers['Content-Type'] = plo.mimetype
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
        plo = await request.app['fs'].navigate(request.match_info.get('path', ''))
    except FileNotFoundError:
        raise web.HTTPNotFound
    if not plo.is_dir:
        raise web.HTTPForbidden
    osp = plo.os_path
    try:
        async with timeout(10):
            paths = osp.rglob('*')
    except TimeoutError as e:
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