import subprocess
from unittest.mock import MagicMock, patch

import pytest
from _pytest.logging import LogCaptureFixture # Import for caplog type

from pyhecate import (
    PyHecateVideo,
)  # Assuming VideoMetadata might be needed for setup


# Fixture for a basic PyHecateVideo instance
@pytest.fixture
def pv_instance(tmp_path) -> PyHecateVideo: # Added return type hint
    """Provides a PyHecateVideo instance with minimal valid setup for run_hecate tests."""
    outdir = tmp_path / "hecate_output"
    outdir.mkdir()
    # Create a dummy video file that PyHecateVideo expects to exist
    video_file = tmp_path / "input.mp4"
    video_file.write_text("dummy video data")

    instance = PyHecateVideo(path=str(video_file), outdir=str(outdir))
    # Minimal metadata needed for hecate command construction in run_hecate
    instance.vwidth = 1280  # Example width
    instance.numsnaps = 10  # Example numsnaps
    instance.gifwidth = 360  # Example gifwidth
    instance.vsumlength = 16  # Example vsumlength
    # Enable features so that hecate command includes respective flags
    instance.vsum = True
    instance.isum = True
    return instance


@patch("subprocess.run")
def test_run_hecate_success(mock_subprocess_run, pv_instance) -> None:
    """Test PyHecateVideo.run_hecate success."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Hecate success"
    mock_result.stderr = ""
    mock_subprocess_run.return_value = mock_result

    assert pv_instance.run_hecate() is True
    mock_subprocess_run.assert_called_once()
    args, _ = mock_subprocess_run.call_args
    assert "hecate" in args[0][0]  # Check that 'hecate' is the command
    assert pv_instance.path in args[0]  # Check input video path
    assert pv_instance.outdir in args[0]  # Check output directory


@patch("subprocess.run")
def test_run_hecate_failure_calledprocesserror(
    mock_subprocess_run, pv_instance, caplog: LogCaptureFixture
) -> None:
    """Test PyHecateVideo.run_hecate failure due to CalledProcessError."""
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd="hecate", stderr="Hecate error"
    )

    assert pv_instance.run_hecate() is False
    mock_subprocess_run.assert_called_once()
    assert f"Hecate failed for {pv_instance.path}: Hecate error" in caplog.text


@patch("subprocess.run")
def test_run_hecate_failure_filenotfounderror(
    mock_subprocess_run, pv_instance, caplog: LogCaptureFixture
) -> None:
    """Test PyHecateVideo.run_hecate failure due to FileNotFoundError."""
    mock_subprocess_run.side_effect = FileNotFoundError("hecate command not found")

    assert pv_instance.run_hecate() is False
    mock_subprocess_run.assert_called_once()
    assert (
        "Hecate command not found. Please ensure it is installed and in your PATH."
        in caplog.text
    )
