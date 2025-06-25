import os
from unittest.mock import patch

import pytest
from _pytest.logging import LogCaptureFixture # Import for caplog type

from pyhecate import PyHecateVideo


@pytest.fixture
def pv_cleanup_instance(tmp_path) -> PyHecateVideo:
    """Provides a PyHecateVideo instance for cleanup_folders tests."""
    # This outdir is where source files (before cleanup) are located
    # and also the parent of structured dirs (jpgdir, gifdir etc.)
    processing_outdir = tmp_path / "video_processing_output"
    processing_outdir.mkdir()

    pv = PyHecateVideo(path="dummy_video.mp4", outdir=str(processing_outdir))
    pv.base = "dummy_video"  # What os.path.split(outdir)[1] would be

    # Simulate that prep_outfolders has run and set these paths
    # These paths are subdirectories of pv.outdir (processing_outdir)
    pv.jpgdir = str(processing_outdir / "jpg-1280")
    pv.gifdir = str(processing_outdir / "gif-360")
    pv.gifsumdir = str(processing_outdir / "gifsum-360")
    pv.mp4dir = str(
        processing_outdir / "mp4-16"
    )  # Not directly used by cleanup_folders logic but part of setup

    # Files that cleanup_folders expects to move
    pv.mp4tmppath = str(
        processing_outdir / f"{pv.base}_sum.mp4"
    )  # Temp summary to be moved
    pv.mp4sumpath = str(
        processing_outdir / "mp4-16" / f"{pv.base}_sum-16.mp4"
    )  # Final sum path

    # Create the subdirectories that shutil.move will target
    os.makedirs(pv.jpgdir, exist_ok=True)
    os.makedirs(pv.gifdir, exist_ok=True)
    os.makedirs(pv.gifsumdir, exist_ok=True)
    os.makedirs(pv.mp4dir, exist_ok=True)

    return pv


def create_dummy_files(base_dir: str, files_to_create: list[str]) -> None:
    """Helper to create dummy files in base_dir."""
    for fname in files_to_create:
        with open(os.path.join(base_dir, fname), "w") as f:
            f.write("dummy data")


def test_cleanup_folders_success_images_and_video(
    pv_cleanup_instance, caplog: LogCaptureFixture
) -> None:
    """Test cleanup_folders success with images and video enabled."""
    pv_cleanup_instance.isum = True
    pv_cleanup_instance.vsum = True

    # Create dummy files in pv_cleanup_instance.outdir that should be moved
    dummy_jpgs = ["img1.jpg", "img2.jpg"]
    dummy_gifs = ["anim1.gif", "anim2.gif"]
    dummy_gifsum = f"{pv_cleanup_instance.base}_sum.gif"
    dummy_mp4sum_temp = os.path.basename(
        pv_cleanup_instance.mp4tmppath
    )  # e.g., dummy_video_sum.mp4

    create_dummy_files(
        pv_cleanup_instance.outdir,
        dummy_jpgs + dummy_gifs + [dummy_gifsum, dummy_mp4sum_temp],
    )

    assert pv_cleanup_instance.cleanup_folders() is True

    # Verify files moved
    for jpg in dummy_jpgs:
        assert not os.path.exists(os.path.join(pv_cleanup_instance.outdir, jpg))
        assert os.path.exists(os.path.join(pv_cleanup_instance.jpgdir, jpg))
    for gif in dummy_gifs:
        assert not os.path.exists(os.path.join(pv_cleanup_instance.outdir, gif))
        assert os.path.exists(os.path.join(pv_cleanup_instance.gifdir, gif))
    assert not os.path.exists(os.path.join(pv_cleanup_instance.outdir, dummy_gifsum))
    assert os.path.exists(os.path.join(pv_cleanup_instance.gifsumdir, dummy_gifsum))

    assert not os.path.exists(
        pv_cleanup_instance.mp4tmppath
    )  # Temp path should be gone
    assert os.path.exists(pv_cleanup_instance.mp4sumpath)  # Final path should exist


