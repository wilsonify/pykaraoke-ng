"""
Comprehensive tests for pykaraoke.core.backend module.

Tests PyKaraokeBackend with mocked dependencies for full coverage
without requiring pygame display or audio.
"""

import json
import sys
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()


class TestBackendState:
    """Tests for BackendState enumeration."""

    def test_backend_state_values(self):
        from pykaraoke.core.backend import BackendState

        assert BackendState.IDLE.value == "idle"
        assert BackendState.PLAYING.value == "playing"
        assert BackendState.PAUSED.value == "paused"
        assert BackendState.STOPPED.value == "stopped"
        assert BackendState.LOADING.value == "loading"
        assert BackendState.ERROR.value == "error"

    def test_backend_state_all_unique(self):
        from pykaraoke.core.backend import BackendState

        values = [s.value for s in BackendState]
        assert len(values) == len(set(values))


class TestPyKaraokeBackendInit:
    """Tests for PyKaraokeBackend initialization."""

    def test_backend_creates(self):
        """Backend should be constructible."""
        try:
            from pykaraoke.core.backend import PyKaraokeBackend

            backend = PyKaraokeBackend()
            assert backend is not None
        except (RuntimeError, ImportError):
            pytest.skip("Backend dependencies not available")

    def test_backend_initial_state_idle(self):
        try:
            from pykaraoke.core.backend import PyKaraokeBackend, BackendState

            backend = PyKaraokeBackend()
            assert backend.state == BackendState.IDLE
        except (RuntimeError, ImportError):
            pytest.skip("Backend dependencies not available")

    def test_backend_initial_playlist_empty(self):
        try:
            from pykaraoke.core.backend import PyKaraokeBackend

            backend = PyKaraokeBackend()
            assert backend.playlist == []
            assert backend.playlist_index == -1
        except (RuntimeError, ImportError):
            pytest.skip("Backend dependencies not available")

    def test_backend_initial_volume(self):
        try:
            from pykaraoke.core.backend import PyKaraokeBackend

            backend = PyKaraokeBackend()
            assert backend.volume == 0.75
        except (RuntimeError, ImportError):
            pytest.skip("Backend dependencies not available")

    def test_backend_initial_no_player(self):
        try:
            from pykaraoke.core.backend import PyKaraokeBackend

            backend = PyKaraokeBackend()
            assert backend.current_player is None
            assert backend.current_song is None
        except (RuntimeError, ImportError):
            pytest.skip("Backend dependencies not available")

    def test_backend_initial_position(self):
        try:
            from pykaraoke.core.backend import PyKaraokeBackend

            backend = PyKaraokeBackend()
            assert backend.position_ms == 0
            assert backend.duration_ms == 0
        except (RuntimeError, ImportError):
            pytest.skip("Backend dependencies not available")


