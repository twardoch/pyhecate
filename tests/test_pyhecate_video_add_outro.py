from unittest.mock import MagicMock, PropertyMock, patch

import ffmpeg  # type: ignore
import pytest
from _pytest.logging import LogCaptureFixture # Import for caplog type

from pyhecate import PyHecateVideo, VideoMetadata


# Fixture for PyHecateVideo instance tailored for add_outro tests
@pytest.fixture
def pv_add_outro_instance(tmp_path) -> PyHecateVideo:
    outdir = tmp_path / "outro_tests"
    outdir.mkdir()

    video_file = tmp_path / "main_sum.mp4"  # Represents the existing summary
    video_file.write_text("main summary data")

    outro_file = tmp_path / "outro.mp4"
    outro_file.write_text("outro video data")

    # Create necessary paths that add_outro expects
    mp4_dir = outdir / "mp4-16"  # Example, matching default vsumlength
    mp4_dir.mkdir()

    pv = PyHecateVideo(
        path="dummy_input.mp4", outdir=str(outdir)
    )  # Main input path not directly used by add_outro
    pv.mp4sumpath = str(video_file)
    pv.mp4outpath = str(mp4_dir / "final_sum_with_outro.mp4")
    pv.outro = str(outro_file)

    # Simulate metadata for the main video (self.vaudio)
    pv.vaudio = True  # Assume main summary has audio for some tests
    return pv


# Mock for ffmpeg.input() and its chained calls
def mock_ffmpeg_input_chain(has_audio=True):
    mock_input = MagicMock(spec=ffmpeg.nodes.InputStream)
    mock_input.video = PropertyMock(spec=ffmpeg.nodes.VideoStream)
    if has_audio:
        mock_input.audio = PropertyMock(spec=ffmpeg.nodes.AudioStream)
    else:  # If no audio, accessing .audio might raise or be None. Mock as if it's not there or not used.
        mock_input.audio = None
    return mock_input


@patch("ffmpeg.output")
@patch("ffmpeg.concat")
@patch("ffmpeg.input")
@patch.object(PyHecateVideo, "_get_video_meta")
def test_add_outro_success_with_audio(
    mock_get_meta,
    mock_ffmpeg_input,
    mock_ffmpeg_concat,
    mock_ffmpeg_output,
    pv_add_outro_instance,
    caplog: LogCaptureFixture,
) -> None:
    """Test add_outro success when both main and outro have audio."""
    pv_add_outro_instance.vaudio = True  # Main summary has audio
    # Mock metadata for outro video (has audio)
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=10, vwidth=1280, vheight=720, vaudio=True
    )

    # Mock ffmpeg.input().video, ffmpeg.input().audio
    mock_in1 = mock_ffmpeg_input_chain(has_audio=True)
    mock_in2 = mock_ffmpeg_input_chain(has_audio=True)
    mock_ffmpeg_input.side_effect = [mock_in1, mock_in2]

    # Mock ffmpeg.concat().node
    mock_concat_node = (MagicMock(), MagicMock())  # (video_stream, audio_stream)
    mock_ffmpeg_concat.return_value.node = mock_concat_node

    # Mock ffmpeg.output().run_async()
    mock_output_run = MagicMock()
    mock_output_run.communicate.return_value = (b"stdout", b"stderr")  # stdout, stderr
    type(mock_output_run).returncode = PropertyMock(return_value=0)  # Success
    mock_ffmpeg_output.return_value.run_async.return_value = mock_output_run

    assert pv_add_outro_instance.add_outro() is True
    mock_get_meta.assert_called_once_with(pv_add_outro_instance.outro)
    assert mock_ffmpeg_input.call_count == 2
    mock_ffmpeg_concat.assert_called_once()  # With v=1, a=1
    # Check that concat was called with audio (a=1)
    _, concat_kwargs = mock_ffmpeg_concat.call_args
    assert concat_kwargs.get("a") == 1
    mock_ffmpeg_output.assert_called_once_with(
        mock_concat_node[0], mock_concat_node[1], pv_add_outro_instance.mp4outpath
    )
    mock_output_run.communicate.assert_called_once()


