import os
from unittest.mock import MagicMock, call, patch

import pytest

import pyhecate  # Actual PyHecate class
from pyhecate import PyHecateVideo  # To mock its constructor or methods


# Minimal fixture for PyHecate instance, primarily for execute() tests
# __init__ tests are somewhat covered in test_pyhecate_video.py, but can be expanded here.
@pytest.fixture
def ph_instance(tmp_path):
    """Provides a basic PyHecate instance.
    Input path is a directory that will be created.
    """
    input_dir = tmp_path / "input_videos"
    input_dir.mkdir()
    # PyHecate.__init__ sets self.path to the input path
    ph = pyhecate.PyHecate(path=str(input_dir), dir_mode=True)
    return ph


# --- Tests for PyHecate.execute() ---


def test_execute_no_videos_found(ph_instance, caplog):
    """Test PyHecate.execute when self.vpaths is empty (e.g., empty input dir)."""
    ph_instance.vpaths = []  # Explicitly set to empty
    # ph_instance.path is already set by fixture to an existing empty dir

    assert ph_instance.execute() is True
    assert f"No videos to process in {ph_instance.path}" in caplog.text


@patch.object(pyhecate.PyHecate, "process_video")
def test_execute_one_video_success(mock_process_video, ph_instance, tmp_path):
    """Test PyHecate.execute with one video, processing succeeds."""
    video_path = str(tmp_path / "video1.mp4")
    ph_instance.vpaths = [video_path]
    mock_process_video.return_value = True

    assert ph_instance.execute() is True
    mock_process_video.assert_called_once_with(video_path)


@patch.object(pyhecate.PyHecate, "process_video")
def test_execute_one_video_failure(mock_process_video, ph_instance, tmp_path):
    """Test PyHecate.execute with one video, processing fails."""
    video_path = str(tmp_path / "video1.mp4")
    ph_instance.vpaths = [video_path]
    mock_process_video.return_value = False

    assert ph_instance.execute() is False
    mock_process_video.assert_called_once_with(video_path)


@patch.object(pyhecate.PyHecate, "process_video")
def test_execute_multiple_videos_all_success(mock_process_video, ph_instance, tmp_path):
    """Test PyHecate.execute with multiple videos, all succeed."""
    video_paths = [str(tmp_path / "v1.mp4"), str(tmp_path / "v2.mp4")]
    ph_instance.vpaths = video_paths
    mock_process_video.return_value = True  # All calls succeed

    assert ph_instance.execute() is True
    assert mock_process_video.call_count == 2
    mock_process_video.assert_has_calls([call(video_paths[0]), call(video_paths[1])])


@patch.object(pyhecate.PyHecate, "process_video")
def test_execute_multiple_videos_one_fails(mock_process_video, ph_instance, tmp_path):
    """Test PyHecate.execute with multiple videos, one fails."""
    video_paths = [
        str(tmp_path / "v1.mp4"),
        str(tmp_path / "v2.mp4"),
        str(tmp_path / "v3.mp4"),
    ]
    ph_instance.vpaths = video_paths
    # First succeeds, second fails, third (though not called if logic is strict) would succeed
    mock_process_video.side_effect = [True, False, True]

    assert ph_instance.execute() is False  # Overall result is False
    # Check calls up to the failure
    assert mock_process_video.call_count == 2  # Called for v1 and v2
    mock_process_video.assert_has_calls([call(video_paths[0]), call(video_paths[1])])


# --- Tests for PyHecate.process_video() ---


@patch("pyhecate.PyHecateVideo")  # Patch the class PyHecateVideo
def test_process_video_success(MockPyHecateVideo, ph_instance, tmp_path, caplog):
    """Test PyHecate.process_video successfully processes a video."""
    video_path = str(tmp_path / "input_dir" / "test_vid.mp4")
    # Ensure parent dir of video_path exists if PyHecateVideo needs it for outdir logic
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    (tmp_path / "input_dir" / "test_vid.mp4").write_text("content")

    # Configure the mock instance that PyHecateVideo() will return
    mock_pv_instance = MagicMock(spec=PyHecateVideo)
    mock_pv_instance.summarize.return_value = True  # Simulate successful summarization
    MockPyHecateVideo.return_value = mock_pv_instance

    # ph_instance.outdir is tmp_path / "input_videos" from fixture
    # voutdir should be tmp_path / "input_videos" / "test_vid"
    expected_voutdir = os.path.join(ph_instance.outdir, "test_vid")

    assert ph_instance.process_video(video_path) is True

    MockPyHecateVideo.assert_called_once_with(
        path=video_path,
        outdir=expected_voutdir,  # Key check: correct output dir for the video
        isumfreq=ph_instance.isumfreq,
        vsumlength=ph_instance.vsumlength,
        outro=ph_instance.outro,
        vsum=ph_instance.vsum,
        isum=ph_instance.isum,
        gifwidth=ph_instance.gifwidth,
    )
    mock_pv_instance.summarize.assert_called_once()
    assert f"Processing: {video_path}" in caplog.text


