#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pyhecate
--------
Copyright (c) 2021 Adam Twardoch <adam+github@twardoch.com>
MIT license. Python 3.8+
"""
__version__ = "1.0.1"

__all__ = ['__main__']

import os
import shutil
import glob
import logging
import ffmpeg
import json
import subprocess
import tempfile

logging.basicConfig(level=logging.INFO)


def video_meta(path):
    temppath = tempfile.mktemp()
    shutil.copy(path, temppath)
    vseconds = None
    vwidth = None
    vheight = None
    vaudio = None
    meta = {}
    command = (
        'ffprobe -v quiet -print_format json -show_format -show_streams '
        f'{temppath}'
    )
    result = subprocess.run(command.split(), capture_output=True)
    if result.returncode == 0 and os.path.exists(path):
        meta = json.loads(result.stdout)
    else:
        raise RuntimeError(
            f'FFProbe failed for {path}, output: {result.stderr}'
        )
    os.remove(temppath)
    for stream in meta.get('streams', []):
        if stream['codec_type'] == 'video':
            vseconds = int(float(stream['duration']))
            vwidth = stream['width']
            vheight = stream['height']
        if stream['codec_type'] == 'audio':
            hasaudio = True
    return (vseconds, vwidth, vheight, vaudio)


def add_outro(mp4temppath, outropath, mp4path, vaudio):
    oseconds, owidth, oheight, oaudio = video_meta(outropath)
    out = None
    ffmpegGlobalArguments = ['-loglevel', 'error', '-nostdin', '-y']
    in1 = ffmpeg.input(mp4temppath)
    in2 = ffmpeg.input(outropath)
    v1 = in1.video
    v2 = in2.video
    if vaudio and oaudio:
        a1 = in1.audio
        a2 = in2.audio
        joined = ffmpeg.concat(v1, a1, v2, a2, v=1, a=1).node
        v3 = joined[0]
        a3 = joined[1]
        out = ffmpeg.output(v3, a3, mp4path).global_args(*ffmpegGlobalArguments)
    else:
        joined = ffmpeg.concat(v1, v2, v=1).node
        v3 = joined[0]
        out = ffmpeg.output(v3, mp4path).global_args(*ffmpegGlobalArguments)
    if out:
        out.run()
        if os.path.exists(mp4path):
            os.remove(mp4temppath)

def procvid(path=None, outdir=None, snapevery=30, outro=None):
    vseconds, vwidth, vheight, vaudio = video_meta(path)
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    else:
        os.makedirs(outdir)
    base = os.path.split(outdir)[1]
    numsnaps = max(int(vseconds / snapevery), 10)
    mp4dir = os.path.join(outdir, "mp4")
    if not os.path.exists(mp4dir):
        os.makedirs(mp4dir)
    mp4temppath = os.path.join(outdir, base + "_sum.mp4")
    mp4path = os.path.join(mp4dir, base + "_sum.mp4")
    if os.path.exists(mp4path):
        os.remove(mp4path)
    jpgdir = os.path.join(outdir, "jpg")
    if not os.path.exists(jpgdir):
        os.makedirs(jpgdir)
    gifdir = os.path.join(outdir, "gif")
    if not os.path.exists(gifdir):
        os.makedirs(gifdir)
    gifsumdir = os.path.join(outdir, "gifsum")
    if not os.path.exists(gifsumdir):
        os.makedirs(gifsumdir)
    hecate_cmd = [
        "hecate",
        "--in_video", path,
        "--out_dir", outdir,
        "--generate_mov",
        "--lmov", str(16),
        "--mov_width_px", str(vwidth),
        "--generate_jpg",
        "--njpg", str(numsnaps),
        "--jpg_width_px", str(vwidth),
        "--generate_gifall",
        "--generate_gifsum",
        "--ngif", str(numsnaps),
        "--gif_width_px", str(360)
    ]
    print(" ".join(hecate_cmd))
    hecate_out = subprocess.run(hecate_cmd, capture_output=True)
    if not hecate_out:
        return False
    if os.path.exists(mp4temppath):
        if outro and not os.path.exists(outro) or not outro:
            shutil.move(mp4temppath, mp4path)
        else:
            add_outro(mp4temppath, outro, mp4path, vaudio)
    jpgs = glob.glob(os.path.join(outdir, "*.jpg"))
    for jpg in jpgs:
        dest = os.path.join(jpgdir, os.path.split(jpg)[1])
        shutil.move(jpg, dest)
    gifsumpath = os.path.join(outdir, base + "_sum.gif")
    if os.path.exists(gifsumpath):
        dest = os.path.join(gifsumdir, os.path.split(gifsumpath)[1])
        shutil.move(gifsumpath, dest)
    gifs = glob.glob(os.path.join(outdir, "*.gif"))
    for gif in gifs:
        dest = os.path.join(gifdir, os.path.split(gif)[1])
        shutil.move(gif, dest)
    return os.path.exists(mp4path)

def app(path=None, dir=None, outdir=None, snapevery=30, outro=None):
    if not (os.path.exists(path)):
        return False
    if not outdir:
        outdir = os.path.split(path)[0]
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    if dir:
        vpaths = [os.path.abspath(p) for p in glob.glob(os.path.join(path, '*.mp4'))]
    else:
        vpaths = [os.path.abspath(path)]
    for vpath in vpaths:
        logging.info('\n\nPROCESSING %s' % (vpath))
        dp = os.path.split(vpath)
        voutdir = os.path.join(outdir, os.path.splitext(dp[1])[0])
        if procvid(vpath, voutdir, snapevery, outro):
            logging.info('SUCCESS: %s' % (vpath))
        else:
            logging.error('FAIL: %s' % (vpath))
    return True
