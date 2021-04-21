#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pyhecate
--------
Copyright (c) 2021 Adam Twardoch <adam+github@twardoch.com>
MIT license. Python 3.8+
"""
__version__ = "1.0.3"

__all__ = ['__main__']

import os
import shutil
import glob
import logging
import json
import subprocess
import tempfile
import time
import ffmpeg
from send2trash import send2trash

ISUMFREQ=30
VSUMLENGTH=16
GIFWIDTH=360

class PyHecateVideo(object):

    def __init__(
            self,
            path=None,
            dir=None,
            outdir=None,
            isumfreq=ISUMFREQ,
            vsumlength=VSUMLENGTH,
            outro=None,
            vsum=True,
            isum=True,
            gifwidth=GIFWIDTH
        ):
        # Quasi-constants
        self.mp4sumsuf = '_sum.mp4'
        self.mp4outsuf = '_outsum.mp4'
        self.gifwidth = gifwidth
        self.vsumlength = vsumlength
        # Params
        self.path = path
        self.dir = dir
        self.outdir = outdir
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)
        self.base = os.path.split(self.outdir)[1]
        self.isumfreq = isumfreq
        self.outro = outro
        self.vsum = vsum
        self.isum = isum
        self.vseconds = 0
        self.vwidth = 0
        self.vheight = 0
        self.vaudio = False
        self.vmeta = False
        self.jpgdir = None
        self.gifdir = None
        self.gifsumdir = None
        self.mp4dir = None
        self.mp4sumpath = None
        self.mp4tmppath = None
        self.mp4outpath = None
        self.numsnaps = 0

    def _video_meta(self, path):
        meta = {}
        vaudio = False
        command = (
            'ffprobe -v quiet -print_format json -show_format -show_streams '
            f'{path}'
        )
        result = subprocess.run(command.split(), capture_output=True)
        if result.returncode == 0 and os.path.exists(path):
            meta = json.loads(result.stdout)
        else:
            logging.error(
                f'FFProbe failed for {path}, output: {result.stderr}'
            )
            return (False, 0, 0, 0, False)
        for stream in meta.get('streams', []):
            if stream['codec_type'] == 'video':
                vseconds = int(float(stream['duration']))
                vwidth = stream['width']
                vheight = stream['height']
            if stream['codec_type'] == 'audio':
                vaudio = True
        return (True, vseconds, vwidth, vheight, vaudio)

    def add_outro(self):
        ometa, oseconds, owidth, oheight, oaudio = self._video_meta(self.outro)
        out = None
        if ometa:
            ffmpeg_args = ['-loglevel', 'error', '-nostdin', '-y']
            in1 = ffmpeg.input(self.mp4sumpath)
            in2 = ffmpeg.input(self.outro)
            v1 = in1.video
            v2 = in2.video
            if self.vaudio and oaudio:
                a1 = in1.audio
                a2 = in2.audio
                joined = ffmpeg.concat(v1, a1, v2, a2, v=1, a=1).node
                v3 = joined[0]
                a3 = joined[1]
                out = ffmpeg.output(v3, a3, self.mp4outpath).global_args(*ffmpeg_args)
            else:
                joined = ffmpeg.concat(v1, v2, v=1).node
                v3 = joined[0]
                out = ffmpeg.output(v3, self.mp4outpath).global_args(*ffmpeg_args)
        if out:
            return out.run()
        else:
            return None

    def run_hecate(self):
        # Run hecate app
        hecate_cmd = [
            "hecate",
            "--in_video", self.path,
            "--out_dir", self.outdir
        ]
        if self.vsum:
            hecate_cmd += [
                "--generate_mov",
                "--lmov", str(self.vsumlength),
                "--mov_width_px", str(self.vwidth),
            ]
        if self.isum:
            hecate_cmd += [
                "--generate_jpg",
                "--njpg", str(self.numsnaps),
                "--jpg_width_px", str(self.vwidth),
                "--generate_gifall",
                "--generate_gifsum",
                "--ngif", str(self.numsnaps),
                "--gif_width_px", str(self.gifwidth)
            ]
        logging.debug("Running hecate with:\n" + " ".join(hecate_cmd))
        return subprocess.run(hecate_cmd, capture_output=True)

    def prep_outfolders(self):
        # Prepare folders
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)
        self.numsnaps = max(int(self.vseconds / self.isumfreq), 10)
        if self.isum:
            self.jpgdir = os.path.join(self.outdir, "jpg")
            if not os.path.exists(self.jpgdir):
                os.makedirs(self.jpgdir)
            self.gifdir = os.path.join(self.outdir, "gif")
            if not os.path.exists(self.gifdir):
                os.makedirs(self.gifdir)
            self.gifsumdir = os.path.join(self.outdir, "gifsum")
            if not os.path.exists(self.gifsumdir):
                os.makedirs(self.gifsumdir)
        if self.vsum:
            self.mp4dir = os.path.join(self.outdir, "mp4")
            if not os.path.exists(self.mp4dir):
                os.makedirs(self.mp4dir)
            self.mp4tmppath = os.path.join(self.outdir, self.base + "_sum.mp4")
            if os.path.exists(self.mp4tmppath):
                send2trash(self.mp4tmppath)
            self.mp4sumpath = os.path.join(self.mp4dir, self.base + self.mp4sumsuf)
            self.mp4outpath = os.path.join(self.mp4dir, self.base + self.mp4outsuf)

    def cleanup_folders(self):
        # Reorganize and clean up
        if self.isum:
            jpgs = glob.glob(os.path.join(self.outdir, "*.jpg"))
            for jpg in jpgs:
                dest = os.path.join(self.jpgdir, os.path.split(jpg)[1])
                shutil.move(jpg, dest)
            gifsumpath = os.path.join(self.outdir, self.base + "_sum.gif")
            if os.path.exists(gifsumpath):
                dest = os.path.join(self.gifsumdir, os.path.split(gifsumpath)[1])
                shutil.move(gifsumpath, dest)
            gifs = glob.glob(os.path.join(self.outdir, "*.gif"))
            for gif in gifs:
                dest = os.path.join(self.gifdir, os.path.split(gif)[1])
                shutil.move(gif, dest)
        if self.vsum:
            if os.path.exists(self.mp4tmppath):
                shutil.move(self.mp4tmppath, self.mp4sumpath)
        return True

    def summarize(self):
        self.vmeta, self.vseconds, self.vwidth, self.vheight, self.vaudio = self._video_meta(self.path)
        if not self.vmeta:
            return False
        self.prep_outfolders()
        if not self.run_hecate():
            return False
        if self.cleanup_folders():
            if self.outro and os.path.exists(self.outro):
                if not self.add_outro():
                    return False
        return True

class PyHecate(object):

    def __init__(
            self,
            path=None,
            dir=None,
            outdir=None,
            isumfreq=ISUMFREQ,
            outro=None,
            vsum=True,
            isum=True,
            vsumlength=VSUMLENGTH,
            gifwidth=GIFWIDTH
        ):
        self.isumfreq = isumfreq
        self.vsumlength = vsumlength
        self.outro = outro
        self.vsum = vsum
        self.isum = isum
        self.gifwidth = gifwidth
        self.vpaths = []
        if not (os.path.exists(path)):
            return False
        if not outdir:
            self.outdir = os.path.split(os.path.abspath(path))[0]
        else:
            self.outdir = outdir
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)
        if dir:
            self.vpaths = sorted([os.path.abspath(p) for p in glob.glob(os.path.join(path, '*.mp4'))])
        else:
            self.vpaths = [os.path.abspath(path)]
        for vpath in self.vpaths:
            self.summarize(vpath)

    def summarize(self, vpath):
        logging.info('Processing:\n%s' % (vpath))
        time.sleep(1)
        dp = os.path.split(vpath)
        voutdir = os.path.join(self.outdir, os.path.splitext(dp[1])[0])
        pyh = PyHecateVideo(
            path=vpath,
            outdir=voutdir,
            isumfreq=self.isumfreq,
            vsumlength=self.vsumlength,
            outro=self.outro,
            vsum=self.vsum,
            isum=self.isum,
            gifwidth=self.gifwidth
        )
        if not pyh.summarize():
            logging.error('Processing failed:\n%s' % (vpath))
