import os
import json # Moved to top
import sys # Moved to top
import subprocess # Added for clarity for @patch
from unittest.mock import MagicMock, patch

import pytest

import pyhecate  # Import the main module
from pyhecate import (
    ISUMFREQ,
    PyHecateVideo,
    VideoMetadata,
)  # Import VideoMetadata
from pyhecate.__main__ import cli as get_cli_parser # Moved to top
from pyhecate.__main__ import main as pyhecate_main # For use in test_main_cli_runs_*


# Define a fixture for a temporary output directory
@pytest.fixture
def temp_outdir(tmp_path):
    d = tmp_path / "output"
    d.mkdir()
    return str(d)


# Test basic instantiation of PyHecateVideo
def test_pyhecate_video_instantiation(temp_outdir):
    """Test that PyHecateVideo can be instantiated."""
    video_path = "dummy.mp4"  # Dummy path, file doesn't need to exist for this test

    # Create a dummy video file for os.path.exists checks if needed by constructor logic
    with open(video_path, "w") as f:
        f.write("dummy video content")

    try:
        pv = PyHecateVideo(
            path=video_path,
            outdir=temp_outdir,
            isumfreq=10,
            vsumlength=5,
            outro="outro.mp4",
            vsum=True,
            isum=True,
            gifwidth=300,
        )
        assert pv.path == video_path
        assert pv.outdir == temp_outdir
        assert pv.isumfreq == 10
        assert pv.vsumlength == 5
        assert pv.outro == "outro.mp4"
        assert pv.vsum is True
        assert pv.isum is True
        assert pv.gifwidth == 300
        assert pv.base == os.path.basename(temp_outdir)
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


# Test _video_meta with mocked subprocess
@patch("subprocess.run")
def test_video_meta_success(mock_subprocess_run, temp_outdir):
    """Test the _video_meta method on a successful ffprobe call."""
    video_path = "test.mp4"
    # Create a dummy video file for os.path.exists checks
    with open(video_path, "w") as f:
        f.write("dummy video content")

    mock_ffprobe_output = {
        "streams": [
            {
                "codec_type": "video",
                "duration": "120.0",
                "width": 1920,
                "height": 1080,
            },
            {"codec_type": "audio"},
        ],
        "format": {"duration": "120.0"},
    }
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(mock_ffprobe_output)
    mock_result.stderr = ""
    mock_subprocess_run.return_value = mock_result

    pv = PyHecateVideo(path=video_path, outdir=temp_outdir)

    try:
        # Call the renamed method
        metadata = pv._get_video_meta(video_path)

        assert metadata["success"] is True
        assert metadata["vseconds"] == 120
        assert metadata["vwidth"] == 1920
        assert metadata["vheight"] == 1080
        assert metadata["vaudio"] is True
        mock_subprocess_run.assert_called_once()
        args, _ = mock_subprocess_run.call_args
        assert "ffprobe" in args[0]
        assert video_path in args[0]
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


@patch("subprocess.run")
def test_video_meta_ffprobe_failure(mock_subprocess_run, temp_outdir):
    """Test the _video_meta method when ffprobe fails."""
    video_path = "fail.mp4"
    with open(video_path, "w") as f:
        f.write("dummy video content")

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "ffprobe error"
    mock_subprocess_run.return_value = mock_result

    pv = PyHecateVideo(path=video_path, outdir=temp_outdir)
    try:
        metadata = pv._get_video_meta(video_path)  # Call the new method
        assert metadata["success"] is False
        assert metadata["vseconds"] == 0
        assert metadata["vwidth"] == 0
        assert metadata["vheight"] == 0
        assert metadata["vaudio"] is False
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)


