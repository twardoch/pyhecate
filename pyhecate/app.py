#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import argparse
import shutil
import glob
import logging
import ffmpeg
from videoprops import get_video_properties
from sh import hecate

logging.basicConfig(level=logging.INFO)


def main():
    args = parser.parse_args()
    path = args.path
    if not(os.path.exists(path)):
        return False
    vid = get_video_properties(path)
    vwidth = vid['width']
    vseconds = int(float(vid['duration']))
    dir = args.dir
    if not dir:
        dir = os.path.splitext(path)[0]
    if not os.path.exists(dir):
        os.makedirs(dir)
    base = os.path.split(dir)[1]
    numsnaps = int(vseconds/args.snapevery)
    if numsnaps < 10:
        numsnaps = 10
    mp4dir = os.path.join(dir, "mp4")
    if not os.path.exists(mp4dir):
        os.makedirs(mp4dir)
    mp4temppath = os.path.join(dir, base + "_sum.mp4")
    mp4path = os.path.join(mp4dir, base + "_sum.mp4")
    if os.path.exists(mp4path):
        os.remove(mp4path)
    jpgdir = os.path.join(dir, "jpg")
    if not os.path.exists(jpgdir):
        os.makedirs(jpgdir)
    gifdir = os.path.join(dir, "gif")
    if not os.path.exists(gifdir):
        os.makedirs(gifdir)
    gifsumdir = os.path.join(dir, "gifsum")
    if not os.path.exists(gifsumdir):
        os.makedirs(gifsumdir)
    out = hecate(
        "--in_video", path,
        "--out_dir", dir,
        "--generate_mov",
        "--lmov", 16,
        "--mov_width_px", vwidth,
        "--generate_jpg",
        "--njpg", numsnaps,
        "--jpg_width_px", vwidth,
        "--generate_gifall",
        "--generate_gifsum",
        "--ngif", numsnaps,
        "--gif_width_px", 360
    )
    if os.path.exists(mp4temppath):
        outro = args.outro
        if not outro:
            shutil.move(mp4temppath, mp4path)
        else:
            if not os.path.exists(outro):
                shutil.move(mp4temppath, mp4path)
            else:
                in1 = ffmpeg.input(mp4temppath)
                in2 = ffmpeg.input(outro)
                v1 = in1.video
                a1 = in1.audio
                v2 = in2.video
                a2 = in2.audio
                joined = ffmpeg.concat(v1, a1, v2, a2, v=1, a=1).node
                v3 = joined[0]
                a3 = joined[1]
                out = ffmpeg.output(v3, a3, mp4path)
                out.run()
                if os.path.exists(mp4path):
                    os.remove(mp4temppath)
    jpgs = glob.glob(os.path.join(dir, "*.jpg"))
    for jpg in jpgs:
        dest = os.path.join(jpgdir, os.path.split(jpg)[1])
        shutil.move(jpg, dest)
    gifsumpath = os.path.join(dir, base + "_sum.gif")
    if os.path.exists(gifsumpath):
        dest = os.path.join(gifsumdir, os.path.split(gifsumpath)[1])
        shutil.move(gifsumpath, dest)
    gifs = glob.glob(os.path.join(dir, "*.gif"))
    for gif in gifs:
        dest = os.path.join(gifdir, os.path.split(gif)[1])
        shutil.move(gif, dest)
    return True

if __name__ == '__main__':
    main()
