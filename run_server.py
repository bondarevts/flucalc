#!/usr/bin/env python3
import subprocess
import sys


def main():
    ip = '127.0.0.1'
    port = 5000
    workers_count = 4
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

    print('FluCalc started on http://{ip}:{port}'.format(ip=ip, port=port))
    subprocess.run('gunicorn -w {workers_count} -b {ip}:{port} flucalc.server:app'.format(
        workers_count=workers_count, ip=ip, port=port
    ), shell=True)


if __name__ == '__main__':
    main()

