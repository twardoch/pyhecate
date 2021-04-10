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
        "--outdir",
        metavar="outdir"
    )
    parser.add_argument(
        "-s",
        "--snapevery",
        metavar="snapevery",
        default=30,
        type=int
    )
    parser.add_argument(
        "-a",
        "--outro",
        metavar="outro"
    )
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version='%s %s' % (PROG, pyhecate.__version__)
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
