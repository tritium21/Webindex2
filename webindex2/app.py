from pathlib import Path

from aiohttp import web
import aiohttp_jinja2
import jinja2
import natsort

from .filesystem import Filesystem, Mount, Item
from .utils import partition



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
@routes.get('/download-zip/{path:.+}', name='download-zip')
async def download(request):
    return web.Response(text=f"You tried to download: '{request.match_info.get('path', '')}'")



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