def test_cleanup_folders_success_images_only(
    pv_cleanup_instance, caplog: LogCaptureFixture
) -> None:
    pv_cleanup_instance.isum = True
    pv_cleanup_instance.vsum = False  # Video summary disabled

    dummy_jpgs = ["img1.jpg"]
    create_dummy_files(pv_cleanup_instance.outdir, dummy_jpgs)

    # Create the temp mp4 summary file, it should NOT be moved if vsum is False
    temp_mp4_name = os.path.basename(pv_cleanup_instance.mp4tmppath)
    create_dummy_files(pv_cleanup_instance.outdir, [temp_mp4_name])

    assert pv_cleanup_instance.cleanup_folders() is True
    assert os.path.exists(os.path.join(pv_cleanup_instance.jpgdir, "img1.jpg"))
    assert os.path.exists(
        pv_cleanup_instance.mp4tmppath
    )  # Should still exist as vsum is False
    assert not os.path.exists(pv_cleanup_instance.mp4sumpath)


def test_cleanup_folders_success_video_only(
    pv_cleanup_instance, caplog: LogCaptureFixture
) -> None:
    pv_cleanup_instance.isum = False  # Image summary disabled
    pv_cleanup_instance.vsum = True

    dummy_jpg = "img1.jpg"
    create_dummy_files(
        pv_cleanup_instance.outdir, [dummy_jpg]
    )  # This should NOT be moved
    temp_mp4_name = os.path.basename(pv_cleanup_instance.mp4tmppath)
    create_dummy_files(pv_cleanup_instance.outdir, [temp_mp4_name])

    assert pv_cleanup_instance.cleanup_folders() is True
    assert os.path.exists(
        os.path.join(pv_cleanup_instance.outdir, dummy_jpg)
    )  # Still in root
    assert not os.path.exists(pv_cleanup_instance.mp4tmppath)
    assert os.path.exists(pv_cleanup_instance.mp4sumpath)


def test_cleanup_folders_no_files_to_move(pv_cleanup_instance, caplog):
    """Test cleanup_folders when no relevant files are found by glob."""
    pv_cleanup_instance.isum = True
    pv_cleanup_instance.vsum = True

    # No dummy files created in pv_cleanup_instance.outdir

    assert pv_cleanup_instance.cleanup_folders() is True
    # Check no errors logged for file operations
    for record in caplog.records:
        assert record.levelname != "ERROR"
        # shutil.move would raise error if source doesn't exist, but glob prevents this.


def test_cleanup_folders_missing_image_output_dirs(pv_cleanup_instance, caplog):
    """Test cleanup_folders when image output directories are not set but isum is True."""
    pv_cleanup_instance.isum = True
    pv_cleanup_instance.vsum = False
    pv_cleanup_instance.jpgdir = None  # Simulate prep_outfolders failure for this dir

    assert pv_cleanup_instance.cleanup_folders() is False
    assert "Image output directories not initialized in cleanup_folders." in caplog.text


def test_cleanup_folders_missing_video_output_paths(pv_cleanup_instance, caplog):
    """Test cleanup_folders when video output paths are not set but vsum is True."""
    pv_cleanup_instance.isum = False
    pv_cleanup_instance.vsum = True
    pv_cleanup_instance.mp4tmppath = (
        None  # Simulate prep_outfolders failure for this path
    )

    assert pv_cleanup_instance.cleanup_folders() is False
    assert "Video output paths not initialized in cleanup_folders." in caplog.text


@patch("shutil.move", side_effect=OSError("Simulated permission error"))
def test_cleanup_folders_shutil_move_fails(
    mock_shutil_move, pv_cleanup_instance, caplog
):
    """Test cleanup_folders when shutil.move raises an OSError."""
    pv_cleanup_instance.isum = True
    pv_cleanup_instance.vsum = True  # Enable both to ensure move is attempted

    # Create one file of each type to trigger shutil.move attempts
    create_dummy_files(
        pv_cleanup_instance.outdir,
        [
            "test.jpg",
            f"{pv_cleanup_instance.base}_sum.gif",
            os.path.basename(pv_cleanup_instance.mp4tmppath),
        ],
    )

    # shutil.move errors are not currently caught by cleanup_folders itself
    with pytest.raises(OSError, match="Simulated permission error"):
        pv_cleanup_instance.cleanup_folders()

    # Check that shutil.move was called (at least once before failing)
    mock_shutil_move.assert_called()
    # Note: Depending on which move fails first, subsequent moves might not happen.
    # The test confirms the exception propagates.
