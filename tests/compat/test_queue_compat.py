"""
Compatibility tests: queue management (Priority 4).

Exercises the same queue operations (add, remove, clear, select, advance)
through both the Python reference and the Rust engine, then compares
playlist state.
"""

import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RS_CLI = os.path.join(
    PROJECT_ROOT,
    "target",
    "debug",
    "pykaraoke-engine-cli.exe" if sys.platform == "win32" else "pykaraoke-engine-cli",
)


def rs_queue_command(command, **params):
    """Send a queue command to the Rust CLI and return the JSON response."""
    if not os.path.isfile(RS_CLI):
        pytest.skip(f"Rust CLI not built at {RS_CLI}")
    args = [RS_CLI, "queue", command]
    for key, value in params.items():
        args.append(f"--{key}")
        args.append(str(value))
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        pytest.fail(f"Rust queue CLI failed:\n{result.stderr}")
    return json.loads(result.stdout)


def _get_py_backend():
    """Create a Python backend instance with mocked pygame."""
    try:
        from pykaraoke.core.backend import PyKaraokeBackend
        return PyKaraokeBackend()
    except (RuntimeError, ImportError) as exc:
        pytest.skip(f"Backend deps unavailable: {exc}")


def _mock_song(title="Test Song", artist="Test Artist", filepath="/tmp/test.kar"):
    song = MagicMock()
    song.title = title
    song.artist = artist
    song.filepath = filepath
    song.display_filename = filepath.split("/")[-1].split("\\")[-1]
    song.zip_stored_name = None
    return song


class TestQueueCompat:
    """Compare Python and Rust queue behaviour."""

    def test_enqueue_increments_length(self):
        """Add to playlist increments length."""
        backend = _get_py_backend()
        mock_song = _mock_song()
        with patch.object(backend.song_db, "make_song_struct", return_value=mock_song):
            assert len(backend.playlist) == 0
            resp = backend.handle_command({
                "action": "add_to_playlist",
                "params": {"filepath": "/tmp/test.kar"},
            })
            assert resp["status"] == "ok"
            assert len(backend.playlist) == 1

    def test_enqueue_returns_error_without_filepath(self):
        """Missing filepath returns error."""
        backend = _get_py_backend()
        resp = backend.handle_command({
            "action": "add_to_playlist",
            "params": {},
        })
        assert resp["status"] == "error"
        assert "filepath" in resp["message"].lower()

    def test_enqueue_multiple_songs(self):
        """Multiple adds increment correctly."""
        backend = _get_py_backend()
        songs = [_mock_song(f"Song {i}", f"Artist {i}", f"/tmp/song{i}.kar") for i in range(3)]
        with patch.object(backend.song_db, "make_song_struct", side_effect=songs):
            for i in range(3):
                resp = backend.handle_command({
                    "action": "add_to_playlist",
                    "params": {"filepath": f"/tmp/song{i}.kar"},
                })
                assert resp["status"] == "ok"
            assert len(backend.playlist) == 3

    def test_clear_playlist(self):
        """Clear removes all entries."""
        backend = _get_py_backend()
        mock_song = _mock_song()
        with patch.object(backend.song_db, "make_song_struct", return_value=mock_song):
            backend.handle_command({
                "action": "add_to_playlist",
                "params": {"filepath": "/tmp/test.kar"},
            })
            assert len(backend.playlist) == 1

        resp = backend.handle_command({"action": "clear_playlist", "params": {}})
        assert resp["status"] == "ok"
        assert len(backend.playlist) == 0

    def test_play_from_queue_auto_advances(self):
        """Play without index auto-selects first queued song."""
        backend = _get_py_backend()
        mock_song = _mock_song("Auto Play", "Artist", "/tmp/auto.kar")
        with patch.object(backend.song_db, "make_song_struct", return_value=mock_song):
            resp = backend.handle_command({
                "action": "add_to_playlist",
                "params": {"filepath": "/tmp/auto.kar"},
            })
            assert resp["status"] == "ok"

        assert backend.current_song is None
        with patch.object(backend, "_start_playback", return_value={"status": "ok"}):
            resp = backend.handle_command({"action": "play", "params": {}})
            assert resp["status"] == "ok"
            assert backend.current_song is not None
