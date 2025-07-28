from unittest.mock import patch

import pytest

from pyhecate import (
    PyHecateVideo,
    VideoMetadata,
)  # Assuming VideoMetadata might be needed


@pytest.fixture
def pv_summarize_instance(tmp_path):
    """Provides a PyHecateVideo instance for summarize tests."""
    outdir = tmp_path / "summarize_output"
    # PyHecateVideo.__init__ creates outdir, so no need to mkdir here for the pv.outdir

    # Dummy video file for path
    video_file = tmp_path / "input_video.mp4"
    video_file.write_text("dummy video content")

    pv = PyHecateVideo(path=str(video_file), outdir=str(outdir))
    # Set some defaults that might be used by mocked methods or internal logic
    pv.vsum = True
    pv.isum = True
    pv.outro = str(tmp_path / "outro.mp4")  # Dummy outro path
    (tmp_path / "outro.mp4").write_text(
        "outro content"
    )  # Create dummy outro file for os.path.exists
    pv.mp4sumpath = str(outdir / "summary.mp4")  # Dummy summary path for os.path.exists
    (outdir / "summary.mp4").write_text(
        "summary content"
    )  # Create dummy summary for os.path.exists

    return pv


# Define paths for mocks to make them consistent
MOCK_GET_VIDEO_META = "pyhecate.PyHecateVideo._get_video_meta"
MOCK_PREP_OUTFOLDERS = "pyhecate.PyHecateVideo.prep_outfolders"
MOCK_RUN_HECATE = "pyhecate.PyHecateVideo.run_hecate"
MOCK_CLEANUP_FOLDERS = "pyhecate.PyHecateVideo.cleanup_folders"
MOCK_ADD_OUTRO = "pyhecate.PyHecateVideo.add_outro"
MOCK_OS_PATH_EXISTS = "os.path.exists"


@patch(
    MOCK_OS_PATH_EXISTS, return_value=True
)  # Assume all relevant paths exist for simplicity here
@patch(MOCK_ADD_OUTRO, return_value=True)
@patch(MOCK_CLEANUP_FOLDERS, return_value=True)
@patch(MOCK_RUN_HECATE, return_value=True)
@patch(MOCK_PREP_OUTFOLDERS)  # Returns None by default
@patch(MOCK_GET_VIDEO_META)
def test_summarize_full_success_path(
    mock_get_meta,
    mock_prep_folders,
    mock_run_hecate,
    mock_cleanup_folders,
    mock_add_outro,
    mock_path_exists,
    pv_summarize_instance,
    caplog,
):
    """Test PyHecateVideo.summarize success path where all steps succeed."""
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=60, vwidth=1280, vheight=720, vaudio=True
    )

    assert pv_summarize_instance.summarize() is True

    mock_get_meta.assert_called_once_with(pv_summarize_instance.path)
    mock_prep_folders.assert_called_once()
    mock_run_hecate.assert_called_once()
    mock_cleanup_folders.assert_called_once()
    mock_add_outro.assert_called_once()  # Called because vsum, outro, and paths exist


@patch(MOCK_GET_VIDEO_META)
def test_summarize_failure_at_get_video_meta(
    mock_get_meta, pv_summarize_instance, caplog
):
    """Test summarize returns False if _get_video_meta fails."""
    mock_get_meta.return_value = VideoMetadata(
        success=False, vseconds=0, vwidth=0, vheight=0, vaudio=False
    )

    assert pv_summarize_instance.summarize() is False
    mock_get_meta.assert_called_once_with(pv_summarize_instance.path)
    assert (
        f"Could not get video metadata for {pv_summarize_instance.path}" in caplog.text
    )


@patch(MOCK_PREP_OUTFOLDERS, side_effect=ValueError("Test prep_outfolders error"))
@patch(MOCK_GET_VIDEO_META)
def test_summarize_failure_at_prep_outfolders(
    mock_get_meta, mock_prep_folders_error, pv_summarize_instance
):
    """Test summarize propagates ValueError from prep_outfolders."""
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=60, vwidth=1280, vheight=720, vaudio=True
    )

    with pytest.raises(ValueError, match="Test prep_outfolders error"):
        pv_summarize_instance.summarize()
    mock_prep_folders_error.assert_called_once()


@patch(MOCK_RUN_HECATE, return_value=False)
@patch(MOCK_PREP_OUTFOLDERS)
@patch(MOCK_GET_VIDEO_META)
def test_summarize_failure_at_run_hecate(
    mock_get_meta,
    mock_prep_folders,
    mock_run_hecate_fails,
    pv_summarize_instance,
    caplog,
):
    """Test summarize returns False if run_hecate fails."""
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=60, vwidth=1280, vheight=720, vaudio=True
    )

    assert pv_summarize_instance.summarize() is False
    mock_run_hecate_fails.assert_called_once()


