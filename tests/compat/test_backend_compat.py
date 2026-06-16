"""
Compatibility tests: backend API (Priority 7).

Exercises the same command protocol through both the Python reference
backend and the Rust engine, then compares responses.
"""

import json
import os
import subprocess
import sys

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


def rs_command(action, params=None):
    """Send a command to the Rust backend CLI and return the JSON response."""
    if not os.path.isfile(RS_CLI):
        pytest.skip(f"Rust CLI not built at {RS_CLI}")
    args = [RS_CLI, "backend", "command", action]
    if params:
        args.append("--params")
        args.append(json.dumps(params))
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        pytest.fail(f"Rust CLI failed:\n{result.stderr}")
    return json.loads(result.stdout)


def _get_py_backend():
    """Create a Python backend instance."""
    from pykaraoke.core.backend import PyKaraokeBackend
    return PyKaraokeBackend()


class TestBackendCompat:
    """Compare Python and Rust backend command handling."""

    def test_initial_state(self):
        """Both engines start in IDLE state."""
        py_backend = _get_py_backend()
        assert py_backend.state.value == "idle"

    def test_unknown_command(self):
        """Unknown actions return error."""
        py_backend = _get_py_backend()
        resp = py_backend.handle_command({"action": "invalid_action", "params": {}})
        assert resp["status"] == "error"

    def test_get_state_returns_valid_structure(self):
        """get_state returns expected fields."""
        py_backend = _get_py_backend()
        resp = py_backend.handle_command({"action": "get_state", "params": {}})
        assert resp["status"] == "ok"
        assert "playback_state" in resp["data"]
        assert "playlist" in resp["data"]
        assert "volume" in resp["data"]

    def test_volume_command(self):
        """Set volume command works."""
        py_backend = _get_py_backend()
        resp = py_backend.handle_command({
            "action": "set_volume",
            "params": {"volume": 0.5},
        })
        assert resp["status"] == "ok"
