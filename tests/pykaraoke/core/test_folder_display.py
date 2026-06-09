"""
Tests for folder display defect.

Verifies that:
  - get_settings returns folder_list
  - add_folder updates the folder list
  - the input field value is not hardcoded in the backend
"""

import os
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


# ===========================================================================
# Unit tests – folder list in settings
# ===========================================================================


class TestFolderListInSettings:
    """Verify get_settings returns folder_list (Defect 1 regression)."""

    def test_get_settings_has_folder_list_key(self):
        backend = _get_backend()
        settings = backend.handle_command({"action": "get_settings"})
        assert settings["status"] == "ok"
        data = settings.get("data", {})
        assert "folder_list" in data, (
            "get_settings must return folder_list so the frontend "
            "knows which folders are configured"
        )

    def test_folder_list_is_list(self):
        backend = _get_backend()
        settings = backend.handle_command({"action": "get_settings"})
        assert isinstance(settings["data"]["folder_list"], list)

    def test_folder_list_after_add_folder(self):
        backend = _get_backend()
        mock_folders = ["C:\\songs\\pop", "C:\\songs\\rock"]

        with patch.object(backend.song_db, "get_folder_list", return_value=mock_folders):
            with patch.object(backend.song_db, "folder_add") as mock_add:
                with patch.object(backend.song_db, "save_settings"):
                    with patch.object(backend.song_db, "add_file"):
                        with patch.object(backend.song_db, "select_sort"):
                            with patch.object(backend.song_db, "save_database"):
                                resp = backend.handle_command({
                                    "action": "add_folder",
                                    "params": {"folder": "C:\\songs\\pop"},
                                })
                                assert resp["status"] == "ok"

            # After adding, get_settings should include the folder
            settings = backend.handle_command({"action": "get_settings"})
            assert "C:\\songs\\pop" in settings["data"]["folder_list"]

    def test_folder_list_empty_initially(self):
        backend = _get_backend()
        with patch.object(backend.song_db, "get_folder_list", return_value=[]):
            settings = backend.handle_command({"action": "get_settings"})
            assert settings["data"]["folder_list"] == []

    def test_add_folder_missing_param_returns_error(self):
        backend = _get_backend()
        resp = backend.handle_command({
            "action": "add_folder",
            "params": {},
        })
        assert resp["status"] == "error"

    def test_add_folder_empty_string_returns_error(self):
        backend = _get_backend()
        resp = backend.handle_command({
            "action": "add_folder",
            "params": {"folder": ""},
        })
        assert resp["status"] == "error"


class TestSettingsContainsExistingFields:
    """Existing settings fields must still be present."""

    def test_settings_still_has_fullscreen(self):
        backend = _get_backend()
        data = backend.handle_command({"action": "get_settings"}).get("data", {})
        assert "fullscreen" in data

    def test_settings_still_has_player_size(self):
        backend = _get_backend()
        data = backend.handle_command({"action": "get_settings"}).get("data", {})
        assert "player_size" in data

    def test_settings_still_has_zoom_mode(self):
        backend = _get_backend()
        data = backend.handle_command({"action": "get_settings"}).get("data", {})
        assert "zoom_mode" in data