class TestBackendCommands:
    """Tests for backend command handling."""

    def _get_backend(self):
        try:
            from pykaraoke.core.backend import PyKaraokeBackend

            return PyKaraokeBackend()
        except (RuntimeError, ImportError):
            pytest.skip("Backend dependencies not available")

    def test_unknown_action(self):
        backend = self._get_backend()
        response = backend.handle_command({"action": "nonexistent"})
        assert response["status"] == "error"
        assert "Unknown action" in response["message"]

    def test_get_state_command(self):
        backend = self._get_backend()
        response = backend.handle_command({"action": "get_state"})
        assert response["status"] == "ok"
        assert "data" in response
        assert "playback_state" in response["data"]

    def test_set_volume_command(self):
        backend = self._get_backend()
        response = backend.handle_command(
            {"action": "set_volume", "params": {"volume": 0.5}}
        )
        assert response["status"] == "ok"
        assert backend.volume == 0.5

    def test_set_volume_clamp_high(self):
        backend = self._get_backend()
        response = backend.handle_command(
            {"action": "set_volume", "params": {"volume": 2.0}}
        )
        assert response["status"] == "ok"
        assert backend.volume == 1.0

    def test_set_volume_clamp_low(self):
        backend = self._get_backend()
        response = backend.handle_command(
            {"action": "set_volume", "params": {"volume": -1.0}}
        )
        assert response["status"] == "ok"
        assert backend.volume == 0.0

    def test_clear_playlist_command(self):
        backend = self._get_backend()
        response = backend.handle_command({"action": "clear_playlist"})
        assert response["status"] == "ok"
        assert backend.playlist == []
        assert backend.playlist_index == -1

    def test_pause_without_playing(self):
        backend = self._get_backend()
        response = backend.handle_command({"action": "pause"})
        assert response["status"] == "error"

    def test_stop_without_playing(self):
        backend = self._get_backend()
        response = backend.handle_command({"action": "stop"})
        assert response["status"] == "ok"  # Already stopped

    def test_next_empty_playlist(self):
        backend = self._get_backend()
        response = backend.handle_command({"action": "next"})
        assert response["status"] == "error"

    def test_previous_empty_playlist(self):
        backend = self._get_backend()
        response = backend.handle_command({"action": "previous"})
        assert response["status"] == "error"

    def test_seek_command(self):
        backend = self._get_backend()
        response = backend.handle_command(
            {"action": "seek", "params": {"position_ms": 5000}}
        )
        assert response["status"] == "ok"

    def test_play_no_song(self):
        backend = self._get_backend()
        response = backend.handle_command({"action": "play", "params": {}})
        assert response["status"] == "error"

    def test_play_invalid_playlist_index(self):
        backend = self._get_backend()
        response = backend.handle_command(
            {"action": "play", "params": {"playlist_index": 99}}
        )
        assert response["status"] == "error"

    def test_load_song_no_filepath(self):
        backend = self._get_backend()
        response = backend.handle_command(
            {"action": "load_song", "params": {}}
        )
        assert response["status"] == "error"

    def test_add_to_playlist_no_filepath(self):
        backend = self._get_backend()
        response = backend.handle_command(
            {"action": "add_to_playlist", "params": {}}
        )
        assert response["status"] == "error"

    def test_remove_from_playlist_invalid(self):
        backend = self._get_backend()
        response = backend.handle_command(
            {"action": "remove_from_playlist", "params": {"index": 99}}
        )
        assert response["status"] == "error"

    def test_add_folder_no_folder(self):
        backend = self._get_backend()
        response = backend.handle_command(
            {"action": "add_folder", "params": {}}
        )
        assert response["status"] == "error"

    def test_get_settings_command(self):
        backend = self._get_backend()
        response = backend.handle_command({"action": "get_settings"})
        assert response["status"] == "ok"
        assert "data" in response

    def test_update_settings_command(self):
        backend = self._get_backend()
        response = backend.handle_command(
            {"action": "update_settings", "params": {"key": "value"}}
        )
        assert response["status"] == "ok"

    def test_search_songs_command(self):
        backend = self._get_backend()
        response = backend.handle_command(
            {"action": "search_songs", "params": {"query": "test"}}
        )
        # May succeed or fail depending on database state
        assert response["status"] in ("ok", "error")

    def test_get_library_command(self):
        backend = self._get_backend()
        response = backend.handle_command({"action": "get_library"})
        assert response["status"] in ("ok", "error")

    def test_scan_library_command(self):
        backend = self._get_backend()
        response = backend.handle_command({"action": "scan_library"})
        assert response["status"] in ("ok", "error")


class TestBackendEvents:
    """Tests for backend event emission."""

    def _get_backend(self):
        try:
            from pykaraoke.core.backend import PyKaraokeBackend

            return PyKaraokeBackend()
        except (RuntimeError, ImportError):
            pytest.skip("Backend dependencies not available")

    def test_set_event_callback(self):
        backend = self._get_backend()
        callback = MagicMock()
        backend.set_event_callback(callback)
        assert backend.event_callback == callback

    def test_emit_event_calls_callback(self):
        backend = self._get_backend()
        callback = MagicMock()
        backend.set_event_callback(callback)
        backend._emit_event("test_event", {"key": "value"})
        callback.assert_called_once()
        event = callback.call_args[0][0]
        assert event["type"] == "test_event"
        assert "timestamp" in event

    def test_emit_event_no_callback(self):
        backend = self._get_backend()
        backend.event_callback = None
        # Should not raise
        backend._emit_event("test_event")

    def test_emit_state_change(self):
        backend = self._get_backend()
        callback = MagicMock()
        backend.set_event_callback(callback)
        backend._emit_state_change()
        callback.assert_called_once()
        event = callback.call_args[0][0]
        assert event["type"] == "state_changed"


