#!/usr/bin/env python3
"""
PyHecate Command Line Interface
"""

import logging
import sys  # For accessing version in Python 3.8+
from argparse import ArgumentParser, Namespace
from importlib.metadata import version as get_version
from typing import Any, Dict

import pyhecate

APP_VERSION = get_version("pyhecate")


def cli() -> ArgumentParser:
    parser = ArgumentParser(prog="pyhecate")

    path_group = parser.add_argument_group("paths and folders")
    path_group.add_argument(
        "path", metavar="path", type=str, help="path to video file or directory"
    )
    path_group.add_argument(
        "-d",
        "--dir",
        dest="dir_mode",  # Changed from 'dir' to 'dir_mode'
        action="store_true",
        help="input path is a folder with video files",
    )
    path_group.add_argument(
        "-o",
        "--outdir",
        dest="outdir",
        metavar="output_folder",
        type=str,
        help="output folder for created subfolders (defaults to input path parent or input path itself if --dir)",
    )

    image_group = parser.add_argument_group("make images")
    image_group.add_argument(
        "-i",
        "--image-every",
        dest="isumfreq",
        metavar="secs",
        default=pyhecate.ISUMFREQ,
        type=int,
        help=f"JPG snapshot frequency in seconds (default: {pyhecate.ISUMFREQ})",
    )
    image_group.add_argument(
        "-g",
        "--gif-width",
        dest="gifwidth",
        metavar="px",
        default=pyhecate.GIFWIDTH,
        type=int,
        help=f"GIF width (default: {pyhecate.GIFWIDTH})",
    )
    image_group.add_argument(
        "-I",
        "--skip-images",
        dest="isum",
        action="store_false",
        help="skip making JPG & GIF images",
    )

    video_group = parser.add_argument_group("make video summary")
    video_group.add_argument(
        "-s",
        "--video-length",
        dest="vsumlength",
        metavar="secs",
        default=pyhecate.VSUMLENGTH,
        type=int,
        help=f"video summary length in seconds (default: {pyhecate.VSUMLENGTH})",
    )
    video_group.add_argument(
        "-a",
        "--outro",
        dest="outro",
        metavar="path_to_outro_video",
        type=str,
        help="append outro video to summary video",
    )
    video_group.add_argument(
        "-S",
        "--skip-video-summary",
        dest="vsum",
        action="store_false",
        help="skip making the video summary MP4 file",
    )

    other_group = parser.add_argument_group("other")
    other_group.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=1,
        help="-v show progress (INFO), -vv show debug (DEBUG)",
    )
    other_group.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {APP_VERSION}",
        help="show version and exit",
    )

    return parser


def main(
    *args: Any, **kwargs: Any
) -> None:  # Added type hints for args/kwargs though they are not used
    arg_parser = cli()
    opts: Namespace = arg_parser.parse_args()

    # Configure logging
    log_level: int = logging.WARNING  # Default
    if opts.verbose == 1:
        log_level = logging.INFO
    elif opts.verbose >= 2:
        log_level = logging.DEBUG

    # For verbosity = 0 (e.g. if default was 0 and no -v given), it could be logging.ERROR or logging.CRITICAL
    # Current default is 1, so -v (opts.verbose=2) -> DEBUG, no flag (opts.verbose=1) -> INFO
    # If user provides -q or similar for less verbosity, that could be handled here too.

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Prepare options for PyHecate class
    # The 'dir' argument was renamed to 'dir_mode' in PyHecate class and CLI arguments
    # to avoid conflict with any potential 'dir' variable or built-in.
    pyhecate_opts: Dict[str, Any] = {
        "path": opts.path,
        "dir_mode": opts.dir_mode,  # Ensure this matches the class's expected argument name
        "outdir": opts.outdir,
        "isumfreq": opts.isumfreq,
        "outro": opts.outro,
        "vsum": opts.vsum,
        "isum": opts.isum,
        "vsumlength": opts.vsumlength,
        "gifwidth": opts.gifwidth,
    }

    logging.debug(f"Running with options: {pyhecate_opts}")

    # Instantiate and run PyHecate
    try:
        _ = pyhecate.PyHecate(**pyhecate_opts)
        # If PyHecate.__init__ can fail and return None or raise specific exceptions, handle here.
        # For now, assume it either completes or logs errors internally.
        # If there's a main processing method in PyHecate that needs to be called after init, do it here.
        # Based on current PyHecate, processing starts in __init__.
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
