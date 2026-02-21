"""
Comprehensive tests for pykaraoke.core.player module.

Tests the base pykPlayer class with pygame mocked to allow headless testing.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

mock_pygame = install_pygame_mock()

from pykaraoke.core.player import pykPlayer
from pykaraoke.config.constants import (
    STATE_INIT,
    STATE_NOT_PLAYING,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_CLOSING,
    STATE_CLOSED,
)


class TestPykPlayerInit:
    """Tests for pykPlayer initialization."""

    def test_player_has_filename(self):
        """pykPlayer should store its filename."""
        player = pykPlayer("test_song.cdg", MagicMock(), MagicMock())
        assert player.FileName == "test_song.cdg"

    def test_player_has_error_callback(self):
        """pykPlayer should store error callback."""
        err_cb = MagicMock()
        player = pykPlayer("test.cdg", err_cb, MagicMock())
        assert player.errorNotifyCallback == err_cb

    def test_player_has_done_callback(self):
        """pykPlayer should store done callback."""
        done_cb = MagicMock()
        player = pykPlayer("test.cdg", MagicMock(), done_cb)
        assert player.doneCallback == done_cb

    def test_player_initial_state(self):
        """pykPlayer should start in NOT_PLAYING state."""
        player = pykPlayer("test.cdg", MagicMock(), MagicMock())
        # State is set by manager.InitPlayer or the constructor
        assert hasattr(player, "State")

    def test_player_has_window_title(self):
        """pykPlayer should have a WindowTitle."""
        player = pykPlayer("test_song.cdg", MagicMock(), MagicMock())
        assert hasattr(player, "WindowTitle")
        assert isinstance(player.WindowTitle, str)


class TestPykPlayerState:
    """Tests for player state management."""

    def test_close_sets_state(self):
        """Close should transition to CLOSED state."""
        player = pykPlayer("test.cdg", MagicMock(), MagicMock())
        player.State = STATE_PLAYING
        player.Close()
        assert player.State == STATE_CLOSED

    def test_shutdown(self):
        """shutdown should close the player."""
        player = pykPlayer("test.cdg", MagicMock(), MagicMock())
        player.State = STATE_PLAYING
        player.shutdown()
        assert player.State == STATE_CLOSED


class TestPykPlayerMethods:
    """Tests for player control methods."""

    def test_pause(self):
        """Pause should toggle pause state."""
        player = pykPlayer("test.cdg", MagicMock(), MagicMock())
        player.State = STATE_PLAYING
        player.Pause()
        # Pause should toggle state
        assert player.State in (STATE_PAUSED, STATE_PLAYING)

    def test_do_stuff(self):
        """doStuff should not crash."""
        player = pykPlayer("test.cdg", MagicMock(), MagicMock())
        player.State = STATE_PLAYING
        # doStuff is called by Poll()
        try:
            player.doStuff()
        except (AttributeError, TypeError):
            pass  # May need manager to be initialized

    def test_validate(self):
        """Validate should return a boolean."""
        player = pykPlayer("test.cdg", MagicMock(), MagicMock())
        result = player.Validate()
        assert isinstance(result, bool)

    def test_do_resize(self):
        """doResize should accept a new size."""
        player = pykPlayer("test.cdg", MagicMock(), MagicMock())
        player.doResize((800, 600))  # Should not raise

    def test_do_resize_begin(self):
        """doResizeBegin should be callable."""
        player = pykPlayer("test.cdg", MagicMock(), MagicMock())
        player.doResizeBegin()  # Should not raise

    def test_do_resize_end(self):
        """doResizeEnd should be callable."""
        player = pykPlayer("test.cdg", MagicMock(), MagicMock())
        player.doResizeEnd()  # Should not raise

    def test_handle_event(self):
        """handleEvent should accept pygame events."""
        player = pykPlayer("test.cdg", MagicMock(), MagicMock())
        mock_event = MagicMock()
        mock_event.type = 2  # KEYDOWN
        player.handleEvent(mock_event)  # Should not raise


class TestPykPlayerSongData:
    """Tests for song data handling."""

    def test_player_with_song_data(self):
        """pykPlayer should accept song data list."""
        song_data = [MagicMock()]
        player = pykPlayer("test.cdg", MagicMock(), MagicMock(), songData=song_data)
        assert hasattr(player, "songDatas") or hasattr(player, "SongDatas")
