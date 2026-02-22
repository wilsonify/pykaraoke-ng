"""
Targeted tests for backend.py new/changed code lines.

Covers the error paths and dispatch-table changes introduced by recent refactoring:
- _init_database error handling (line 139)
- _emit_event error callback (line 153)
- handle_command dispatch table (lines 175-181)
- _handle_play player-creation failure (line 308)
- _on_player_error callback (lines 327-330)
"""

import os
import sys
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()

from pykaraoke.core.backend import PyKaraokeBackend, BackendState


def _make_backend():
    """Create a backend instance, skipping if deps are missing."""
    try:
        return PyKaraokeBackend()
    except Exception as exc:
        pytest.skip(f"Cannot create backend: {exc}")


# ---------- _init_database error path (line 139) ----------

class TestInitDatabaseError:
    """Covers the except branch when LoadSettings raises."""

    def test_init_database_oserror(self):
        with patch("pykaraoke.core.backend.database") as mock_db:
            mock_db.globalSongDB.load_settings.side_effect = OSError("disk fail")
            backend = PyKaraokeBackend()
            assert backend.error_message == "disk fail"

    def test_init_database_runtime_error(self):
        with patch("pykaraoke.core.backend.database") as mock_db:
            mock_db.globalSongDB.load_settings.side_effect = RuntimeError("corrupt")
            backend = PyKaraokeBackend()
            assert backend.error_message == "corrupt"

    def test_init_database_value_error(self):
        with patch("pykaraoke.core.backend.database") as mock_db:
            mock_db.globalSongDB.load_settings.side_effect = ValueError("bad val")
            backend = PyKaraokeBackend()
            assert backend.error_message == "bad val"


# ---------- _emit_event error path (line 153) ----------

class TestEmitEventError:
    """Covers the except branch in _emit_event when callback raises."""

    def test_emit_event_callback_raises_type_error(self):
        backend = _make_backend()
        bad_cb = MagicMock(side_effect=TypeError("bad callback"))
        backend.set_event_callback(bad_cb)
        # Should not propagate — the exception is logged
        backend._emit_event("test_event", {"key": "value"})
        bad_cb.assert_called_once()

    def test_emit_event_callback_raises_value_error(self):
        backend = _make_backend()
        bad_cb = MagicMock(side_effect=ValueError("value error in cb"))
        backend.set_event_callback(bad_cb)
        backend._emit_event("test_event")
        bad_cb.assert_called_once()

    def test_emit_event_callback_raises_runtime_error(self):
        backend = _make_backend()
        bad_cb = MagicMock(side_effect=RuntimeError("runtime cb error"))
        backend.set_event_callback(bad_cb)
        backend._emit_event("state_changed")
        bad_cb.assert_called_once()


# ---------- handle_command dispatch table (new code lines 104-125, 175-181) --

class TestHandleCommandDispatch:
    """Tests the command-handler dispatch table and error path."""

    def test_dispatch_unknown_action(self):
        backend = _make_backend()
        result = backend.handle_command({"action": "nonexistent_action"})
        assert result["status"] == "error"
        assert "Unknown action" in result["message"]

    def test_dispatch_handler_raises_runtime_error(self):
        backend = _make_backend()
        # Inject a handler that raises
        backend._command_handlers["boom"] = MagicMock(
            side_effect=RuntimeError("boom error")
        )
        result = backend.handle_command({"action": "boom", "params": {}})
        assert result["status"] == "error"
        assert "boom error" in result["message"]

    def test_dispatch_handler_raises_os_error(self):
        backend = _make_backend()
        backend._command_handlers["oserr"] = MagicMock(
            side_effect=OSError("os err")
        )
        result = backend.handle_command({"action": "oserr", "params": {}})
        assert result["status"] == "error"

    def test_dispatch_handler_raises_value_error(self):
        backend = _make_backend()
        backend._command_handlers["valerr"] = MagicMock(
            side_effect=ValueError("val err")
        )
        result = backend.handle_command({"action": "valerr", "params": {}})
        assert result["status"] == "error"

    def test_dispatch_handler_raises_type_error(self):
        backend = _make_backend()
        backend._command_handlers["typerr"] = MagicMock(
            side_effect=TypeError("type err")
        )
        result = backend.handle_command({"action": "typerr", "params": {}})
        assert result["status"] == "error"

    def test_dispatch_handler_raises_attribute_error(self):
        backend = _make_backend()
        backend._command_handlers["attrerr"] = MagicMock(
            side_effect=AttributeError("attr err")
        )
        result = backend.handle_command({"action": "attrerr", "params": {}})
        assert result["status"] == "error"

    def test_dispatch_get_state_returns_data(self):
        backend = _make_backend()
        result = backend.handle_command({"action": "get_state"})
        assert result["status"] == "ok"
        assert "data" in result

    def test_dispatch_all_known_actions_exist(self):
        backend = _make_backend()
        expected_actions = [
            "play", "pause", "stop", "next", "previous", "seek",
            "set_volume", "load_song", "add_to_playlist",
            "remove_from_playlist", "clear_playlist", "get_state",
            "search_songs", "get_library", "scan_library", "add_folder",
            "get_settings", "update_settings",
        ]
        for action in expected_actions:
            assert action in backend._command_handlers, f"Missing handler for {action}"


