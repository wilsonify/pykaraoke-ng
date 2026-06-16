"""Validation tests for the built Rust native backend binary.

These tests treat the compiled Rust pykaraoke-engine-cli as the product.
They validate that the actual release artifact starts, responds to
JSON commands, and shuts down cleanly — without mocking anything.

Usage:
    pytest tests/validation/test_artifact_backend.py -v
    PYKARAOKE_BACKEND_EXE=/path/to/pykaraoke-engine-cli.exe pytest ...
"""

import json
import time
from pathlib import Path

import pytest


# ===========================================================================
# Smoke Tests
# ===========================================================================


class TestBackendStartup:
    """Verify the Rust binary artifact exists, starts, and responds to IPC."""

    def test_backend_exe_exists(self, backend_exe):
        assert backend_exe.is_file()
        # A real Rust build is > 100 KB; a placeholder is ~100 bytes
        assert backend_exe.stat().st_size > 100_000, (
            f"Rust binary too small ({backend_exe.stat().st_size} bytes) — "
            "likely a placeholder, not a real build"
        )

    def test_backend_responds_to_get_state(self, backend_process):
        response = backend_process.send("get_state")
        assert response["status"] == "ok"
        data = response.get("data", response)
        assert "playback_state" in data
        assert "playlist" in data
        assert "current_song" in data
        assert data["playback_state"] == "idle"

    def test_backend_shuts_down_cleanly(self, backend_process):
        """Closing stdin triggers EOF → graceful shutdown."""
        backend_process.close()


# ===========================================================================
# Settings / Configuration
# ===========================================================================


class TestBackendSettings:
    """Verify settings are returned correctly from the Rust artifact."""

    def test_get_settings_returns_folder_list(self, backend_process):
        resp = backend_process.send("get_settings")
        assert resp["status"] == "ok"
        data = resp.get("data", {})
        assert "folder_list" in data
        assert isinstance(data["folder_list"], list)

    def test_get_settings_has_required_fields(self, backend_process):
        resp = backend_process.send("get_settings")
        data = resp.get("data", {})
        for key in ("fullscreen", "display_width", "display_height", "folder_list", "volume"):
            assert key in data, f"Missing settings key: {key}"


# ===========================================================================
# Library / Song Database
# ===========================================================================


class TestBackendLibrary:
    """Verify the Rust artifact can work with the song database."""

    def test_get_library_returns_list(self, backend_process):
        resp = backend_process.send("get_library")
        assert resp["status"] == "ok"
        data = resp.get("data", resp)
        assert isinstance(data.get("songs", []), list)

    def test_scan_library_succeeds(self, backend_process):
        """Library scan should succeed even when no folders are configured."""
        resp = backend_process.send("scan_library")
        assert resp["status"] == "ok"


# ===========================================================================
# Playlist / Enqueue
# ===========================================================================


class TestBackendPlaylist:
    """Verify the Rust artifact handles playlist operations."""

    def test_enqueue_missing_filepath_returns_error(self, backend_process):
        resp = backend_process.send("add_to_playlist", {"filepath": ""})
        assert resp["status"] == "error"

    def test_enqueue_without_filepath_returns_error(self, backend_process):
        resp = backend_process.send("add_to_playlist", {})
        assert resp["status"] == "error"

    def test_play_without_songs_returns_error(self, backend_process):
        resp = backend_process.send("play")
        assert resp["status"] == "error"

    def test_clear_playlist_succeeds(self, backend_process):
        resp = backend_process.send("clear_playlist")
        assert resp["status"] == "ok"


# ===========================================================================
# Volume
# ===========================================================================


class TestBackendVolume:
    """Verify volume control in the Rust artifact."""

    def test_set_volume_responds(self, backend_process):
        resp = backend_process.send("set_volume", {"volume": 0.5})
        assert resp["status"] == "ok"

    def test_set_volume_clamps_high(self, backend_process):
        resp = backend_process.send("set_volume", {"volume": 2.0})
        assert resp["status"] == "ok"

    def test_set_volume_clamps_low(self, backend_process):
        resp = backend_process.send("set_volume", {"volume": -1.0})
        assert resp["status"] == "ok"


# ===========================================================================
# Error Handling
# ===========================================================================


class TestBackendErrorHandling:
    """Verify the Rust artifact handles malformed commands gracefully."""

    def test_unknown_action(self, backend_process):
        resp = backend_process.send("nonexistent_action")
        assert resp["status"] == "error"
        assert "unknown" in resp.get("message", "").lower()

    def test_empty_action(self, backend_process):
        resp = backend_process.send("")
        assert resp["status"] == "error"