@patch("ffmpeg.output")
@patch("ffmpeg.concat")
@patch("ffmpeg.input")
@patch.object(PyHecateVideo, "_get_video_meta")
def test_add_outro_success_video_only(
    mock_get_meta,
    mock_ffmpeg_input,
    mock_ffmpeg_concat,
    mock_ffmpeg_output,
    pv_add_outro_instance,
    caplog: LogCaptureFixture,
) -> None:
    """Test add_outro success with video only (no audio in main or outro)."""
    pv_add_outro_instance.vaudio = False  # Main summary no audio
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=10, vwidth=1280, vheight=720, vaudio=False
    )  # Outro no audio

    mock_in1 = mock_ffmpeg_input_chain(has_audio=False)
    mock_in2 = mock_ffmpeg_input_chain(has_audio=False)
    mock_ffmpeg_input.side_effect = [mock_in1, mock_in2]

    mock_concat_node = (MagicMock(),)  # Only video stream
    mock_ffmpeg_concat.return_value.node = mock_concat_node

    mock_output_run = MagicMock()
    mock_output_run.communicate.return_value = (b"", b"")
    type(mock_output_run).returncode = PropertyMock(return_value=0)
    mock_ffmpeg_output.return_value.run_async.return_value = mock_output_run

    assert pv_add_outro_instance.add_outro() is True
    # Check that concat was called without audio (default or v=1 explicitly, a not specified or a=0)
    _, concat_kwargs = mock_ffmpeg_concat.call_args
    assert (
        "a" not in concat_kwargs or concat_kwargs.get("a") == 0
    )  # Or check that it's called with (v1,v2, v=1)
    mock_ffmpeg_output.assert_called_once_with(
        mock_concat_node[0], pv_add_outro_instance.mp4outpath
    )


def test_add_outro_missing_params(
    pv_add_outro_instance, caplog: LogCaptureFixture
) -> None:
    """Test add_outro when essential parameters like self.outro are missing."""
    pv_add_outro_instance.outro = None
    assert pv_add_outro_instance.add_outro() is False
    assert "add_outro called with missing outro" in caplog.text


@patch.object(PyHecateVideo, "_get_video_meta")
def test_add_outro_metadata_fetch_fails(
    mock_get_meta, pv_add_outro_instance, caplog: LogCaptureFixture
) -> None:
    """Test add_outro when fetching outro metadata fails."""
    mock_get_meta.return_value = VideoMetadata(
        success=False, vseconds=0, vwidth=0, vheight=0, vaudio=False
    )

    assert pv_add_outro_instance.add_outro() is False
    assert f"Could not process outro video {pv_add_outro_instance.outro}" in caplog.text
    mock_get_meta.assert_called_once_with(pv_add_outro_instance.outro)


@patch(
    "ffmpeg.input",
    side_effect=ffmpeg.Error("ffmpeg_input_error", b"", b"ffmpeg input error details"),
)
@patch.object(PyHecateVideo, "_get_video_meta")
def test_add_outro_ffmpeg_setup_error(
    mock_get_meta, mock_ffmpeg_input_error, pv_add_outro_instance, caplog: LogCaptureFixture
) -> None:
    """Test add_outro when ffmpeg.input() or .concat() raises ffmpeg.Error."""
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=10, vwidth=1280, vheight=720, vaudio=True
    )

    assert pv_add_outro_instance.add_outro() is False
    assert (
        "ffmpeg error during input/concat setup for outro: ffmpeg input error details"
        in caplog.text
    )
    # Ensure send2trash was called if mp4outpath exists (it won't in this mocked setup unless we create it)
    # To test send2trash, we'd need to mock os.path.exists and send2trash itself.


