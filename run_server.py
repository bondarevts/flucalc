#!/usr/bin/env python3
import sys
from flucalc.server import app


def main():
    app.run(debug='--debug' in sys.argv)


if __name__ == '__main__':
    main()

