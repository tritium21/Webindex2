import argparse
import logging
import os
import sys

from aiohttp import web

from .app import init
from .config import load

def main(args=None):
    CONF_PATH = os.environ.get('WEBINDEX_CONF', 'config.toml')
    parser = argparse.ArgumentParser(
        prog=f"{ sys.executable} -m {__package__}",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '--host', '-H',
        default='localhost',
        help="Host to listen on",
    )
    parser.add_argument(
        '--port', '-P',
        type=int, default=8080,
        help="Port to listen on"
    )
    parser.add_argument(
        '--config', '-c',
        default=CONF_PATH,
        help="Path to config file"
    )
    parser.add_argument(
        '--verbose', '-v',
        action='count', default=0,
        help="Log loudness"
    )
    args = parser.parse_args(args=args)
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(args.verbose, 2)]
    config = load(args.config)
    app = init(config)
    logging.basicConfig(level=level)
    web.run_app(app, host=args.host, port=args.port)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))