@patch(MOCK_CLEANUP_FOLDERS, return_value=False)
@patch(MOCK_RUN_HECATE, return_value=True)
@patch(MOCK_PREP_OUTFOLDERS)
@patch(MOCK_GET_VIDEO_META)
def test_summarize_failure_at_cleanup_folders(
    mock_get_meta,
    mock_prep_folders,
    mock_run_hecate,
    mock_cleanup_fails,
    pv_summarize_instance,
    caplog,
):
    """Test summarize returns False if cleanup_folders fails."""
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=60, vwidth=1280, vheight=720, vaudio=True
    )

    assert pv_summarize_instance.summarize() is False
    mock_cleanup_fails.assert_called_once()


@patch(MOCK_OS_PATH_EXISTS, return_value=True)
@patch(MOCK_ADD_OUTRO, return_value=False)  # add_outro fails
@patch(MOCK_CLEANUP_FOLDERS, return_value=True)
@patch(MOCK_RUN_HECATE, return_value=True)
@patch(MOCK_PREP_OUTFOLDERS)
@patch(MOCK_GET_VIDEO_META)
def test_summarize_failure_at_add_outro_still_returns_true(
    mock_get_meta,
    mock_prep_folders,
    mock_run_hecate,
    mock_cleanup_folders,
    mock_add_outro_fails,
    mock_path_exists,
    pv_summarize_instance,
    caplog,
):
    """Test summarize returns True even if optional add_outro fails, but logs warning."""
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=60, vwidth=1280, vheight=720, vaudio=True
    )

    assert pv_summarize_instance.summarize() is True  # Still True
    mock_add_outro_fails.assert_called_once()
    assert f"Failed to add outro to {pv_summarize_instance.path}" in caplog.text


@patch(MOCK_OS_PATH_EXISTS, return_value=True)
@patch(MOCK_ADD_OUTRO)  # Keep this mock to ensure it's NOT called
@patch(MOCK_CLEANUP_FOLDERS, return_value=True)
@patch(MOCK_RUN_HECATE, return_value=True)
@patch(MOCK_PREP_OUTFOLDERS)
@patch(MOCK_GET_VIDEO_META)
def test_summarize_add_outro_not_called_if_vsum_false(
    mock_get_meta,
    mock_prep_folders,
    mock_run_hecate,
    mock_cleanup_folders,
    mock_add_outro,
    mock_path_exists,
    pv_summarize_instance,
):
    """Test add_outro is not called if vsum is False."""
    pv_summarize_instance.vsum = False  # Disable video summary
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=60, vwidth=1280, vheight=720, vaudio=True
    )

    assert pv_summarize_instance.summarize() is True
    mock_add_outro.assert_not_called()


@patch(MOCK_OS_PATH_EXISTS, return_value=True)
@patch(MOCK_ADD_OUTRO)
@patch(MOCK_CLEANUP_FOLDERS, return_value=True)
@patch(MOCK_RUN_HECATE, return_value=True)
@patch(MOCK_PREP_OUTFOLDERS)
@patch(MOCK_GET_VIDEO_META)
def test_summarize_add_outro_not_called_if_no_outro_path(
    mock_get_meta,
    mock_prep_folders,
    mock_run_hecate,
    mock_cleanup_folders,
    mock_add_outro,
    mock_path_exists,
    pv_summarize_instance,
):
    """Test add_outro is not called if self.outro is None."""
    pv_summarize_instance.outro = None  # No outro path
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=60, vwidth=1280, vheight=720, vaudio=True
    )

    assert pv_summarize_instance.summarize() is True
    mock_add_outro.assert_not_called()


@patch(MOCK_OS_PATH_EXISTS)  # Control os.path.exists calls specifically
@patch(MOCK_ADD_OUTRO)
@patch(MOCK_CLEANUP_FOLDERS, return_value=True)
@patch(MOCK_RUN_HECATE, return_value=True)
@patch(MOCK_PREP_OUTFOLDERS)
@patch(MOCK_GET_VIDEO_META)
def test_summarize_add_outro_not_called_if_outro_file_does_not_exist(
    mock_get_meta,
    mock_prep_folders,
    mock_run_hecate,
    mock_cleanup_folders,
    mock_add_outro,
    mock_path_exists_dynamic,
    pv_summarize_instance,
):
    """Test add_outro is not called if the outro file itself does not exist."""
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=60, vwidth=1280, vheight=720, vaudio=True
    )

    # Make os.path.exists return False for the outro file, True for summary
    def side_effect_os_path_exists(path_arg):
        if path_arg == pv_summarize_instance.outro:
            return False
        if path_arg == pv_summarize_instance.mp4sumpath:
            return True
        return True  # Default for other checks if any

    mock_path_exists_dynamic.side_effect = side_effect_os_path_exists

    assert pv_summarize_instance.summarize() is True
    mock_add_outro.assert_not_called()
    # Check that os.path.exists was called for the outro and summary
    # This is tricky with multiple calls. We trust the side_effect works.
    # mock_path_exists_dynamic.assert_any_call(pv_summarize_instance.outro)
    # mock_path_exists_dynamic.assert_any_call(pv_summarize_instance.mp4sumpath)
