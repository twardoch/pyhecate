# pyhecate: Automated Video Thumbnails, GIFs, and Summaries on macOS

**`pyhecate` is a Python command-line tool and library for macOS that automates the creation of insightful visual summaries from your video files. It generates still image thumbnails (JPGs), animated GIFs, and concise summary videos (MP4s), making it easy to preview, catalog, or share your video content.**

It acts as a powerful and user-friendly wrapper for the underlying [`hecate`](https://github.com/twardoch/hecate) command-line application, simplifying its usage and adding features like batch processing and custom video outros.

## Who is this for?

`pyhecate` is designed for anyone who works with video content on a Mac and needs a quick way to generate visual summaries:

*   **Content Creators:** Quickly create thumbnails or teaser GIFs for social media or websites.
*   **Video Editors:** Generate previews or contact sheets of video footage.
*   **Archivists & Librarians:** Efficiently catalog large video collections with visual metadata.
*   **Researchers:** Extract keyframes or summarized clips for analysis.
*   **Anyone with video files:** Get a quick overview of video content without scrubbing through entire files.

## Why is it useful?

*   **Saves Time:** Automates the otherwise tedious manual process of extracting frames and creating summaries.
*   **Multiple Output Formats:** Generates JPG snapshots, animated GIFs, and summary MP4 videos from a single command.
*   **Highly Customizable:**
    *   Control snapshot frequency for JPGs.
    *   Define the width of animated GIFs.
    *   Set the desired length for video summaries.
    *   Optionally skip image or video summary generation.
*   **Batch Processing:** Process a single video file or an entire folder of videos at once.
*   **Add Outros:** Automatically append a custom outro/ending video clip to your generated summaries.
*   **Organized Output:** Creates well-structured folders for each processed video, keeping generated files neatly organized.

## Installation

### Prerequisites

1.  **`hecate`**: `pyhecate` relies on the `hecate` command-line tool. You must install it first.
    *   Follow the installation instructions on the [official `hecate` GitHub page](https://github.com/twardoch/hecate/blob/master/README.md).

2.  **`ffmpeg`**: You also need `ffmpeg` and `ffprobe` installed and available in your system's PATH. `pyhecate` uses these for video metadata analysis and processing.
    *   The easiest way to install `ffmpeg` on macOS is typically via [Homebrew](https://brew.sh/):
        ```bash
        brew install ffmpeg
        ```
    *   Alternatively, download binaries from the [official FFmpeg website](https://ffmpeg.org/download.html).

### Installing `pyhecate`

Once the prerequisites are met, you can install `pyhecate`:

*   **Recommended (from PyPI):**
    ```bash
    pip install pyhecate
    ```

*   **Alternative (directly from GitHub for the latest version):**
    ```bash
    python3 -m pip install --user --upgrade git+https://github.com/twardoch/pyhecate/
    ```

## Usage

### Command-Line Interface (CLI)

Open your Terminal application and use the `pyhecate` command.

**Basic Structure:**

```bash
pyhecate [OPTIONS] <path_to_video_file_or_folder>
```

**Common Options:**

*   `path`: (Required) Path to the video file or a folder containing video files.
*   `-d`, `--dir`: Treat the `path` argument as a folder and process all `*.mp4` files within it.
*   `-o <output_folder>`, `--outdir <output_folder>`: Specify a parent folder where output subfolders (one for each video) will be created. Defaults to the input video's directory.
*   `-i <secs>`, `--image-every <secs>`: Set JPG snapshot frequency in seconds (default: 30).
*   `-g <px>`, `--gif-width <px>`: Set the width for animated GIFs in pixels (default: 360).
*   `-I`, `--skip-images`: Skip generating JPG and GIF images.
*   `-s <secs>`, `--video-length <secs>`: Set the video summary length in seconds (default: 16).
*   `-a <path_to_outro_video>`, `--outro <path_to_outro_video>`: Path to an MP4 video file to append as an outro to the summary video.
*   `-S`, `--skip-video-summary`: Skip making the video summary MP4 file.
*   `-v`: Verbose output (use `-vv` for debug-level verbosity).
*   `-h`, `--help`: Show the full help message with all options.

**Examples:**

1.  **Process a single video with default settings:**
    (Output will be in a folder named `myvideo_out` inside the same directory as `myvideo.mp4`)
    ```bash
    pyhecate /path/to/myvideo.mp4
    ```

2.  **Process all MP4 videos in a directory, saving results to a specific output location:**
    ```bash
    pyhecate -d /path/to/my_videos_folder -o /path/to/desired_output_location
    ```

3.  **Process a single video, create a 60-second summary, use 200px wide GIFs, and add an outro:**
    ```bash
    pyhecate /path/to/another_video.mp4 -s 60 -g 200 -a /path/to/my_outro.mp4
    ```

4.  **Process a video, but only generate the video summary (no JPGs or GIFs):**
    ```bash
    pyhecate /path/to/presentation.mp4 -I
    ```

### Programmatic Usage (Python Library)

You can also use `pyhecate` within your Python scripts for more complex workflows.

**Core Classes:**

*   `pyhecate.PyHecate`: Useful for processing based on file/folder paths, similar to CLI usage.
*   `pyhecate.PyHecateVideo`: Provides fine-grained control over the processing of a single video file.

**Examples:**

1.  **Process all videos in a directory using `PyHecate`:**
    ```python
    from pyhecate import PyHecate
    import logging

    # Configure logging to see progress (optional)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    processor = PyHecate(
        path="/path/to/your_video_collection", # Path to the directory
        dir=True,                             # Indicate it's a directory
        outdir="/path/to/programmatic_output", # Specify output base directory
        isumfreq=60,                          # Snapshot every 60 seconds
        vsumlength=30,                        # 30-second video summaries
        gifwidth=400                          # 400px wide GIFs
    )
    # Processing is triggered during instantiation when 'dir=True' or for single files.
    print("Processing complete. Check the output directory.")
    ```

2.  **Process a single video with detailed control using `PyHecateVideo`:**
    ```python
    from pyhecate import PyHecateVideo
    import logging
    import os

    # Configure logging (optional)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    video_file = "/path/to/source_video.mp4"
    base_output_dir = "/path/to/single_video_output"

    # PyHecateVideo expects the final output directory for *this specific video*
    video_name_without_ext = os.path.splitext(os.path.basename(video_file))[0]
    specific_video_outdir = os.path.join(base_output_dir, video_name_without_ext)

    if not os.path.exists(specific_video_outdir):
        os.makedirs(specific_video_outdir)

    video_processor = PyHecateVideo(
        path=video_file,
        outdir=specific_video_outdir, # Directory where this video's outputs (jpg, gif, mp4 subfolders) will be created
        isumfreq=10,                  # Snapshots every 10 seconds
        vsumlength=20,                # 20-second summary
        gifwidth=320,                 # 320px wide GIFs
        outro="/path/to/your_outro.mp4", # Optional: path to an outro video
        isum=True,                    # Generate images (JPGs, GIFs)
        vsum=True                     # Generate video summary
    )

    success = video_processor.summarize()

    if success:
        print(f"Successfully processed {video_file}")
        print(f"Outputs are in: {specific_video_outdir}")
    else:
        print(f"Failed to process {video_file}")
    ```

## Technical Details

### How the Code Works

`pyhecate` is structured around two main classes and leverages external command-line tools for its core functionality:

*   **`pyhecate.PyHecate` Class:**
    *   This class serves as the main entry point when using `pyhecate` as a library for processing multiple files or for simpler single-file processing.
    *   It handles the initial path inputs, determining if it's a single video file or a directory of videos.
    *   If a directory is provided, it scans for `*.mp4` files.
    *   For each video file identified, it constructs an appropriate output subdirectory path (e.g., `main_output_dir/video_filename_without_ext/`) and then instantiates `PyHecateVideo` to handle the actual processing for that video.
    *   It passes along configuration options (like image frequency, summary length, etc.) to each `PyHecateVideo` instance.

*   **`pyhecate.PyHecateVideo` Class:**
    *   This class is responsible for all processing operations for a *single* video file.
    *   **1. Metadata Extraction:**
        *   It begins by calling `ffprobe` (a tool distributed with `ffmpeg`) using `subprocess.run()`.
        *   This fetches crucial metadata from the video file, such as its duration, width, height, and whether it contains an audio stream. This information is used to configure subsequent processing steps (e.g., number of snapshots, video summary dimensions).
    *   **2. Output Preparation (`prep_outfolders` method):**
        *   Based on the video's metadata and user settings, it creates a structured set of subdirectories within the video's specific output folder (e.g., `.../video_name_out/`). These include:
            *   `jpg-<width>`: For still image snapshots.
            *   `gif-<width>`: For individual frame animated GIFs.
            *   `gifsum-<width>`: For summary animated GIFs.
            *   `mp4-<length>`: For the summary MP4 video.
        *   It also defines paths for temporary and final summary files.
    *   **3. `hecate` Execution (`run_hecate` method):**
        *   This is the core processing step. The method constructs a command-line call to the external `hecate` application.
        *   Arguments for `hecate` are dynamically built based on the `PyHecateVideo` instance's attributes (e.g., `self.vsum` to generate video summary, `self.isum` for images, `self.vsumlength`, `self.numsnaps`, `self.gifwidth`).
        *   `subprocess.run()` is used to execute the `hecate` command. `hecate` then performs the heavy lifting of analyzing the video and generating the raw output files (images, summary video) into the video's specific output folder (which acts as a temporary staging area for `hecate`).
    *   **4. File Organization & Cleanup (`cleanup_folders` method):**
        *   After `hecate` completes, its output files (JPGs, GIFs, temporary summary MP4) are located directly in the video's output folder.
        *   This method moves these files into their respective, neatly organized subdirectories (e.g., `jpg-1280/`, `gifsum-360/`) that were created in the `prep_outfolders` step.
    *   **5. Outro Addition (`add_outro` method):**
        *   If an outro video path (`self.outro`) is provided and a summary video was generated, this method uses the `ffmpeg-python` library.
        *   It takes the generated summary video and the specified outro video as inputs.
        *   It then uses `ffmpeg-python`'s capabilities to concatenate these two video streams (and their audio streams, if present and compatible) into a new MP4 file, which becomes the final summary video with the outro.
    *   **Orchestration (`summarize` method):**
        *   This public method in `PyHecateVideo` calls the above steps in sequence to fully process a single video.

**Key External Tools & Libraries:**

*   **[`hecate`](https://github.com/twardoch/hecate):** The core engine for analyzing video content and generating initial thumbnails, GIFs, and summary videos. `pyhecate` wraps `hecate` calls using `subprocess`.
*   **[`ffmpeg`](https://ffmpeg.org/) (and `ffprobe`):** Used for:
    *   `ffprobe`: Extracting video metadata (duration, dimensions, audio information) via `subprocess`.
    *   `ffmpeg` (via [`ffmpeg-python`](https://github.com/kkroening/ffmpeg-python) library): Concatenating the generated video summary with a custom outro video.
*   **[`Send2Trash`](https://github.com/hsoft/send2trash):** Used for moving files to the system's trash/recycle bin instead of permanently deleting them, which is a safer default.

### Coding Standards and Contributing

We welcome contributions to `pyhecate`! To ensure code quality and consistency, please follow these guidelines:

**Development Environment Setup:**

1.  **Prerequisites:**
    *   Python 3.8+
    *   Git
    *   The `hecate` command-line tool installed and in your PATH.
    *   `ffmpeg` and `ffprobe` installed and in your PATH.
2.  **Clone the Repository:**
    ```bash
    git clone https://github.com/twardoch/pyhecate.git
    cd pyhecate
    ```
3.  **Install in Editable Mode with Development Dependencies:**
    This will install `pyhecate` such that changes you make to the source code are immediately effective. The `[dev]` extra includes tools for linting, formatting, type checking, and testing.
    ```bash
    pip install -e .[dev]
    ```

**Code Style & Quality:**

*   **Formatting:** Code is formatted using **Ruff**. Before committing, please format your changes:
    ```bash
    ruff format .
    ```
*   **Linting:** Code is linted using **Ruff** to catch common issues and enforce style. Check your code with:
    ```bash
    ruff check .
    ```
    Configuration for Ruff can be found in `pyproject.toml`. We generally follow PEP 8 guidelines.
*   **Type Checking:** Static type checking is performed using **MyPy**. Ensure your code passes type checks:
    ```bash
    mypy .
    ```
    All new code should include type hints. MyPy configuration is also in `pyproject.toml`.

**Testing:**

*   Tests are written using the **pytest** framework and are located in the `tests/` directory.
*   Run all tests with:
    ```bash
    pytest
    ```
*   New features or bug fixes should ideally be accompanied by new tests to cover the changes.
*   Ensure all tests pass before submitting a pull request.

**Dependencies:**

*   Project dependencies are managed in `pyproject.toml` (using Hatch for the build system) and also listed in `setup.py` for broader compatibility.
*   Development dependencies are specified under `[project.optional-dependencies]` in `pyproject.toml`.

**Commit Messages:**

*   Please write clear and descriptive commit messages. While not strictly enforced, following a convention like [Conventional Commits](https://www.conventionalcommits.org/) is encouraged.
    *   Example: `feat: Add support for custom GIF frame rates`
    *   Example: `fix: Correctly handle videos with no audio stream during outro`
    *   Example: `docs: Update README with new installation instructions`

**Pull Requests:**

1.  Fork the repository on GitHub.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes, adhering to the coding standards above (format, lint, type check, test).
4.  Push your changes to your fork.
5.  Open a pull request against the `main` (or relevant development) branch of the `twardoch/pyhecate` repository.
6.  Clearly describe the changes you've made and why.

**Project-Specific Guidelines:**
*   Be mindful of any instructions or conventions documented in files like `AGENTS.md` or similar notes within the project if you encounter them, as these may contain specific guidance for working with certain parts of the codebase.

Thank you for contributing!
