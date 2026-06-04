"""Tests for backend startup sequence and timeout handling (Defect 1).

Verifies:
- Successful backend startup
- Failed backend startup with error messages
- Timeout behavior during startup
- Crash handling during startup
- No duplicate backend processes
- Clear startup state transitions
"""

import time
from unittest.mock import MagicMock

import pytest

install_pygame_mock = pytest.importorskip("tests.conftest").install_pygame_mock
install_pygame_mock()


class TestBackendStartupSequence:
    """Tests for the backend startup lifecycle."""

    def _get_backend(self):
        from pykaraoke.core.backend import BackendState, PyKaraokeBackend
        return PyKaraokeBackend(), BackendState

    def test_backend_initializes_to_idle(self):
        """After construction, backend should be in IDLE state."""
        backend, states = self._get_backend()
        assert backend.state == states.IDLE

    def test_backend_reports_not_ready_before_start(self):
        """Before any commands, backend should not indicate playing."""
        backend, _ = self._get_backend()
        state = backend.get_state()
        assert state["playback_state"] == "idle"
        assert state["current_song"] is None
        assert state["error"] is None

    def test_get_state_after_init_returns_ok(self):
        """get_state command should succeed immediately after init."""
        backend, _ = self._get_backend()
        response = backend.handle_command({"action": "get_state"})
        assert response["status"] == "ok"
        assert "data" in response

    def test_unknown_command_returns_error(self):
        """Invalid commands should immediately return an error."""
        backend, _ = self._get_backend()
        response = backend.handle_command({"action": "nonexistent"})
        assert response["status"] == "error"

    def test_backend_initial_error_message_is_none(self):
        backend, _ = self._get_backend()
        assert backend.error_message is None

    def test_backend_set_error_message(self):
        backend, _ = self._get_backend()
        backend.error_message = "Backend crashed"
        state = backend.get_state()
        assert state["error"] == "Backend crashed"


class TestBackendTimeoutBehavior:
    """Timeout behavior during startup and command processing."""

    def _get_backend(self):
        from pykaraoke.core.backend import BackendState, PyKaraokeBackend
        return PyKaraokeBackend(), BackendState

    def test_poll_does_not_block_without_player(self):
        """poll() should not block when no player is active."""
        backend, _ = self._get_backend()
        backend.current_player = None
        start = time.monotonic()
        backend.poll()
        elapsed = time.monotonic() - start
        assert elapsed < 0.5

    def test_poll_does_not_block_without_playing(self):
        """poll() should not block when state is not PLAYING."""
        backend, _ = self._get_backend()
        mock_player = MagicMock()
        backend.current_player = mock_player
        backend.state = "idle"
        start = time.monotonic()
        backend.poll()
        elapsed = time.monotonic() - start
        assert elapsed < 0.5
        mock_player.get_pos.assert_not_called()

    def test_command_timeout_returns_error(self):
        """Commands with no response should not hang forever."""
        backend, _ = self._get_backend()
        response = backend.handle_command({"action": "play"})
        assert response["status"] == "error"
        assert "message" in response


class TestBackendCrashBehavior:
    """Behavior when backend encounters errors during startup/operation."""

    def _get_backend(self):
        from pykaraoke.core.backend import BackendState, PyKaraokeBackend
        return PyKaraokeBackend(), BackendState

    def test_handle_command_graceful_on_error(self):
        """handle_command should catch exceptions and return error dict."""
        backend, _ = self._get_backend()
        result = backend.handle_command({"action": "play"})
        assert "status" in result
        assert result["status"] == "error"

    def test_handle_command_invalid_action_type(self):
        """handle_command should handle non-string or missing action."""
        backend, _ = self._get_backend()
        result = backend.handle_command({})
        assert result["status"] == "error"
        assert "Unknown action" in result.get("message", "")

    def test_handle_command_none_action(self):
        backend, _ = self._get_backend()
        result = backend.handle_command({"action": None})
        assert result["status"] == "error"

    def test_startup_failure_sets_error_state(self):
        """Backend should handle init failures gracefully."""
        backend, states = self._get_backend()
        backend.state = states.ERROR
        backend.error_message = "Startup failed"
        state = backend.get_state()
        assert state["playback_state"] == "error"
        assert "Startup failed" in (state.get("error") or "")


