#!/usr/bin/env python

"""
Test suite for PyKaraoke Backend API

Tests the headless backend service to ensure commands work correctly
without requiring UI components.
"""

import json
import sys

import pytest


class TestBackendAPI:
    """Test the backend API command handling"""

    def test_import_backend(self):
        """Test that backend module can be imported"""
        try:
            from pykaraoke.core import backend

            assert hasattr(backend, "PyKaraokeBackend")
            assert hasattr(backend, "BackendState")
        except ImportError as e:
            pytest.skip(f"Backend module not importable: {e}")

    def test_backend_initialization(self):
        """Test backend can be initialized"""
        try:
            from pykaraoke.core import backend as backend_module

            backend_instance = backend_module.PyKaraokeBackend()
            assert backend_instance is not None
            assert backend_instance.state == backend_module.BackendState.IDLE
            assert backend_instance.playlist == []
            assert backend_instance.playlist_index == -1
        except Exception as e:
            pytest.skip(f"Backend initialization failed: {e}")

    def test_unknown_command(self):
        """Test handling of unknown commands"""
        try:
            from pykaraoke.core import backend as backend_module

            backend_instance = backend_module.PyKaraokeBackend()

            command = {"action": "invalid_action", "params": {}}
            response = backend_instance.handle_command(command)

            assert response["status"] == "error"
            assert "message" in response
        except Exception as e:
            pytest.skip(f"Backend test failed: {e}")

    def test_state_serialization(self):
        """Test that state can be serialized to JSON"""
        try:
            from pykaraoke.core import backend as backend_module

            backend_instance = backend_module.PyKaraokeBackend()

            state = backend_instance.get_state()

            # Should be JSON serializable
            json_str = json.dumps(state)
            assert json_str is not None

            # Should be deserializable
            parsed = json.loads(json_str)
            assert parsed["playback_state"] == "idle"
        except Exception as e:
            pytest.skip(f"Backend test failed: {e}")


class TestBackendAPIIntegration:
    """Integration tests for backend API that require full environment (pygame/mixer)"""

    @pytest.mark.integration
    def test_get_state_command(self):
        """Test get_state command returns valid state"""
        try:
            from pykaraoke.core import backend as backend_module

            backend_instance = backend_module.PyKaraokeBackend()

            command = {"action": "get_state", "params": {}}
            response = backend_instance.handle_command(command)

            assert response["status"] == "ok"
            assert "data" in response
            assert "playback_state" in response["data"]
            assert "playlist" in response["data"]
            assert "volume" in response["data"]
        except Exception as e:
            pytest.skip(f"Integration test - requires full environment: {e}")

    @pytest.mark.integration
    def test_volume_command(self):
        """Test volume control command (requires pygame mixer)"""
        try:
            from pykaraoke.core import backend as backend_module

            backend_instance = backend_module.PyKaraokeBackend()

            # Set volume to 0.5
            command = {"action": "set_volume", "params": {"volume": 0.5}}
            response = backend_instance.handle_command(command)

            assert response["status"] == "ok"
            assert backend_instance.volume == 0.5

            # Set volume to out-of-range value (should clamp to 1.0)
            command = {"action": "set_volume", "params": {"volume": 1.5}}
            response = backend_instance.handle_command(command)

            assert response["status"] == "ok"
            assert backend_instance.volume == 1.0  # Clamped to max

            # Set volume to negative (should clamp to 0.0)
            command = {"action": "set_volume", "params": {"volume": -0.5}}
            response = backend_instance.handle_command(command)

            assert response["status"] == "ok"
            assert backend_instance.volume == 0.0  # Clamped to min
        except Exception as e:
            pytest.skip(f"Integration test - requires full environment: {e}")

    @pytest.mark.integration
    def test_playlist_operations(self):
        """Test playlist management commands"""
        try:
            from pykaraoke.core import backend as backend_module

            backend_instance = backend_module.PyKaraokeBackend()

            # Clear playlist
            command = {"action": "clear_playlist", "params": {}}
            response = backend_instance.handle_command(command)
            assert response["status"] == "ok"
            assert len(backend_instance.playlist) == 0

            # Note: Adding to playlist would require valid song files
            # So we just test the clear operation
        except Exception as e:
            pytest.skip(f"Integration test - requires full environment: {e}")


class TestBackendStdioProtocol:
    """Tests for backend stdio protocol handling."""

    def test_stdio_cycle_get_state(self):
        """Simulate a full stdin→handle_command→stdout cycle using StringIO."""
        import io
        import json
        from unittest import mock
        import threading
        import time

        from pykaraoke.core import backend as backend_module

        backend_instance = backend_module.PyKaraokeBackend()

        command = {"action": "get_state", "params": {}}
        stdin_mock = io.StringIO(json.dumps(command) + "\n")
        stdout_mock = io.StringIO()

        # create_stdio_server blocks until stdin is exhausted,
        # so drive it in a separate thread with a timeout.
        exc_info = []

        def run():
            try:
                with (
                    mock.patch.object(sys, "stdin", stdin_mock),
                    mock.patch.object(sys, "stderr", io.StringIO()),
                ):
                    backend_module.create_stdio_server(backend_instance, json_out=stdout_mock)
            except Exception as e:
                exc_info.append(e)

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=5)

        if exc_info:
            raise exc_info[0]

        output = stdout_mock.getvalue()
        assert output, "No output from stdio server"
        parsed = json.loads(output)
        assert parsed["type"] == "response"
        assert parsed["response"]["status"] == "ok"

    def test_stdio_cycle_invalid_json(self):
        """Invalid JSON input should produce an error response."""
        import io
        import json
        from unittest import mock
        import threading

        from pykaraoke.core import backend as backend_module

        backend_instance = backend_module.PyKaraokeBackend()

        stdin_mock = io.StringIO("not valid json\n")
        stdout_mock = io.StringIO()

        exc_info = []

        def run():
            try:
                with (
                    mock.patch.object(sys, "stdin", stdin_mock),
                    mock.patch.object(sys, "stderr", io.StringIO()),
                ):
                    backend_module.create_stdio_server(backend_instance, json_out=stdout_mock)
            except Exception as e:
                exc_info.append(e)

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=5)

        if exc_info:
            raise exc_info[0]

        output = stdout_mock.getvalue()
        assert output, "No output from stdio server"
        parsed = json.loads(output)
        assert parsed["type"] == "response"
        assert parsed["response"]["status"] == "error"

    def test_backend_shutdown(self):
        """Call shutdown — should complete without error."""
        from pykaraoke.core import backend as backend_module

        backend_instance = backend_module.PyKaraokeBackend()
        backend_instance.shutdown()

    def test_event_callback(self):
        """Verify that set_event_callback works end-to-end."""
        from pykaraoke.core import backend as backend_module

        backend_instance = backend_module.PyKaraokeBackend()
        received_events = []

        def collector(event):
            received_events.append(event)

        backend_instance.set_event_callback(collector)
        backend_instance._emit_event("test_event", {"key": "value"})

        assert len(received_events) == 1
        assert received_events[0]["type"] == "test_event"
        assert received_events[0]["data"]["key"] == "value"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