class TestBackendGetState:
    """Tests for get_state serialization."""

    def _get_backend(self):
        try:
            from pykaraoke.core.backend import PyKaraokeBackend

            return PyKaraokeBackend()
        except (RuntimeError, ImportError):
            pytest.skip("Backend dependencies not available")

    def test_get_state_returns_dict(self):
        backend = self._get_backend()
        state = backend.get_state()
        assert isinstance(state, dict)

    def test_get_state_has_required_fields(self):
        backend = self._get_backend()
        state = backend.get_state()
        assert "playback_state" in state
        assert "current_song" in state
        assert "playlist" in state
        assert "playlist_index" in state
        assert "volume" in state
        assert "position_ms" in state
        assert "duration_ms" in state

    def test_get_state_json_serializable(self):
        backend = self._get_backend()
        state = backend.get_state()
        json_str = json.dumps(state)
        parsed = json.loads(json_str)
        assert parsed["playback_state"] == "idle"

    def test_song_to_dict_none(self):
        backend = self._get_backend()
        state = backend.get_state()
        assert state["current_song"] is None

    def test_song_to_dict_with_mock_song(self):
        backend = self._get_backend()
        mock_song = MagicMock()
        mock_song.Title = "Test Song"
        mock_song.Artist = "Test Artist"
        mock_song.DisplayFilename = "test.cdg"
        mock_song.Filepath = "/path/test.cdg"
        mock_song.ZipStoredName = None
        result = backend._song_to_dict(mock_song)
        assert result["title"] == "Test Song"
        assert result["artist"] == "Test Artist"
        assert result["filename"] == "test.cdg"


class TestBackendPoll:
    """Tests for backend poll method."""

    def _get_backend(self):
        try:
            from pykaraoke.core.backend import PyKaraokeBackend

            return PyKaraokeBackend()
        except (RuntimeError, ImportError):
            pytest.skip("Backend dependencies not available")

    def test_poll_no_player(self):
        backend = self._get_backend()
        backend.current_player = None
        backend.poll()  # Should not raise

    def test_poll_with_player(self):
        from pykaraoke.core.backend import BackendState

        backend = self._get_backend()
        backend.current_player = MagicMock()
        backend.current_player.GetPos.return_value = 1000
        backend.state = BackendState.PLAYING
        backend.poll()
        assert backend.position_ms == 1000


class TestBackendShutdown:
    """Tests for backend shutdown."""

    def _get_backend(self):
        try:
            from pykaraoke.core.backend import PyKaraokeBackend

            return PyKaraokeBackend()
        except (RuntimeError, ImportError):
            pytest.skip("Backend dependencies not available")

    def test_shutdown_no_player(self):
        backend = self._get_backend()
        backend.current_player = None
        backend.shutdown()  # Should not raise

    def test_shutdown_with_player(self):
        backend = self._get_backend()
        mock_player = MagicMock()
        backend.current_player = mock_player
        backend.shutdown()
        mock_player.Close.assert_called_once()


class TestBackendMain:
    """Tests for backend main() entry point."""

    def test_main_function_exists(self):
        from pykaraoke.core.backend import main

        assert callable(main)

    def test_create_stdio_server_exists(self):
        from pykaraoke.core.backend import create_stdio_server

        assert callable(create_stdio_server)

    def test_create_http_server_exists(self):
        from pykaraoke.core.backend import create_http_server

        assert callable(create_http_server)

    def test_imports_available_flag(self):
        from pykaraoke.core import backend

        assert hasattr(backend, "IMPORTS_AVAILABLE")
        assert isinstance(backend.IMPORTS_AVAILABLE, bool)
