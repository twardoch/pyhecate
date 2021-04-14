#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
"""

import pyhecate
from argparse import ArgumentParser

PROG = 'pyhecate'

def cli():
    parser = ArgumentParser(
        prog="%s" % PROG
    )
    parser.add_argument(
        'path',
        metavar='path',
        help='path to video file'
    )
    parser.add_argument(
        "-d",
        "--dir",
        action='store_true',
        help='path is a folder with video files'
    )
    parser.add_argument(
        "-o",
        "--outdir",
        metavar="outdir",
        help = 'output folder for created folders'
    )
    parser.add_argument(
        "-s",
        "--snapevery",
        metavar="snapevery",
        default=30,
        type=int,
        help = 'make a JPG every n seconds'
    )
    parser.add_argument(
        "-a",
        "--outro",
        metavar="outro",
        help = 'append an outro video file to summary video'
    )
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version='%s %s' % (PROG, pyhecate.__version__),
        help='show version and exit'
    )

    return parser


def main(*args, **kwargs):
    parser = cli(*args, **kwargs)
    opts = parser.parse_args()
    if opts:
        opts = vars(opts)
        pyhecate.app(**opts)

if __name__ == '__main__':
    main()