@patch("ffmpeg.output")
@patch("ffmpeg.concat")  # Mock concat as it's called before output
@patch("ffmpeg.input")
@patch.object(PyHecateVideo, "_get_video_meta")
def test_add_outro_ffmpeg_execution_failure(
    mock_get_meta,
    mock_ffmpeg_input,
    mock_ffmpeg_concat,
    mock_ffmpeg_output,
    pv_add_outro_instance,
    caplog: LogCaptureFixture,
) -> None:
    """Test add_outro when ffmpeg execution (run_async) fails."""
    pv_add_outro_instance.vaudio = True
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=10, vwidth=1280, vheight=720, vaudio=True
    )

    mock_in1 = mock_ffmpeg_input_chain(has_audio=True)
    mock_in2 = mock_ffmpeg_input_chain(has_audio=True)
    mock_ffmpeg_input.side_effect = [mock_in1, mock_in2]
    mock_ffmpeg_concat.return_value.node = (MagicMock(), MagicMock())

    mock_output_run = MagicMock()
    mock_output_run.communicate.return_value = (
        b"",
        b"ffmpeg execution error",
    )  # stderr message
    type(mock_output_run).returncode = PropertyMock(
        return_value=1
    )  # Non-zero return code
    mock_ffmpeg_output.return_value.run_async.return_value = mock_output_run

    assert pv_add_outro_instance.add_outro() is False
    assert "ffmpeg error when adding outro: ffmpeg execution error" in caplog.text


@patch("ffmpeg.output", side_effect=Exception("Broad run_async exception"))
@patch("ffmpeg.concat")
@patch("ffmpeg.input")
@patch.object(PyHecateVideo, "_get_video_meta")
def test_add_outro_broad_exception_on_run(
    mock_get_meta,
    mock_ffmpeg_input,
    mock_ffmpeg_concat,
    mock_ffmpeg_output_exception,
    pv_add_outro_instance,
    caplog: LogCaptureFixture,
) -> None:
    """Test add_outro handles broad exceptions during ffmpeg.output().run_async()."""
    pv_add_outro_instance.vaudio = True
    mock_get_meta.return_value = VideoMetadata(
        success=True, vseconds=10, vwidth=1280, vheight=720, vaudio=True
    )

    mock_in1 = mock_ffmpeg_input_chain(has_audio=True)
    mock_in2 = mock_ffmpeg_input_chain(has_audio=True)
    mock_ffmpeg_input.side_effect = [mock_in1, mock_in2]
    mock_ffmpeg_concat.return_value.node = (MagicMock(), MagicMock())

    # The exception is raised when ffmpeg.output() is called, before run_async
    # To test exception from run_async itself, the mock_ffmpeg_output.return_value.run_async.side_effect = Exception(...)

    # Let's refine the mock to raise from run_async
    mock_ffmpeg_output_instance = MagicMock()
    mock_ffmpeg_output_instance.run_async.side_effect = Exception(
        "Broad run_async exception"
    )
    # We need to re-patch ffmpeg.output to return this instance
    # This is getting complex. Let's assume the previous test with side_effect on ffmpeg.output()
    # covers the scenario where ffmpeg.output() itself fails before run_async.
    # For an exception specifically from run_async:

    # Re-patching for run_async specific exception:
    # We need a new patch for this specific case if ffmpeg.output is already patched at function level.
    # It's easier to make the mock_ffmpeg_output.return_value.run_async itself have a side_effect.
    # The current @patch("ffmpeg.output", side_effect=...) is general.
    # Let's adjust the test for an exception from run_async()

    # Resetting the top-level patch for ffmpeg.output for this specific test case
    with patch("ffmpeg.output") as mock_ffmpeg_output_again:
        mock_output_obj = MagicMock()
        mock_output_obj.run_async.side_effect = Exception(
            "Broad run_async exception from run_async"
        )
        mock_ffmpeg_output_again.return_value = mock_output_obj

        assert pv_add_outro_instance.add_outro() is False
        assert (
            f"Failed adding outro to {pv_add_outro_instance.mp4sumpath}: Broad run_async exception from run_async"
            in caplog.text
        )


# Note: Testing send2trash calls would require further mocking of os.path.exists and send2trash.
# For now, we assume send2trash works if called.
