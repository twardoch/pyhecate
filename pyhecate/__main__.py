#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
"""

import pyhecate
from argparse import ArgumentParser
import logging

PROG = 'pyhecate'

def cli():
    parser = ArgumentParser(
        prog="%s" % PROG
    )
    group = parser.add_argument_group('paths and folders')
    group.add_argument(
        'path',
        metavar='path',
        help='path to video file'
    )
    group.add_argument(
        "-d",
        "--dir",
        dest='dir',
        action='store_true',
        help='path is a folder with video files'
    )
    group.add_argument(
        "-o",
        "--outdir",
        dest='outdir',
        metavar="output_folder",
        help = 'output folder for created folders'
    )
    group = parser.add_argument_group('make images')
    group.add_argument(
        "-i",
        "--image-every",
        dest='isumfreq',
        metavar="secs",
        default=pyhecate.ISUMFREQ,
        type=int,
        help = 'JPG snapshot frequency in seconds (default: %(default)s)'
    )
    group.add_argument(
        "-g",
        "--gif-width",
        dest='gifwidth',
        metavar="px",
        default=pyhecate.GIFWIDTH,
        type=int,
        help='GIF width (default: %(default)s)'
    )
    group.add_argument(
        "-I",
        "--skip-images",
        dest='isum',
        action='store_false',
        help='skip making JPG & GIF images'
    )
    group = parser.add_argument_group('make video summary')
    group.add_argument(
        "-s",
        "--video-length",
        dest='vsumlength',
        metavar="secs",
        default=pyhecate.VSUMLENGTH,
        type=int,
        help='video summary length in seconds (default: %(default)s)'
    )
    group.add_argument(
        "-a",
        "--outro",
        dest='outro',
        metavar="path_to_outro_video",
        help = 'append outro video to summary video'
    )
    group.add_argument(
        "-S",
        "--skip-video-summary",
        dest='vsum',
        action='store_false',
        help='skip making the video summary MP4 file'
    )
    group = parser.add_argument_group('other')
    group.add_argument(
        '-v',
        '--verbose',
        action='count',
        default=1,
        help='-v show progress, -vv show debug'
    )
    group.add_argument(
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
    opts.verbose = 40 - (10 * opts.verbose) if opts.verbose > 0 else 0
    logging.basicConfig(level=opts.verbose, format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
    opts = vars(opts)
    logging.debug('Running with options:\n%s' % repr(opts))
    del opts['verbose']
    pyh = pyhecate.PyHecate(**opts)

if __name__ == '__main__':
    main()
