import argparse
import logging
import sys

from aiohttp import web

from .app import init

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', '-H', default='localhost')
    parser.add_argument('--port', '-P', type=int, default=8080)
    args, rest = parser.parse_known_args(args=argv)
    app = init(rest)
    logging.basicConfig(level=logging.DEBUG)
    web.run_app(app, host=args.host, port=args.port)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))