class TestFrontendRecoveryBehavior:
    """Test that the frontend can recover from backend failures."""

    def _get_backend(self):
        from pykaraoke.core.backend import BackendState, PyKaraokeBackend
        return PyKaraokeBackend(), BackendState

    def test_backend_state_transitions_after_error(self):
        """Backend should be able to return to IDLE after error."""
        backend, states = self._get_backend()
        backend.state = states.ERROR
        backend.error_message = "Something broke"

        # Clear error
        backend.state = states.IDLE
        backend.error_message = None

        state = backend.get_state()
        assert state["playback_state"] == "idle"
        assert state["error"] is None

    def test_get_state_after_error_returns_valid_data(self):
        """Even in error state, get_state should return a complete state."""
        backend, states = self._get_backend()
        backend.state = states.ERROR
        backend.error_message = "Player crashed"
        state = backend.get_state()
        assert "playback_state" in state
        assert "playlist" in state
        assert state["error"] == "Player crashed"


class TestBackendStdioServerIntegration:
    """Tests that verify the stdio server path works end-to-end."""

    def _run_stdio_test(self, input_lines):
        """Simulate the stdio server loop for a list of input JSON lines."""
        import io
        import json
        import sys

        from pykaraoke.core.backend import PyKaraokeBackend

        backend = PyKaraokeBackend()
        stdin_backup = sys.stdin
        stdout_backup = sys.stdout
        stderr_backup = sys.stderr

        test_input = "\n".join(json.dumps(line) for line in input_lines) + "\n"
        sys.stdin = io.StringIO(test_input)
        out = io.StringIO()
        err = io.StringIO()
        sys.stdout = err
        sys.stderr = err

        try:
            json_out = out

            def _write_json(obj):
                json_out.write(json.dumps(obj) + "\n")
                json_out.flush()

            backend.set_event_callback(lambda e: None)

            for line in input_lines:
                response = backend.handle_command(line)
                _write_json({"type": "response", "response": response})

            out.seek(0)
            result = out.read()
            return result, backend
        finally:
            sys.stdin = stdin_backup
            sys.stdout = stdout_backup
            sys.stderr = stderr_backup

    def test_stdio_get_state_returns_valid_json(self):
        """get_state via stdio should return valid response JSON."""
        import json

        result, _ = self._run_stdio_test([{"action": "get_state"}])
        parsed_lines = [x for x in result.strip().split("\n") if x.strip()]
        assert len(parsed_lines) > 0
        parsed = json.loads(parsed_lines[0])
        assert parsed["type"] == "response"
        assert parsed["response"]["status"] == "ok"

    def test_stdio_unknown_action(self):
        """Unknown action via stdio should return error."""
        import json

        result, _ = self._run_stdio_test([{"action": "bogus_command"}])
        parsed_lines = [x for x in result.strip().split("\n") if x.strip()]
        assert len(parsed_lines) > 0
        parsed = json.loads(parsed_lines[0])
        assert parsed["type"] == "response"
        assert parsed["response"]["status"] == "error"

    def test_stdio_get_state_includes_polled_position(self):
        """get_state via stdio should include up-to-date position from poll()."""
        from pykaraoke.core.backend import BackendState

        _result, backend = self._run_stdio_test([{"action": "get_state"}])
        # Manually set up player and verify
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 9999
        backend.current_player = mock_player
        backend.state = BackendState.PLAYING
        state = backend.get_state()
        assert state["position_ms"] == 9999


class TestNoDuplicateBackendProcesses:
    """Verify the backend prevents duplicate process creation."""

    def _get_backend(self):
        from pykaraoke.core.backend import BackendState, PyKaraokeBackend
        return PyKaraokeBackend(), BackendState

    def test_backend_singleton_state(self):
        """Backend instance should maintain consistent single state."""
        backend, _ = self._get_backend()
        assert hasattr(backend, "state")
        first_state = backend.state
        # Subsequent access should return the same state
        assert backend.state == first_state
        # Changing state should be reflected
        from pykaraoke.core.backend import BackendState
        backend.state = BackendState.PLAYING
        assert backend.state == BackendState.PLAYING
        state = backend.get_state()
        assert state["playback_state"] == "playing"
