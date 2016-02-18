#!/usr/bin/env python3
import logging
import sys
from flucalc.server import app


def main():
    ip = '127.0.0.1'
    port = 5000
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if ':' in arg:
                ip, port = arg.split(':')
                port = int(port)
                break
            if '.' in arg:
                ip = arg
            if arg.isdigit():
                port = int(arg)
    debug = '--debug' in sys.argv

    logging_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(filename='flucalc.log', level=logging_level,
                        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
    logging.info('Start server. ip=%s, port=%s.%s', ip, port, ' Debug mode' if debug else '')

    app.run(host=ip, port=port, debug=debug)


if __name__ == '__main__':
    main()

