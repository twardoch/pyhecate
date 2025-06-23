#!/usr/bin/env python3
"""
pyhecate
--------
Copyright (c) 2021 Adam Twardoch <adam+github@twardoch.com>
MIT license. Python 3.8+
"""

__all__ = ["__main__"]

import glob
import json
import logging
import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

import ffmpeg  # type: ignore
from send2trash import send2trash  # type: ignore

ISUMFREQ: int = 30
VSUMLENGTH: int = 16
GIFWIDTH: int = 360


class PyHecateVideo:
    def __init__(
        self,
        path: str,
        outdir: str,
        isumfreq: int = ISUMFREQ,
        vsumlength: int = VSUMLENGTH,
        outro: Optional[str] = None,
        vsum: bool = True,
        isum: bool = True,
        gifwidth: int = GIFWIDTH,
    ) -> None:
        # Quasi-constants
        self.gifwidth: int = gifwidth
        self.vsumlength: int = vsumlength
        self.mp4sumsuf: str = f"_sum-{vsumlength}.mp4"
        self.mp4outsuf: str = f"_outsum-{vsumlength}.mp4"
        # Params
        self.path: str = path
        self.outdir: str = outdir
        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)
        self.base: str = os.path.split(self.outdir)[1]
        self.isumfreq: int = isumfreq
        self.outro: Optional[str] = outro
        self.vsum: bool = vsum
        self.isum: bool = isum
        self.vseconds: int = 0
        self.vwidth: int = 0
        self.vheight: int = 0
        self.vaudio: bool = False
        self.vmeta: bool = False
        self.jpgdir: Optional[str] = None
        self.gifdir: Optional[str] = None
        self.gifsumdir: Optional[str] = None
        self.mp4dir: Optional[str] = None
        self.mp4sumpath: Optional[str] = None
        self.mp4tmppath: Optional[str] = None
        self.mp4outpath: Optional[str] = None
        self.numsnaps: int = 0

    def _video_meta(self, path: str) -> Tuple[bool, int, int, int, bool]:
        meta: Dict[str, Any] = {}
        vseconds: int = 0
        vwidth: int = 0
        vheight: int = 0
        vaudio: bool = False
        command: str = (
            f"ffprobe -v quiet -print_format json -show_format -show_streams {path}"
        )
        try:
            result = subprocess.run(
                command.split(), capture_output=True, text=True, check=True
            )
            if os.path.exists(path):  # Re-check after ffprobe, path might be gone
                meta = json.loads(result.stdout)
            else:
                logging.error(f"Video file disappeared during ffprobe: {path}")
                return False, 0, 0, 0, False
        except subprocess.CalledProcessError as e:
            logging.error(f"FFProbe failed for {path}, error: {e.stderr}")
            return False, 0, 0, 0, False
        except json.JSONDecodeError:
            logging.error(f"FFProbe output for {path} is not valid JSON.")
            return False, 0, 0, 0, False

        for stream in meta.get("streams", []):
            if stream.get("codec_type") == "video":
                vseconds = int(float(stream.get("duration", 0)))
                vwidth = int(stream.get("width", 0))
                vheight = int(stream.get("height", 0))
            if stream.get("codec_type") == "audio":
                vaudio = True

        if vwidth == 0 or vheight == 0:  # Ensure we got valid video dimensions
            logging.error(f"FFProbe could not determine video dimensions for {path}")
            return False, 0, 0, 0, False

        return True, vseconds, vwidth, vheight, vaudio

    def add_outro(self) -> bool:
        if (
            not self.outro or not self.mp4sumpath or not self.mp4outpath
        ):  # Should not happen if called correctly
            logging.error(
                "add_outro called with missing outro, mp4sumpath or mp4outpath"
            )
            return False

        ometa, _, _, _, oaudio = self._video_meta(self.outro)
        out = None
        if ometa:
            ffmpeg_args: List[str] = [
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
                _, serr = process.communicate()
                if process.returncode != 0:
                    logging.error(
                        f"ffmpeg error when adding outro: {serr.decode('utf8')}"
                    )
                    if os.path.exists(self.mp4outpath):
                        send2trash(self.mp4outpath)
                    return False
                return True
            except Exception as e:  # Broad exception for ffmpeg execution issues
                logging.error(f"Failed adding outro to {self.mp4sumpath}: {e}")
                if self.mp4outpath and os.path.exists(self.mp4outpath):
                    send2trash(self.mp4outpath)
                return False
        else:
            logging.warning(
                f"Could not process outro video {self.outro} or main summary video."
            )
            return False

    def run_hecate(self) -> bool:
        # Run hecate app
        hecate_cmd: List[str] = [
            "hecate",
            "--in_video",
            self.path,
            "--out_dir",
            self.outdir,
        ]
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

    def summarize(self) -> bool:
        (
            self.vmeta,
            self.vseconds,
            self.vwidth,
            self.vheight,
            self.vaudio,
        ) = self._video_meta(self.path)
        if not self.vmeta:
            return False

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
        path: str,
        dir_mode: bool = False,  # Renamed 'dir' to 'dir_mode' to avoid conflict with os.path.dir
        outdir: Optional[str] = None,
        isumfreq: int = ISUMFREQ,
        outro: Optional[str] = None,
        vsum: bool = True,
        isum: bool = True,
        vsumlength: int = VSUMLENGTH,
        gifwidth: int = GIFWIDTH,
    ) -> None:
        self.isumfreq: int = isumfreq
        self.vsumlength: int = vsumlength
        self.outro: Optional[str] = outro
        self.vsum: bool = vsum
        self.isum: bool = isum
        self.gifwidth: int = gifwidth
        self.vpaths: List[str] = []

        if not os.path.exists(path):
            logging.error(f"Input path does not exist: {path}")
            # Consider raising an error here or handling it so __init__ doesn't partially succeed
            return

        abs_path: str = os.path.abspath(path)
        if outdir:
            self.outdir: str = os.path.abspath(outdir)
        else:
            self.outdir = os.path.split(abs_path)[0] if not dir_mode else abs_path

        if not os.path.exists(self.outdir):
            os.makedirs(self.outdir)

        if dir_mode:
            if not os.path.isdir(abs_path):
                logging.error(
                    f"Input path {abs_path} is not a directory, but --dir mode was specified."
                )
                return
            self.vpaths = sorted(
                [
                    os.path.join(abs_path, p)
                    for p in os.listdir(abs_path)
                    if p.lower().endswith(".mp4")  # Consider other video formats?
                ]
            )
            if not self.vpaths:
                logging.warning(f"No .mp4 files found in directory: {abs_path}")
        else:
            if not os.path.isfile(abs_path):
                logging.error(f"Input path {abs_path} is not a file.")
                return
            self.vpaths = [abs_path]

        for vpath_item in self.vpaths:
            self.process_video(vpath_item)

    def process_video(
        self, vpath: str
    ) -> None:  # Renamed from summarize to avoid confusion
        logging.info(f"\n\nProcessing: {vpath}")
        time.sleep(1)  # Is this sleep necessary?
        dp: Tuple[str, str] = os.path.split(vpath)
        video_name_without_ext: str = os.path.splitext(dp[1])[0]

        # Determine specific output directory for this video
        # If processing a single file, outdir for PyHecate might be the parent of the video file.
        # The video-specific output should be a subfolder within that.
        # If processing a directory, self.outdir is that directory.
        # Individual video outputs should still go into subfolders.

        # If original outdir was, e.g. /path/to/videos/
        # and video is /path/to/videos/video1.mp4
        # then voutdir becomes /path/to/videos/video1/
        # If original outdir was /path/to/custom_output/
        # and video is /path/to/videos/video1.mp4
        # then voutdir becomes /path/to/custom_output/video1/

        voutdir: str = os.path.join(self.outdir, video_name_without_ext)

        pyh_video = PyHecateVideo(
            path=vpath,
            outdir=voutdir,
            isumfreq=self.isumfreq,
            vsumlength=self.vsumlength,
            outro=self.outro,
            vsum=self.vsum,
            isum=self.isum,
            gifwidth=self.gifwidth,
        )
        if not pyh_video.summarize():
            logging.error(f"Processing failed for: {vpath}")