@patch("pyhecate.PyHecateVideo")
def test_process_video_failure(MockPyHecateVideo, ph_instance, tmp_path, caplog):
    """Test PyHecate.process_video when PyHecateVideo.summarize fails."""
    video_path = str(tmp_path / "input_dir" / "fail_vid.mp4")
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    (tmp_path / "input_dir" / "fail_vid.mp4").write_text("content")

    mock_pv_instance = MagicMock(spec=PyHecateVideo)
    mock_pv_instance.summarize.return_value = False  # Simulate failed summarization
    MockPyHecateVideo.return_value = mock_pv_instance

    expected_voutdir = os.path.join(ph_instance.outdir, "fail_vid")

    assert ph_instance.process_video(video_path) is False

    MockPyHecateVideo.assert_called_once_with(
        path=video_path,
        outdir=expected_voutdir,
        isumfreq=ph_instance.isumfreq,  # Check other params pass through
        vsumlength=ph_instance.vsumlength,
        outro=ph_instance.outro,
        vsum=ph_instance.vsum,
        isum=ph_instance.isum,
        gifwidth=ph_instance.gifwidth,
    )
    mock_pv_instance.summarize.assert_called_once()
    assert f"Processing failed for: {video_path}" in caplog.text


# Further tests for PyHecate.__init__ could be added here if more granularity is needed
# than what's in test_pyhecate_video.py's test_pyhecate_instantiation.
# For example, testing different outdir logic more explicitly.


@pytest.mark.parametrize(
    "dir_mode, expected_outdir_segment",
    [
        (False, "single_file_parent"),  # Expects outdir to be parent of file_path
        (True, "input_dir_itself"),  # Expects outdir to be input_dir
    ],
)
def test_pyhecate_init_outdir_logic(tmp_path, dir_mode, expected_outdir_segment):
    """Test PyHecate.__init__ outdir determination when outdir is not specified."""
    if dir_mode:  # Input is a directory
        input_path_str = str(tmp_path / "input_dir_itself")
        os.makedirs(input_path_str, exist_ok=True)
        # Expected outdir is the input_path_str itself
        expected_outdir_abs = os.path.abspath(input_path_str)
    else:  # Input is a file
        parent_dir = tmp_path / "single_file_parent"
        parent_dir.mkdir()
        input_path_str = str(parent_dir / "testfile.mp4")
        with open(input_path_str, "w") as f:
            f.write("dummy")
        # Expected outdir is the parent directory
        expected_outdir_abs = os.path.abspath(str(parent_dir))

    ph = pyhecate.PyHecate(path=input_path_str, dir_mode=dir_mode, outdir=None)
    assert ph.outdir == expected_outdir_abs


def test_pyhecate_init_custom_outdir(tmp_path):
    """Test PyHecate.__init__ with a custom outdir specified."""
    input_file = tmp_path / "video.mp4"
    input_file.write_text("content")
    custom_out = tmp_path / "my_custom_outputs"
    # custom_out does not need to exist beforehand, __init__ creates it.

    ph = pyhecate.PyHecate(path=str(input_file), dir_mode=False, outdir=str(custom_out))
    assert ph.outdir == os.path.abspath(str(custom_out))
    assert os.path.exists(ph.outdir)  # Check it was created


def test_pyhecate_init_finds_mp4_files_in_dir_mode(tmp_path):
    """Test PyHecate.__init__ correctly finds .mp4 files in directory mode."""
    input_dir = tmp_path / "video_folder"
    input_dir.mkdir()
    (input_dir / "vid1.mp4").write_text("v1")
    (input_dir / "vid2.MP4").write_text("v2")  # Check case insensitivity of .endswith
    (input_dir / "image.jpg").write_text("img")
    (input_dir / "subfolder").mkdir()
    (input_dir / "subfolder" / "vid3.mp4").write_text(
        "v3_sub"
    )  # Should not be found (not recursive)

    ph = pyhecate.PyHecate(path=str(input_dir), dir_mode=True)

    assert len(ph.vpaths) == 2
    # Paths are sorted
    expected_vpaths = sorted(
        [
            os.path.abspath(str(input_dir / "vid1.mp4")),
            os.path.abspath(str(input_dir / "vid2.MP4")),
        ]
    )
    assert ph.vpaths == expected_vpaths
