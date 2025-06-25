# TODO List for PyHecate Project Enhancement

## Initial Setup & Analysis
- [x] Verify `PLAN.md` accurately reflects initial strategy. (Covered by plan creation)
- [x] Populate `CHANGELOG.md` with its creation entry. (Done)

## Build System & Packaging (`pyproject.toml`)
- [x] Determine if `setup.py` is necessary given `hatchling` and `pyproject.toml`. (Removed `setup.py`)
- [x] Remove `requirements.txt` as dependencies are in `pyproject.toml`. (Done)
- [x] Verify `hatch-vcs` is correctly configured for versioning. (Confirmed `__version__` is not in `__init__.py`, `hatch-vcs` will use tags)
- [x] Review dependencies in `pyproject.toml` for correctness and currency. (Appear correct and current)
- [x] Ensure `project.scripts` and `project.urls` are accurate. (Appear accurate)
- [x] Add `keywords` to `pyproject.toml`. (Done)
- [ ] Check `tool.hatch.build.targets` for optimal configuration. (Seems okay for now, `include = ["/pyhecate", "/tests"]` is good)

## Core Logic (`pyhecate/__init__.py`)
- [x] Refactor `PyHecateVideo._video_meta()` (now `_get_video_meta`):
    - [x] Improve error handling for `subprocess.run` (used `shlex.split`, added `FileNotFoundError` for ffprobe).
    - [x] Clarify return values using `VideoMetadata` TypedDict. (Done)
- [ ] Refactor `PyHecateVideo.add_outro()`:
    - [ ] Simplify `ffmpeg-python` chain if possible. (Current chain is standard for concat)
    - [ ] Enhance error reporting for `ffmpeg.Error` and other exceptions. (Existing logging is reasonable)
- [ ] Refactor `PyHecateVideo.run_hecate()`:
    - [x] Improve error handling for `subprocess.run`. (Catches `FileNotFoundError` for hecate)
- [ ] Refactor `PyHecateVideo.prep_outfolders()`:
    - [ ] Ensure robustness in path creation and handling. (Seems okay, creates dirs)
- [ ] Refactor `PyHecateVideo.cleanup_folders()`:
    - [ ] Improve error handling for file operations. (Currently relies on `shutil` exceptions)
- [ ] Review `PyHecateVideo.summarize()` for overall flow and error propagation. (Reviewed, seems logical)
- [x] Refactor `PyHecate.__init__()`:
    - [x] Processing loop moved to `execute()` method. (Done)
    - [ ] Clarify output directory logic (`self.outdir`). (Logic reviewed, seems okay)
    - [ ] Improve handling of non-existent paths or empty directories. (Handled, logs errors)
- [x] `PyHecate.process_video()` now returns bool.
- [x] Add comprehensive docstrings to `pyhecate/__init__.py` classes and methods. (Done)
- [ ] Add more detailed logging throughout the core logic. (Current logging is decent, can be enhanced iteratively)
- [ ] Evaluate use of `send2trash` for consistency. (Used for temp files and failed outro, seems appropriate)
- [ ] Ensure all file operations are robust (e.g., handle cases where files might be unexpectedly missing). (Generally okay, some `shutil` ops could be wrapped if needed)
- [ ] Review usage of `Any` type hints. (Reviewed, deemed acceptable for ffprobe output)


## CLI (`pyhecate/__main__.py`)
- [x] Review argument parsing for clarity and completeness. (Reviewed, seems clear)
- [x] Ensure CLI arguments map correctly to `PyHecate` options. (Reviewed, mapping is correct)
- [x] Verify logging levels are set as expected based on verbosity flags. (Reviewed, current INFO default is clear, though could be changed if desired)
- [x] Improve error reporting for CLI-level issues. (Main execution block now catches exceptions from PyHecate and sets exit code)
- [x] Update `main()` to call `PyHecate().execute()` and handle exit codes. (Done)
- [x] Add docstrings to `cli()` and `main()`. (Done)
- [x] Remove unused `*args, **kwargs` from `main()`. (Done)

## Testing (various `tests/test_*.py` files)
- [x] Update existing tests in `tests/test_pyhecate_video.py` for refactoring (Done: `_get_video_meta`, CLI tests for `execute()`).
- [x] Increase test coverage for `PyHecateVideo` methods:
    - [x] `add_outro` (various scenarios). (Covered in `test_pyhecate_video_add_outro.py`)
    - [x] `run_hecate` (success, failure, not found). (Covered in `test_pyhecate_video_run_hecate.py`)
    - [x] `cleanup_folders` (various scenarios). (Covered in `test_pyhecate_video_cleanup_folders.py`)
    - [x] `summarize` (orchestration, error propagation). (Covered in `test_pyhecate_video_summarize.py`)
- [x] Increase test coverage for `PyHecate` class:
    - [x] `__init__` (path handling, outdir logic, file discovery). (Covered in `test_pyhecate_video.py` and `test_pyhecate_class.py`)
    - [x] `execute()` (no videos, single/multiple videos, success/failure). (Covered in `test_pyhecate_class.py`)
    - [x] `process_video()` (interaction with `PyHecateVideo`). (Covered in `test_pyhecate_class.py`)
- [x] Tests for CLI main execution flow and exit codes. (Covered by `test_main_cli_runs_*` in `test_pyhecate_video.py`)
- [ ] Granular tests for CLI argument parsing mapping to `PyHecate` options if further detail needed. (Current coverage is decent).
- [ ] Ensure mocks are used effectively. (Ongoing, seems reasonable).
- [ ] Consider property-based testing. (Future enhancement).

## Documentation & General
- [ ] Update `README.md` with any changes to CLI or functionality.
- [ ] Add/improve docstrings for all public modules, classes, and functions.
- [ ] Ensure type hinting is comprehensive and correct. Run `mypy`.
- [ ] Run `ruff` for linting and formatting, address all issues.
- [ ] Standardize error messages and logging formats.
- [ ] Consider adding a `.editorconfig` file for consistent coding styles.

## Long-term / Nice-to-haves
- [ ] Explore replacing direct `hecate` subprocess call with a Python API if one exists or could be contributed to the `hecate` project.
- [ ] Investigate cross-platform compatibility beyond macOS if desired.
- [ ] Performance profiling and optimization for large videos or batches.
- [ ] More sophisticated progress reporting for long operations.
