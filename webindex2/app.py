from aiohttp import web
from aiohttp_jinja2 import setup as jinja2_setup
from jinja2 import PackageLoader, pass_context

from .filesystem import Filesystem
from .views import routes


def url_rewriter(env, prefix=None):
    url_for = env.globals['url']
    if prefix is None:
        return url_for
    @pass_context
    def _url_for(*args, **kwargs):
        url = url_for(*args, **kwargs)
        return url.with_path(f'{prefix}{url.path}')
    env.globals['url'] = _url_for
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
    env = jinja2_setup(
        app,
        loader=PackageLoader('webindex2'),
        extensions=["jinja2_humanize_extension.HumanizeExtension"],
    )
    url_rewriter(env, prefix=None)
    fs = Filesystem.from_spec(r'books|x:\finished|/books_protected')
    # fs = Filesystem.from_spec(r'books|x:\finished')
    app['fs'] = fs
    app.add_routes(route_rewriter(routes, prefix='/webindex'))
    #  app.add_routes(routes)
    return app

if __name__ == '__main__':
    web.run_app(init())