# Test prep_outfolders
def test_prep_outfolders(temp_outdir):
    """Test that prep_outfolders creates the necessary directories."""
    video_path = "dummy_prep.mp4"
    pv = PyHecateVideo(path=video_path, outdir=temp_outdir)
    # Simulate metadata that would be set by _video_meta
    pv.vseconds = 600
    pv.vwidth = 1280
    pv.isumfreq = 30  # ensure numsnaps is reasonable
    pv.isum = True
    pv.vsum = True

    pv.prep_outfolders()

    assert os.path.exists(pv.jpgdir)
    assert os.path.exists(pv.gifdir)
    assert os.path.exists(pv.gifsumdir)
    assert os.path.exists(pv.mp4dir)
    assert pv.numsnaps == max(600 // 30, 10)
    assert pv.mp4tmppath is not None
    assert pv.mp4sumpath is not None
    assert pv.mp4outpath is not None


# Minimal test for PyHecate instantiation (main class)
@patch("pyhecate.PyHecateVideo._get_video_meta")  # Updated mock path
def test_pyhecate_instantiation(mock_get_video_meta, tmp_path):  # Renamed mock argument
    """Test basic instantiation of the main PyHecate class."""
    # Mock _get_video_meta to prevent actual ffprobe calls and return benign values
    mock_get_video_meta.return_value = VideoMetadata(  # Use TypedDict for return value
        success=True, vseconds=60, vwidth=1280, vheight=720, vaudio=False
    )

    # PyHecate's __init__ no longer processes videos directly.
    # This test remains valid for checking instantiation logic (path handling, outdir).
    # The mock on _get_video_meta is for PyHecateVideo, which would be called if
    # PyHecate.execute() was run and PyHecate.process_video() was called.
    # For purely __init__ testing of PyHecate, this mock isn't strictly necessary
    # unless PyHecate.__init__ itself tried to create a PyHecateVideo and call summarize.
    # Since PyHecate.__init__ only sets up paths, the mock is less critical here but harmless.

    # For a simple instantiation test, provide a non-existent path
    # or a path that results in no videos if dir_mode=True
    dummy_file_path = tmp_path / "non_existent_video.mp4"

    # This will log an error but shouldn't crash if path doesn't exist
    ph = pyhecate.PyHecate(path=str(dummy_file_path))
    assert isinstance(ph, pyhecate.PyHecate)
    assert not ph.vpaths  # No video paths should be found
    # self.outdir might not be set if path doesn't exist and __init__ returns early

    dummy_dir_path = tmp_path / "empty_video_dir"
    dummy_dir_path.mkdir()
    ph_dir = pyhecate.PyHecate(path=str(dummy_dir_path), dir_mode=True)
    assert isinstance(ph_dir, pyhecate.PyHecate)
    assert not ph_dir.vpaths  # No videos in the directory
    # In dir_mode with existing dir, outdir should default to the input path if not specified
    assert hasattr(ph_dir, "outdir") and ph_dir.outdir == str(dummy_dir_path)

    # Test with a custom output directory
    custom_outdir_path = tmp_path / "custom_out"
    # Use a dummy file that exists for this part of the test to ensure outdir is processed
    dummy_existing_file_for_outdir_test = tmp_path / "exists.mp4"
    dummy_existing_file_for_outdir_test.write_text("content")

    ph_custom_out = pyhecate.PyHecate(
        path=str(dummy_existing_file_for_outdir_test), outdir=str(custom_outdir_path)
    )
    assert hasattr(ph_custom_out, "outdir") and ph_custom_out.outdir == str(
        custom_outdir_path
    )
    assert os.path.exists(custom_outdir_path)  # outdir should be created


# It's good practice to also have a test for the CLI.
# This is more involved as it requires mocking subprocess calls for hecate and ffmpeg.
# For now, we'll add a placeholder or a very simple CLI test.

# from pyhecate.__main__ import cli as get_cli_parser # Moved to top


def test_cli_version():
    """Test that the CLI parser has a version action."""
    parser = get_cli_parser()
    with pytest.raises(SystemExit) as e:
        parser.parse_args(["--version"])
    assert e.value.code == 0  # Successful exit for --version


@patch("pyhecate.PyHecate")  # Patch the class
def test_main_cli_runs_success(MockPyHecate, tmp_path, caplog):  # Added caplog
    """Test that the main CLI function runs and exits successfully."""
    # from pyhecate.__main__ import main as pyhecate_main # Moved to top

    # Configure the mock instance that PyHecate() will return
    mock_processor_instance = MagicMock()
    mock_processor_instance.execute.return_value = True  # Simulate successful execution
    MockPyHecate.return_value = mock_processor_instance

    dummy_video = tmp_path / "video.mp4"
    dummy_video.write_text("content")

    with patch.object(sys, "argv", ["pyhecate", str(dummy_video)]):
        with pytest.raises(SystemExit) as e:
            pyhecate_main()
        assert e.value.code == 0  # Successful exit

    # Check that PyHecate was instantiated with correct args
    MockPyHecate.assert_called_once()
    _, kwargs = MockPyHecate.call_args
    assert kwargs["path"] == str(dummy_video)
    assert kwargs["dir_mode"] is False
    assert kwargs["isumfreq"] == ISUMFREQ
    # Check that execute was called on the instance
    mock_processor_instance.execute.assert_called_once()


@patch("pyhecate.PyHecate")  # Patch the class
def test_main_cli_runs_failure_on_execute(MockPyHecate, tmp_path, caplog):
    """Test that the main CLI function exits with error if execute() fails."""
    # from pyhecate.__main__ import main as pyhecate_main # Moved to top

    mock_processor_instance = MagicMock()
    mock_processor_instance.execute.return_value = False  # Simulate failed execution
    MockPyHecate.return_value = mock_processor_instance

    dummy_video = tmp_path / "video.mp4"
    dummy_video.write_text("content")

    with patch.object(sys, "argv", ["pyhecate", str(dummy_video)]):
        with pytest.raises(SystemExit) as e:
            pyhecate_main()
        assert e.value.code == 1  # Error exit

    mock_processor_instance.execute.assert_called_once()


@patch("pyhecate.PyHecate")  # Patch the class
def test_main_cli_runs_failure_on_exception(MockPyHecate, tmp_path, caplog):
    """Test that the main CLI function exits with error if PyHecate raises an exception."""
    # from pyhecate.__main__ import main as pyhecate_main # Moved to top

    MockPyHecate.side_effect = Exception(
        "Test init error"
    )  # Simulate error during instantiation

    dummy_video = tmp_path / "video.mp4"
    dummy_video.write_text("content")

    with patch.object(sys, "argv", ["pyhecate", str(dummy_video)]):
        with pytest.raises(SystemExit) as e:
            pyhecate_main()
        assert e.value.code == 1  # Error exit


# Need to import json for the mock_ffprobe_output
# import json # Moved to top

# Need to import sys for patching sys.argv
# import sys # Moved to top
