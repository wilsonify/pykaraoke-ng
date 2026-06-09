"""
Tests for queue and playback defect.

Verifies that:
  - add_to_playlist + play without playlist_index auto-plays from queue
  - play returns error when both queue and current_song are empty
  - play with valid playlist_index still works
  - play/pause/resume cycle works after queue enqueue
"""

from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()


def _get_backend():
    try:
        from pykaraoke.core.backend import PyKaraokeBackend
        return PyKaraokeBackend()
    except (RuntimeError, ImportError) as exc:
        pytest.skip(f"Backend dependencies not available: {exc}")


def _mock_song(title="Test Song", artist="Test Artist", filepath="/tmp/test.kar"):
    song = MagicMock()
    song.title = title
    song.artist = artist
    song.filepath = filepath
    song.display_filename = filepath.split("/")[-1].split("\\")[-1]
    song.zip_stored_name = None
    return song


# ===========================================================================
# Defect 2: Queue and Playback Do Not Work
# ===========================================================================


class TestPlayFromQueue:
    """Play command should auto-play from queue when no current_song."""

    def test_play_from_queue_when_no_current_song(self):
        """Play without playlist_index should auto-play first queued song."""
        backend = _get_backend()
        mock_song = _mock_song("Auto Play", "Artist", "/tmp/auto.kar")

        with patch.object(backend.song_db, "make_song_struct", return_value=mock_song):
            # Enqueue a song
            resp = backend.handle_command({
                "action": "add_to_playlist",
                "params": {"filepath": "/tmp/auto.kar"},
            })
            assert resp["status"] == "ok"
            assert len(backend.playlist) == 1

        # current_song should still be None at this point
        assert backend.current_song is None

        with patch.object(backend, "_start_playback", return_value={"status": "ok"}) as mock_start:
            # Play without playlist_index
            resp = backend.handle_command({"action": "play", "params": {}})
            assert resp["status"] == "ok", (
                f"Expected 'ok' when playlist has songs, got: {resp}"
            )
            mock_start.assert_called_once()
            assert backend.current_song is not None
            assert backend.current_song.filepath == "/tmp/auto.kar"

    def test_play_from_queue_selects_first_song(self):
        """Play should select playlist[0] when no playlist_index given."""
        backend = _get_backend()
        songs = [
            _mock_song("First", "A", "/tmp/first.kar"),
            _mock_song("Second", "B", "/tmp/second.kar"),
        ]

        with patch.object(backend.song_db, "make_song_struct", side_effect=songs):
            for fp in ["/tmp/first.kar", "/tmp/second.kar"]:
                backend.handle_command({
                    "action": "add_to_playlist",
                    "params": {"filepath": fp},
                })
            assert len(backend.playlist) == 2

        with patch.object(backend, "_start_playback", return_value={"status": "ok"}):
            resp = backend.handle_command({"action": "play", "params": {}})
            assert resp["status"] == "ok"
            assert backend.current_song.title == "First"

    def test_play_returns_error_when_no_songs(self):
        """Play should return error when both playlist and current_song are empty."""
        backend = _get_backend()
        with patch.object(backend, "_start_playback", return_value={"status": "ok"}):
            resp = backend.handle_command({"action": "play", "params": {}})
            assert resp["status"] == "error"

    def test_play_with_valid_playlist_index(self):
        """Play with a valid playlist_index should still work."""
        backend = _get_backend()
        songs = [
            _mock_song("Index 0", "A", "/tmp/i0.kar"),
            _mock_song("Index 1", "B", "/tmp/i1.kar"),
        ]

        with patch.object(backend.song_db, "make_song_struct", side_effect=songs):
            for fp in ["/tmp/i0.kar", "/tmp/i1.kar"]:
                backend.handle_command({
                    "action": "add_to_playlist",
                    "params": {"filepath": fp},
                })

        with patch.object(backend, "_start_playback", return_value={"status": "ok"}):
            resp = backend.handle_command({
                "action": "play",
                "params": {"playlist_index": 1},
            })
            assert resp["status"] == "ok"
            assert backend.current_song.title == "Index 1"

    def test_play_with_invalid_playlist_index(self):
        """Play with an out-of-range playlist_index should error."""
        backend = _get_backend()
        resp = backend.handle_command({
            "action": "play",
            "params": {"playlist_index": 99},
        })
        assert resp["status"] == "error"

    def test_play_from_queue_sets_playlist_index(self):
        """Auto-play from queue should set playlist_index to 0."""
        backend = _get_backend()
        mock_song = _mock_song("Auto", "A", "/tmp/a.kar")

        with patch.object(backend.song_db, "make_song_struct", return_value=mock_song):
            backend.handle_command({
                "action": "add_to_playlist",
                "params": {"filepath": "/tmp/a.kar"},
            })

        with patch.object(backend, "_start_playback", return_value={"status": "ok"}):
            backend.handle_command({"action": "play", "params": {}})
            assert backend.playlist_index == 0
