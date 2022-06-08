import argparse
import logging
import os
import pathlib
import sys

try:
    import asyncio
    import uvloop  # type: ignore
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

from aiohttp import web

from .app import init
from .config import load


def main(args=None):
    CONF_PATH = os.environ.get('WEBINDEX_CONF', 'config.toml')
    parser = argparse.ArgumentParser(
        prog=f"{__package__}",
        formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=52),
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count', default=0,
        help="Log loudness"
    )
    mag = parser.add_mutually_exclusive_group(required=True)
    mag.add_argument(
        '-H', '--host',
        default='localhost',
        help="Host to listen on",
    )
    parser.add_argument(
        '-P', '--port',
        type=int, default=8080,
        help="Port to listen on"
    )
    mag.add_argument(
        '-U', '--unix',
        metavar='PATH',
        help="Unix Socket to listen on"
    )
    parser.add_argument(
        '-c', '--config',
        type=pathlib.Path,
        default=pathlib.Path(CONF_PATH).resolve(),
        metavar='PATH',
        help="Path to config file"
    )
    args = parser.parse_args(args=args)
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(args.verbose, 2)]
    config = load(pathlib.Path(args.config).resolve())
    app = init(config)
    logging.basicConfig(level=level)
    if args.path:
        web.run_app(app, path=args.path)
    else:
        web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))