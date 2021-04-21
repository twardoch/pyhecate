# pyhecate

Automagically generate thumbnails, animated GIFs, and summaries from videos on macOS.

Python CLI wrapper for https://github.com/twardoch/hecate

## Installation

First [install `hecate`](https://github.com/twardoch/hecate/blob/master/README.md), then install this via `python3 -m install --user --upgrade git+https://github.com/twardoch/pyhecate/`

## Usage

```
usage: pyhecate [-h] [-d] [-o output_folder] [-i secs] [-g px] [-I] [-s secs]
                [-a path_to_outro_video] [-S] [-v] [-V]
                path

optional arguments:
  -h, --help            show this help message and exit

paths and folders:
  path                  path to video file
  -d, --dir             path is a folder with video files
  -o output_folder, --outdir output_folder
                        output folder for created folders

make images:
  -i secs, --image-every secs
                        JPG snapshot frequency in seconds (default: 30)
  -g px, --gif-width px
                        GIF width (default: 360)
  -I, --skip-images     skip making JPG & GIF images

make video summary:
  -s secs, --video-length secs
                        video summary length in seconds (default: 16)
  -a path_to_outro_video, --outro path_to_outro_video
                        append outro video to summary video
  -S, --skip-video-summary
                        skip making the video summary MP4 file

other:
  -v, --verbose         -v show progress, -vv show debug
  -V, --version         show version and exit
```


## Requirements

- macOS 11 (may work on older or other systems)
- Python 3.8+ (tested on 3.9)

## Credits

- Copyright (c) 2021 Adam Twardoch
- [MIT license](./LICENSE)
