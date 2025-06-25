#!/usr/bin/env python3
"""
pyhecate
--------
Copyright (c) 2021 Adam Twardoch <adam+github@twardoch.com>
MIT license. Python 3.8+
"""

__version__ = "1.0.3"

__all__ = ["__main__"]

import glob
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time

import ffmpeg
from send2trash import send2trash

ISUMFREQ = 30
VSUMLENGTH = 16
GIFWIDTH = 360


class PyHecateVideo:
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
        gifwidth=GIFWIDTH,
    ):
        # Quasi-constants
        self.gifwidth = gifwidth
        self.vsumlength = vsumlength
        self.mp4sumsuf = "_sum-%s.mp4" % vsumlength
        self.mp4outsuf = "_outsum-%s.mp4" % vsumlength
        # Params
        self.path: str = path
        self.outdir: str = outdir
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
            f"ffprobe -v quiet -print_format json -show_format -show_streams {path}"
        )
        result = subprocess.run(command.split(), capture_output=True)
        if result.returncode == 0 and os.path.exists(path):
            meta = json.loads(result.stdout)
        else:
            logging.error(f"FFProbe failed for {path}, output: {result.stderr}")
            return (False, 0, 0, 0, False)
        for stream in meta.get("streams", []):
            if stream["codec_type"] == "video":
                vseconds = int(float(stream["duration"]))
                vwidth = stream["width"]
                vheight = stream["height"]
            if stream["codec_type"] == "audio":
                vaudio = True
        return (True, vseconds, vwidth, vheight, vaudio)

    def add_outro(self):
        ometa, oseconds, owidth, oheight, oaudio = self._video_meta(self.outro)
        out = None
        if ometa:
            ffmpeg_args = [
                "-loglevel",
                "error",
                "-max_muxing_queue_size",
                "9999",
                "-nostdin",
                "-y",
            ]
            try:
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
                    out = ffmpeg.output(v3, a3, self.mp4outpath).global_args(
                        *ffmpeg_args
                    )
                else:
                    joined = ffmpeg.concat(v1, v2, v=1).node
                    v3 = joined[0]
                    out = ffmpeg.output(v3, self.mp4outpath).global_args(*ffmpeg_args)
            except ffmpeg.Error as e:
                logging.error(
                    f"ffmpeg error during input/concat setup for outro: {e.stderr.decode('utf8') if e.stderr else e}"
                )
                if self.mp4outpath and os.path.exists(self.mp4outpath):
                    send2trash(self.mp4outpath)
                return False

        if out:
            try:
                process = out.run_async(pipe_stdout=True, pipe_stderr=True)
                sout, serr = process.communicate()
                if serr:
                    logging.error("ffmpeg error when adding outro:\n%s" % serr)
                    send2trash(self.mp4outpath)
                    return False
                else:
                    return True
            except:
                logging.error("Failed adding outro to:\n%s" % self.mp4sumpath)
                send2trash(self.mp4outpath)
                return False
        else:
            logging.warning(
                f"Could not process outro video {self.outro} or main summary video."
            )
            return False

    def run_hecate(self) -> bool:
        """
        Runs the 'hecate' command-line tool to generate video summaries and images.

        The specific 'hecate' commands (for video summary, JPGs, GIFs) are
        determined by the instance attributes self.vsum, self.isum, and related
        parameters (vsumlength, numsnaps, vwidth, gifwidth).

        Returns:
            True if 'hecate' executed successfully.
            False if 'hecate' failed or was not found.
        """
        # Run hecate app
        hecate_cmd = ["hecate", "--in_video", self.path, "--out_dir", self.outdir]
        if self.vsum:
            hecate_cmd += [
                "--generate_mov",
                "--lmov",
                str(self.vsumlength),
                "--mov_width_px",
                str(self.vwidth),
            ]
        if self.isum:
            hecate_cmd += [
                "--generate_jpg",
                "--njpg",
                str(self.numsnaps),
                "--jpg_width_px",
                str(self.vwidth),
                "--generate_gifall",
                "--generate_gifsum",
                "--ngif",
                str(self.numsnaps),
                "--gif_width_px",
                str(self.gifwidth),
            ]
        logging.debug(f"Running hecate with: {' '.join(hecate_cmd)}")
        try:
            result = subprocess.run(
                hecate_cmd, capture_output=True, text=True, check=True
            )
            logging.debug(f"Hecate output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Hecate failed for {self.path}: {e.stderr}")
            return False
        except FileNotFoundError:
            logging.error(
                "Hecate command not found. Please ensure it is installed and in your PATH."
            )
            return False

    def prep_outfolders(self) -> None:
        """
        Prepares output folders for JPGs, GIFs, and MP4 summaries.

        It creates necessary subdirectories (e.g., 'jpg-1280', 'gif-360', 'mp4-16')
        within self.outdir based on processing options and video dimensions.
        It also defines paths for temporary and final summary files.

        Raises:
            ValueError: If self.isumfreq is negative.
        """
        # Prepare folders
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)
        if self.isumfreq < 0:
            raise ValueError("isumfreq must be non-negative")
        self.numsnaps = (
            max(int(self.vseconds / self.isumfreq), 10) if self.isumfreq > 0 else 10
        )
        if self.isum:
            self.jpgdir = os.path.join(self.outdir, f"jpg-{self.vwidth}")
            if not os.path.exists(self.jpgdir):
                os.makedirs(self.jpgdir)
            self.gifdir = os.path.join(self.outdir, f"gif-{self.gifwidth}")
            if not os.path.exists(self.gifdir):
                os.makedirs(self.gifdir)
            self.gifsumdir = os.path.join(self.outdir, f"gifsum-{self.gifwidth}")
            if not os.path.exists(self.gifsumdir):
                os.makedirs(self.gifsumdir)
        if self.vsum:
            self.mp4dir = os.path.join(self.outdir, f"mp4-{self.vsumlength}")
            if not os.path.exists(self.mp4dir):
                os.makedirs(self.mp4dir)
            self.mp4tmppath = os.path.join(self.outdir, f"{self.base}_sum.mp4")
            if os.path.exists(self.mp4tmppath):
                send2trash(self.mp4tmppath)
            self.mp4sumpath = os.path.join(self.mp4dir, f"{self.base}{self.mp4sumsuf}")
            self.mp4outpath = os.path.join(self.mp4dir, f"{self.base}{self.mp4outsuf}")

    def cleanup_folders(self) -> bool:
        """
        Reorganizes and cleans up files generated by 'hecate'.

        Moves JPGs, summary GIFs, and individual GIFs from the base output
        directory (self.outdir, which is the video-specific output dir)
        into their respective subdirectories (e.g., 'jpg-1280', 'gifsum-360').
        Also moves the temporary MP4 summary to its final location.

        Returns:
            True if cleanup was successful or if no cleanup was needed for a category.
            False if essential paths (like self.jpgdir) were not initialized,
            which indicates a problem in `prep_outfolders`.
        """
        # Reorganize and clean up
        if self.isum:
            if (
                not self.jpgdir or not self.gifdir or not self.gifsumdir
            ):  # Should be set in prep_outfolders
                logging.error(
                    "Image output directories not initialized in cleanup_folders."
                )
                return False
            jpgs: List[str] = glob.glob(os.path.join(self.outdir, "*.jpg"))
            for jpg in jpgs:
                dest: str = os.path.join(self.jpgdir, os.path.split(jpg)[1])
                shutil.move(jpg, dest)
            gifsumpath: str = os.path.join(self.outdir, f"{self.base}_sum.gif")
            if os.path.exists(gifsumpath):
                dest = os.path.join(self.gifsumdir, os.path.split(gifsumpath)[1])
                shutil.move(gifsumpath, dest)
            gifs: List[str] = glob.glob(os.path.join(self.outdir, "*.gif"))
            for gif in gifs:
                dest = os.path.join(self.gifdir, os.path.split(gif)[1])
                shutil.move(gif, dest)
        if self.vsum:
            if (
                not self.mp4tmppath or not self.mp4sumpath
            ):  # Should be set in prep_outfolders
                logging.error("Video output paths not initialized in cleanup_folders.")
                return False
            if os.path.exists(self.mp4tmppath):
                shutil.move(self.mp4tmppath, self.mp4sumpath)
        return True

    def summarize(self):
        self.vmeta, self.vseconds, self.vwidth, self.vheight, self.vaudio = (
            self._video_meta(self.path)
        )
        if not self.vmeta:
            return False

        self.vmeta = video_meta[
            "success"
        ]  # Though already checked, set for consistency if used elsewhere
        self.vseconds = video_meta["vseconds"]
        self.vwidth = video_meta["vwidth"]
        self.vheight = video_meta["vheight"]
        self.vaudio = video_meta["vaudio"]

        self.prep_outfolders()

        if not self.run_hecate():
            return False

        if not self.cleanup_folders():
            return False

        if (
            self.vsum
            and self.outro
            and os.path.exists(self.outro)
            and self.mp4sumpath
            and os.path.exists(self.mp4sumpath)
        ):
            if not self.add_outro():
                # Logged in add_outro, but we might want to indicate failure source
                logging.warning(f"Failed to add outro to {self.path}")
                # Depending on desired behavior, this could be a hard False or just a warning
        return True


class PyHecate:
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
        gifwidth=GIFWIDTH,
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
            self.outdir = os.path.split(abs_path)[0] if not dir_mode else abs_path

        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)
        if dir:
            self.vpaths = sorted(
                [os.path.abspath(p) for p in glob.glob(os.path.join(path, "*.mp4"))]
            )
        else:
            self.vpaths = [os.path.abspath(path)]
        for vpath in self.vpaths:
            self.summarize(vpath)

    def summarize(self, vpath):
        logging.info("\n\nProcessing:\n%s" % (vpath))
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
            gifwidth=self.gifwidth,
        )
        if not pyh.summarize():
            logging.error("Processing failed:\n%s" % (vpath))
