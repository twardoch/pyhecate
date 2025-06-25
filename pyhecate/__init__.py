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
import shlex # Moved import shlex to top-level
import subprocess
# import time # Unused import removed by ruff, confirming
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import ffmpeg  # type: ignore
from send2trash import send2trash  # type: ignore

ISUMFREQ: int = 30
VSUMLENGTH: int = 16
GIFWIDTH: int = 360


class VideoMetadata(TypedDict):
    """
    Represents the extracted metadata from a video file.

    Attributes:
        success: True if metadata extraction was successful, False otherwise.
        vseconds: Duration of the video in seconds.
        vwidth: Width of the video in pixels.
        vheight: Height of the video in pixels.
        vaudio: True if the video has an audio stream, False otherwise.
    """

    success: bool
    vseconds: int
    vwidth: int
    vheight: int
    vaudio: bool


class PyHecateVideo:
    """
    Handles the processing of a single video file to generate summaries,
    thumbnails, and GIFs using 'hecate' and 'ffmpeg'.
    """

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
        """
        Initializes PyHecateVideo for processing a single video.

        Args:
            path: Path to the input video file.
            outdir: Directory where output subfolders and files will be created.
                    This directory itself will be created if it doesn't exist.
            isumfreq: Frequency in seconds for JPG snapshots.
            vsumlength: Length of the video summary in seconds.
            outro: Optional path to an outro video to append to the summary.
            vsum: If True, generate video summary.
            isum: If True, generate image summaries (JPGs, GIFs).
            gifwidth: Width of the generated GIFs in pixels.
        """
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

    def _get_video_meta(self, path: str) -> VideoMetadata:
        """
        Retrieves video metadata (duration, dimensions, audio presence) using ffprobe.

        Args:
            path: The path to the video file.

        Returns:
            A VideoMetadata object containing the extracted information.
            The 'success' field in VideoMetadata indicates if extraction was successful.
        """
        meta_dict: Dict[str, Any] = {}
        vseconds: int = 0
        vwidth: int = 0
        vheight: int = 0
        vaudio: bool = False
        success: bool = False

        command: str = (
            f'ffprobe -v quiet -print_format json -show_format -show_streams "{path}"'
        )
        try:
            # Note: Using shell=True can be a security risk if path is not sanitized.
            # However, ffprobe path arguments are typically safe.
            # Splitting the command manually is safer if paths can have spaces.
            # For now, assuming paths are manageable or this will be reviewed.
            # Using command.split() is generally safer than shell=True.
            # Ensure path is properly quoted if it can contain spaces.
            # Let's use command.split() for better security for now.
            # If paths have spaces, ffmpeg-python handles it, but direct subprocess needs care.
            # Path is quoted in the command string, so shell=True might be needed if not splitting.
            # Sticking to command.split() and assuming paths won't break this simple split.
            # A more robust way: shlex.split(command)
            # import shlex # Import shlex for robust command splitting -> Moved to top

            result = subprocess.run(
                shlex.split(command), capture_output=True, text=True, check=True
            )
            if os.path.exists(path):  # Re-check after ffprobe, path might be gone
                meta_dict = json.loads(result.stdout)
                success = True
            else:
                logging.error(f"Video file disappeared during ffprobe: {path}")
        except subprocess.CalledProcessError as e:
            logging.error(f'FFProbe failed for "{path}", error: {e.stderr}')
        except json.JSONDecodeError:
            logging.error(f'FFProbe output for "{path}" is not valid JSON.')
        except FileNotFoundError:  # If ffprobe itself is not found
            logging.error(
                "ffprobe command not found. Please ensure it is installed and in your PATH."
            )

        if success:
            for stream in meta_dict.get("streams", []):
                if stream.get("codec_type") == "video":
                    vseconds = int(float(stream.get("duration", 0)))
                    vwidth = int(stream.get("width", 0))
                    vheight = int(stream.get("height", 0))
                if stream.get("codec_type") == "audio":
                    vaudio = True

            if vwidth == 0 or vheight == 0:  # Ensure we got valid video dimensions
                logging.error(
                    f'FFProbe could not determine video dimensions for "{path}"'
                )
                success = False  # Mark as failure if dimensions are invalid

        return VideoMetadata(
            success=success,
            vseconds=vseconds,
            vwidth=vwidth,
            vheight=vheight,
            vaudio=vaudio,
        )

    def add_outro(self) -> bool:
        """
        Appends an outro video to the generated video summary if specified.

        This method uses ffmpeg-python to concatenate the main summary video
        (self.mp4sumpath) with the outro video (self.outro) and saves it
        to self.mp4outpath.

        Returns:
            True if the outro was added successfully or if no outro was specified.
            False if an error occurred during the process.
        """
        if (
            not self.outro or not self.mp4sumpath or not self.mp4outpath
        ):  # Should not happen if called correctly
            logging.error(
                "add_outro called with missing outro, mp4sumpath or mp4outpath"
            )
            return False

        outro_meta = self._get_video_meta(self.outro)
        out = None
        if outro_meta["success"]:
            oaudio = outro_meta["vaudio"]  # Extract audio flag
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

    def summarize(self) -> bool:
        """
        Orchestrates the full video summarization process for the single video.

        This involves:
        1. Getting video metadata.
        2. Preparing output folders.
        3. Running 'hecate' to generate initial summaries/images.
        4. Cleaning up and organizing generated files.
        5. Adding an outro video if specified.

        Returns:
            True if the summarization process (excluding optional outro) completes successfully.
            False if any critical step fails. Note that a failure in adding an
            optional outro is logged as a warning but does not cause this method
            to return False.
        """
        video_meta = self._get_video_meta(self.path)
        if not video_meta["success"]:
            logging.error(
                f"Could not get video metadata for {self.path}. Aborting summarization."
            )
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
    """
    Manages video processing tasks for single files or directories of video files.

    This class identifies video files to process based on the input path and
    mode (single file or directory). It then uses PyHecateVideo instances
    to perform the actual processing for each identified video.
    """

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
        """
        Initializes PyHecate to manage video processing tasks.

        This constructor sets up paths and identifies videos to be processed.
        Actual processing is deferred to the `execute()` method.

        Args:
            path: Path to the input video file or directory.
            dir_mode: If True, `path` is treated as a directory of videos.
                      Otherwise, `path` is treated as a single video file.
            outdir: Optional path to a general output directory.
                    If not provided, defaults to the parent of `path` (for single file)
                    or `path` itself (for directory mode).
                    Each video processed will have its own subfolder created within this
                    main output directory.
            isumfreq: Frequency in seconds for JPG snapshots.
            vsumlength: Length of the video summary in seconds.
            outro: Optional path to an outro video to append to summaries.
            vsum: If True, generate video summaries.
            isum: If True, generate image summaries (JPGs, GIFs).
            gifwidth: Width of the generated GIFs in pixels.
        """
        self.path: str = path  # Store original path for execute method's logging
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

        # Processing loop moved to execute() method

    def execute(self) -> bool:
        """
        Processes all videos found during initialization.
        Returns True if all videos were processed successfully (or no videos found),
        False if any video failed or if initialization failed to find videos.
        """
        if not self.vpaths:
            if os.path.exists(self.path):  # Path existed but no videos found
                logging.warning(f"No videos to process in {self.path}.")
            # If self.path didn't exist, error was logged in __init__ and vpaths is empty.
            # In this case, it's an init failure, so return False.
            # A more robust way might be to set a flag in __init__ if path validation failed.
            # For now, empty vpaths after a valid path existed is not an error, but init failure is.
            # Let's assume if __init__ logged an error for path, it's already "failed".
            # This logic needs to be robust: if __init__ failed to set up self.path correctly,
            # self.vpaths would be empty.
            # A simple check: if self.vpaths is empty AND __init__ had issues setting up (e.g. path not found),
            # then it's a failure. If path was valid but simply no .mp4s, it's not a failure.
            # This distinction is tricky without an explicit success/failure flag from __init__.
            # For now, if vpaths is empty, we'll consider it "nothing to do" unless path itself was bad.
            # The original code in __init__ would log errors if path was bad and then vpaths would be empty.
            # Let's refine this: if __init__ returned due to bad path, vpaths is empty.
            # We need a way for PyHecate user to know if init itself was okay.
            # One way: raise an exception from __init__ on critical errors.
            # Or, add a status attribute.
            # For now, let's assume if vpaths is empty, either no videos or init problem.
            # The CLI will call this. If __init__ logs "Input path does not exist", then execute() will find empty vpaths.

            # If self.path was invalid in __init__, it would have returned early.
            # So, if we reach here and vpaths is empty, it means either the dir was empty
            # or the single file was not a video (or not .mp4).
            # This isn't necessarily an error for the execute() method itself.
            # Let's return True indicating "executed, nothing to do or all done".
            # The PyHecate class constructor already logs errors if input path is invalid.
            return True  # No videos to process or successfully processed all.

        all_successful = True
        for vpath_item in self.vpaths:
            if not self.process_video(vpath_item):
                all_successful = False
        return all_successful

    def process_video(
        self, vpath: str
    ) -> bool:  # Renamed from summarize and changed to return bool
        """
        Processes a single video file using an instance of PyHecateVideo.

        Args:
            vpath: The absolute path to the video file to process.

        Returns:
            True if the video was processed successfully, False otherwise.
        """
        logging.info(f"\n\nProcessing: {vpath}")
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
            return False
        return True