# ---------- _handle_play failure (line 308) ----------

class TestHandlePlayFailure:
    """Covers RuntimeError('Failed to create player') on line 308."""

    def test_play_with_no_current_song(self):
        backend = _make_backend()
        backend.current_song = None
        result = backend.handle_command({"action": "play", "params": {}})
        assert result["status"] == "error"

    def test_play_with_null_player(self):
        """MakePlayer returns None → RuntimeError."""
        backend = _make_backend()
        mock_song = MagicMock()
        mock_song.MakePlayer.return_value = None
        backend.current_song = mock_song
        result = backend.handle_command({"action": "play", "params": {}})
        assert result["status"] == "error"
        assert backend.state == BackendState.ERROR

    def test_play_make_player_raises(self):
        """MakePlayer raises an exception."""
        backend = _make_backend()
        mock_song = MagicMock()
        mock_song.MakePlayer.side_effect = RuntimeError("player init failed")
        backend.current_song = mock_song
        result = backend.handle_command({"action": "play", "params": {}})
        assert result["status"] == "error"
        assert "player init failed" in result["message"]


# ---------- _on_player_error callback (lines 325-330) ----------

class TestOnPlayerError:
    """Covers _on_player_error setting state and emitting event."""

    def test_on_player_error_sets_state(self):
        backend = _make_backend()
        cb = MagicMock()
        backend.set_event_callback(cb)
        backend._on_player_error("something went wrong")
        assert backend.state == BackendState.ERROR
        assert backend.error_message == "something went wrong"
        # Verify playback_error event emitted
        assert any(
            call.args[0].get("type") == "playback_error"
            for call in cb.call_args_list
        )

    def test_on_player_error_without_callback(self):
        backend = _make_backend()
        backend.event_callback = None
        backend._on_player_error("err msg")
        assert backend.state == BackendState.ERROR
        assert backend.error_message == "err msg"


# ---------- _on_song_finished callback ----------

class TestOnSongFinished:
    """Covers _on_song_finished auto-advance and idle state."""

    def test_on_song_finished_goes_idle_no_more_songs(self):
        backend = _make_backend()
        backend.playlist = [MagicMock()]
        backend.playlist_index = 0
        backend._on_song_finished()
        assert backend.state == BackendState.IDLE

    def test_on_song_finished_emits_event(self):
        backend = _make_backend()
        cb = MagicMock()
        backend.set_event_callback(cb)
        backend.playlist = [MagicMock()]
        backend.playlist_index = 0
        backend._on_song_finished()
        assert any(
            call.args[0].get("type") == "song_finished"
            for call in cb.call_args_list
        )


# ---------- Lazy % logging (lines 139, 153, 172, 180, 319, etc.) ----------

class TestLazyLogging:
    """Verify logger.error / logger.debug use lazy formatting (no f-strings)."""

    def test_handle_command_logs_debug(self):
        backend = _make_backend()
        with patch("pykaraoke.core.backend.logger") as mock_logger:
            backend.handle_command({"action": "get_state"})
            mock_logger.debug.assert_called()
            # Check first positional arg is a format string, not an f-string
            call_args = mock_logger.debug.call_args
            assert "%s" in call_args[0][0]

    def test_error_command_logs_with_lazy_format(self):
        backend = _make_backend()
        backend._command_handlers["fail"] = MagicMock(
            side_effect=RuntimeError("fail msg")
        )
        with patch("pykaraoke.core.backend.logger") as mock_logger:
            backend.handle_command({"action": "fail"})
            mock_logger.error.assert_called()
            call_args = mock_logger.error.call_args
            assert "%s" in call_args[0][0]


# ---------- main() port parsing error path (line 769) ----------

class TestMainPortParsing:
    """Covers the invalid PYKARAOKE_API_PORT env var path in main()."""

    def test_invalid_port_env_var(self):
        """PYKARAOKE_API_PORT='abc' → ValueError caught, uses default 8080."""
        from pykaraoke.core import backend as backend_module

        with patch.dict(os.environ, {"PYKARAOKE_API_PORT": "abc"}):
            with patch("pykaraoke.core.backend.logger") as mock_logger:
                with patch("sys.argv", ["backend", "--mode", "stdio"]):
                    with patch.object(backend_module, "create_stdio_server"):
                        backend_module.main()
                        # The warning about invalid port should have been logged
                        mock_logger.warning.assert_any_call(
                            "Invalid PYKARAOKE_API_PORT value, using default: %d", 8080
                        )

    def test_valid_port_env_var(self):
        """PYKARAOKE_API_PORT='9090' → uses 9090."""
        from pykaraoke.core import backend as backend_module

        with patch.dict(os.environ, {"PYKARAOKE_API_PORT": "9090"}):
            with patch("sys.argv", ["backend", "--mode", "stdio"]):
                with patch.object(backend_module, "create_stdio_server") as mock_stdio:
                    backend_module.main()
                    mock_stdio.assert_called_once()
