"""
Tests for the queue/enqueue functionality.

Verifies that:
  - add_to_playlist correctly creates a SongStruct and appends it
  - .kar files are recognised and enqueued
  - Artist/title are parsed from the Elvis fixture filename
  - The queue length increments
  - Missing filepaths are rejected with a clear error
  - The Elvis .kar fixture can be loaded end-to-end

These tests mock pygame so they can run headless on any CI runner.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_backend():
    """Create a PyKaraokeBackend instance, skip if deps are unavailable."""
    try:
        from pykaraoke.core.backend import PyKaraokeBackend
        return PyKaraokeBackend()
    except (RuntimeError, ImportError) as exc:
        pytest.skip(f"Backend dependencies not available: {exc}")


def _mock_song(title="Test Song", artist="Test Artist", filepath="/tmp/test.kar"):
    """Create a mock SongStruct-like object."""
    song = MagicMock()
    song.title = title
    song.artist = artist
    song.filepath = filepath
    song.display_filename = os.path.basename(filepath)
    song.zip_stored_name = None
    return song


FIXTURES_DIR = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "fixtures",
    "ultrastar-deluxe", "Creative Commons",
)

ELVIS_FIXTURE = os.path.join(
    FIXTURES_DIR, "elvis_presley_-_cant_help_falling_in_love.kar",
)


# ===========================================================================
# Unit tests – queue behaviour
# ===========================================================================


class TestEnqueueBasic:
    """Verify that the add_to_playlist command works after the fix."""

    def test_enqueue_increments_queue_length(self):
        backend = _get_backend()
        mock_song = _mock_song()
        with patch.object(backend.song_db, "make_song_struct", return_value=mock_song):
            assert len(backend.playlist) == 0

            response = backend.handle_command({
                "action": "add_to_playlist",
                "params": {"filepath": "/tmp/test.kar"},
            })

            assert response["status"] == "ok"
            assert len(backend.playlist) == 1

    def test_enqueue_returns_error_without_filepath(self):
        backend = _get_backend()
        response = backend.handle_command({
            "action": "add_to_playlist",
            "params": {},
        })
        assert response["status"] == "error"
        assert "filepath" in response["message"].lower()

    def test_enqueue_multiple_songs(self):
        backend = _get_backend()
        songs = [_mock_song(f"Song {i}", f"Artist {i}", f"/tmp/song{i}.kar") for i in range(3)]
        with patch.object(backend.song_db, "make_song_struct", side_effect=songs):
            for i in range(3):
                resp = backend.handle_command({
                    "action": "add_to_playlist",
                    "params": {"filepath": f"/tmp/song{i}.kar"},
                })
                assert resp["status"] == "ok"

            assert len(backend.playlist) == 3

    def test_enqueue_error_surfaces_message(self):
        """When make_song_struct raises, the error should surface in the response."""
        backend = _get_backend()
        with patch.object(
            backend.song_db, "make_song_struct",
            side_effect=ValueError("File not found: /bad/path.kar"),
        ):
            response = backend.handle_command({
                "action": "add_to_playlist",
                "params": {"filepath": "/bad/path.kar"},
            })
            assert response["status"] == "error"
            assert "File not found" in response["message"]

    def test_enqueue_emits_playlist_updated_event(self):
        backend = _get_backend()
        events = []
        backend.set_event_callback(lambda e: events.append(e))

        mock_song = _mock_song("My Song", "My Artist", "/tmp/my.kar")
        with patch.object(backend.song_db, "make_song_struct", return_value=mock_song):
            backend.handle_command({
                "action": "add_to_playlist",
                "params": {"filepath": "/tmp/my.kar"},
            })

        playlist_events = [e for e in events if e["type"] == "playlist_updated"]
        assert len(playlist_events) == 1
        assert len(playlist_events[0]["data"]["playlist"]) == 1


class TestEnqueueKarFormat:
    """Verify .kar file format is handled correctly during enqueue."""

    def test_kar_extension_recognised(self):
        """Settings include .kar in kar_extensions by default."""
        from pykaraoke.core.database import SettingsStruct
        settings = SettingsStruct()
        assert ".kar" in settings.kar_extensions

    def test_enqueue_kar_file(self):
        """A .kar filepath should be accepted by add_to_playlist."""
        backend = _get_backend()
        mock_song = _mock_song("Cant Help Falling In Love", "Elvis Presley", "/songs/elvis.kar")
        with patch.object(backend.song_db, "make_song_struct", return_value=mock_song):
            resp = backend.handle_command({
                "action": "add_to_playlist",
                "params": {"filepath": "/songs/elvis.kar"},
            })
            assert resp["status"] == "ok"
            assert backend.playlist[0].title == "Cant Help Falling In Love"
            assert backend.playlist[0].artist == "Elvis Presley"


class TestFilenameParsingForQueue:
    """Verify the filename parser extracts artist/title from the Elvis fixture."""

    def test_elvis_fixture_parsed(self):
        from pykaraoke.core.filename_parser import FilenameParser

        parser = FilenameParser()
        result = parser.parse(
            "elvis_presley_-_cant_help_falling_in_love.kar"
        )
        # The " - " pattern is detected via underscores around dash
        # The filename uses underscores, so the space-dash-space regex
        # won't match. It falls through to legacy Artist-Title parsing.
        # With the ARTIST_TITLE default the first part before the first
        # dash is the artist.
        assert result.artist != ""
        assert result.title != ""

    def test_elvis_space_dash_filename_parsed(self):
        """If the filename uses spaces (as presented in the UI), parsing works."""
        from pykaraoke.core.filename_parser import FilenameParser

        parser = FilenameParser()
        result = parser.parse(
            "Elvis Presley - Cant Help Falling In Love.kar"
        )
        assert result.artist == "Elvis Presley"
        assert result.title == "Cant Help Falling In Love"


# ===========================================================================
# Integration test – Elvis fixture file
# ===========================================================================


class TestElvisFixtureIntegration:
    """Integration test: load the real Elvis .kar fixture into the queue."""

    @pytest.mark.integration
    def test_elvis_fixture_exists(self):
        """The Elvis fixture file should exist on disk."""
        assert os.path.isfile(ELVIS_FIXTURE), (
            f"Fixture not found: {ELVIS_FIXTURE}"
        )

    @pytest.mark.integration
    def test_elvis_fixture_enqueues(self):
        """Enqueue the real Elvis .kar fixture and verify queue state."""
        if not os.path.isfile(ELVIS_FIXTURE):
            pytest.skip("Elvis fixture not found")

        backend = _get_backend()

        response = backend.handle_command({
            "action": "add_to_playlist",
            "params": {"filepath": os.path.abspath(ELVIS_FIXTURE)},
        })

        assert response["status"] == "ok", f"Enqueue failed: {response}"
        assert len(backend.playlist) == 1

        queued = backend.playlist[0]
        # Verify that the queued item has a display_filename containing "elvis"
        display = getattr(queued, "display_filename", "")
        assert "elvis" in display.lower() or "cant_help" in display.lower(), (
            f"Unexpected display_filename: {display}"
        )

    @pytest.mark.integration
    def test_elvis_fixture_queue_state(self):
        """After enqueueing Elvis, get_state should reflect the queue."""
        if not os.path.isfile(ELVIS_FIXTURE):
            pytest.skip("Elvis fixture not found")

        backend = _get_backend()
        resp = backend.handle_command({
            "action": "add_to_playlist",
            "params": {"filepath": os.path.abspath(ELVIS_FIXTURE)},
        })
        assert resp["status"] == "ok", f"Enqueue failed: {resp}"

        state = backend.get_state()
        assert len(state["playlist"]) == 1
        # The filepath should be present in the serialised state
        assert state["playlist"][0]["filepath"] != ""


# ===========================================================================
# Regression: make_song_struct vs makeSongStruct
# ===========================================================================


class TestMakeSongStructMethodName:
    """Regression test: ensure the backend calls the correct method name."""

    def test_song_db_has_make_song_struct(self):
        """SongDB must expose make_song_struct (snake_case)."""
        from pykaraoke.core.database import SongDB
        assert hasattr(SongDB, "make_song_struct"), (
            "SongDB must have make_song_struct method"
        )

    def test_backend_calls_make_song_struct(self):
        """Backend add_to_playlist must call make_song_struct, not makeSongStruct."""
        backend = _get_backend()
        mock_song = _mock_song("T", "A", "/x.kar")

        with patch.object(backend.song_db, "make_song_struct", return_value=mock_song) as mock_method:
            backend.handle_command({
                "action": "add_to_playlist",
                "params": {"filepath": "/x.kar"},
            })
            mock_method.assert_called_once_with("/x.kar")

    def test_backend_does_not_call_camelcase(self):
        """Ensure the old camelCase name is NOT called."""
        backend = _get_backend()
        mock_song = _mock_song("T", "A", "/x.kar")

        with patch.object(backend.song_db, "make_song_struct", return_value=mock_song):
            # Attach a spy for the old name
            backend.song_db.makeSongStruct = MagicMock()

            backend.handle_command({
                "action": "add_to_playlist",
                "params": {"filepath": "/x.kar"},
            })

            backend.song_db.makeSongStruct.assert_not_called()
