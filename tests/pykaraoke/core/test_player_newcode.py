"""
Targeted tests for player.py new/changed code lines.

Covers:
- Import of STATE_CAPTURING (line 34)
- Import of GP2X_BUTTON_* constants (lines 31-36)
- doStuff with STATE_CAPTURING check
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()


class TestPlayerImports:
    """Verify the new imports are accessible in player module."""

    def test_state_capturing_imported(self):
        from pykaraoke.config.constants import STATE_CAPTURING
        assert STATE_CAPTURING is not None

    def test_gp2x_button_select_imported(self):
        from pykaraoke.config.constants import GP2X_BUTTON_SELECT
        assert GP2X_BUTTON_SELECT is not None

    def test_gp2x_button_start_imported(self):
        from pykaraoke.config.constants import GP2X_BUTTON_START
        assert GP2X_BUTTON_START is not None

    def test_gp2x_button_l_imported(self):
        from pykaraoke.config.constants import GP2X_BUTTON_L
        assert GP2X_BUTTON_L is not None

    def test_gp2x_button_r_imported(self):
        from pykaraoke.config.constants import GP2X_BUTTON_R
        assert GP2X_BUTTON_R is not None

    def test_gp2x_button_left_imported(self):
        from pykaraoke.config.constants import GP2X_BUTTON_LEFT
        assert GP2X_BUTTON_LEFT is not None

    def test_gp2x_button_right_imported(self):
        from pykaraoke.config.constants import GP2X_BUTTON_RIGHT
        assert GP2X_BUTTON_RIGHT is not None

    def test_player_module_imports_state_capturing(self):
        """player.py should import STATE_CAPTURING without error."""
        from pykaraoke.core import player
        assert hasattr(player, "STATE_CAPTURING")

    def test_player_module_imports_gp2x_buttons(self):
        """player.py should import GP2X_BUTTON_* without error."""
        from pykaraoke.core import player
        assert hasattr(player, "GP2X_BUTTON_SELECT")
        assert hasattr(player, "GP2X_BUTTON_START")


class TestPlayerDoStuffCapturingState:
    """Test doStuff behavior when state is STATE_CAPTURING."""

    def _make_player(self):
        from pykaraoke.core.manager import manager
        from pykaraoke.core import player

        # Pre-set options on the singleton to skip setup_options/parse_args
        if manager.options is None:
            opts = MagicMock()
            opts.dump = None
            opts.nomusic = False
            opts.size_x = 640
            opts.size_y = 480
            opts.hide_mouse = False
            manager.options = opts

        mock_song_db = MagicMock()
        mock_song_db.settings = MagicMock()
        mock_song_db.settings.cdg_derive_song_information = False
        mock_song = MagicMock()
        mock_song.type = 1
        mock_song.zip_stored_name = None
        mock_song.filepath = "test.cdg"
        mock_song.display_filename = "test.cdg"
        mock_song.get_song_datas.return_value = []

        p = player.PykPlayer(mock_song, mock_song_db, MagicMock(), MagicMock())
        return p

    def test_do_stuff_with_capturing_state(self):
        from pykaraoke.config.constants import STATE_CAPTURING
        p = self._make_player()
        p.State = STATE_CAPTURING
        p.do_frame_dump = MagicMock()
        p.dump_frame_rate = 30.0
        p.PlayFrame = 0
        p.play_time = 0.0
        result = p.do_stuff()


class TestPlayerAdditionalCoverage:
    """Additional player tests to cover more lines."""

    def _make_player(self):
        from pykaraoke.core.manager import manager
        from pykaraoke.core import player

        if manager.options is None:
            opts = MagicMock()
            opts.dump = None
            opts.nomusic = False
            opts.size_x = 640
            opts.size_y = 480
            opts.hide_mouse = False
            manager.options = opts

        mock_song_db = MagicMock()
        mock_song_db.settings = MagicMock()
        mock_song_db.settings.cdg_derive_song_information = False
        mock_song = MagicMock()
        mock_song.type = 1
        mock_song.zip_stored_name = None
        mock_song.filepath = "test.cdg"
        mock_song.display_filename = "test.cdg"
        mock_song.get_song_datas.return_value = []

        p = player.PykPlayer(mock_song, mock_song_db, MagicMock(), MagicMock())
        return p

    def test_player_pause_unpause(self):
        from pykaraoke.config.constants import STATE_PLAYING, STATE_PAUSED
        p = self._make_player()
        p.doPause = MagicMock()
        p.doUnpause = MagicMock()
        p.State = STATE_PLAYING
        p.play_start_time = 0
        p.pause()
        assert p.State == STATE_PAUSED
        p.pause()
        assert p.State == STATE_PLAYING

    def test_player_get_pos_default(self):
        p = self._make_player()
        pos = p.get_pos()
        assert isinstance(pos, (int, float))

    def test_player_close(self):
        from pykaraoke.config.constants import STATE_CLOSING
        p = self._make_player()
        p.close()
        assert p.State == STATE_CLOSING

    def test_player_shutdown(self):
        from pykaraoke.config.constants import STATE_CLOSED
        p = self._make_player()
        p.shutdown()
        assert p.State == STATE_CLOSED

    def test_player_stop(self):
        p = self._make_player()
        p.stop()  # Should not raise

    def test_player_rewind(self):
        p = self._make_player()
        p.rewind()  # Should not raise

    def test_player_get_length(self):
        p = self._make_player()
        length = p.get_length()
        # Base implementation returns None and notifies error
        assert length is None

    def test_player_validate(self):
        p = self._make_player()
        p.validate()  # Should not raise

    def test_player_resize(self):
        p = self._make_player()
        p.do_resize((800, 600))  # Should not raise
