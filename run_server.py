#!/usr/bin/env python3
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
    app.run(host=ip, port=port, debug=debug)


if __name__ == '__main__':
    main()

