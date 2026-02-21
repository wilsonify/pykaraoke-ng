"""
Comprehensive tests for pykaraoke.core.player module.

Tests the base pykPlayer class with pygame mocked to allow headless testing.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

mock_pygame = install_pygame_mock()

from pykaraoke.config.constants import (
    STATE_INIT,
    STATE_NOT_PLAYING,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_CLOSING,
    STATE_CLOSED,
)


def _make_player(song_filepath="test_song.cdg", error_cb=None, done_cb=None, window_title=None):
    """Create a pykPlayer with manager.options pre-set to avoid SetupOptions call."""
    from pykaraoke.core.manager import manager

    # Pre-set options so pykPlayer.__init__ skips SetupOptions/parse_args
    if manager.options is None:
        opts = MagicMock()
        opts.dump = None
        opts.nomusic = False
        opts.size_x = 640
        opts.size_y = 480
        opts.hide_mouse = False
        manager.options = opts

    # Create a mock songDb
    mock_db = MagicMock()
    mock_settings = MagicMock()
    mock_settings.CdgExtensions = [".cdg"]
    mock_settings.KarExtensions = [".kar", ".mid"]
    mock_settings.MpgExtensions = [".mpg", ".mpeg"]
    mock_settings.CdgDeriveSongInformation = False
    mock_settings.FilesystemCoding = "utf-8"
    mock_settings.ZipfileCoding = "cp1252"
    mock_db.Settings = mock_settings

    # Create a mock song object
    mock_song = MagicMock()
    mock_song.Filepath = song_filepath
    mock_song.DisplayFilename = song_filepath
    mock_song.GetSongDatas.return_value = []
    mock_db.makeSongStruct.return_value = mock_song

    from pykaraoke.core.player import pykPlayer
    return pykPlayer(
        song_filepath,
        mock_db,
        errorNotifyCallback=error_cb,
        doneCallback=done_cb,
        windowTitle=window_title,
    )


class TestPykPlayerInit:
    def test_player_has_song(self):
        player = _make_player()
        assert hasattr(player, "Song")
        assert player.Song is not None

    def test_player_has_error_callback(self):
        err_cb = MagicMock()
        player = _make_player(error_cb=err_cb)
        assert player.ErrorNotifyCallback == err_cb

    def test_player_has_done_callback(self):
        done_cb = MagicMock()
        player = _make_player(done_cb=done_cb)
        assert player.SongFinishedCallback == done_cb

    def test_player_initial_state(self):
        player = _make_player()
        assert player.State == STATE_INIT

    def test_player_has_window_title(self):
        player = _make_player(window_title="My Song")
        assert player.WindowTitle == "My Song"

    def test_player_default_window_title(self):
        player = _make_player()
        assert hasattr(player, "WindowTitle")

    def test_player_play_time_zero(self):
        player = _make_player()
        assert player.PlayTime == 0

    def test_player_play_frame_zero(self):
        player = _make_player()
        assert player.PlayFrame == 0

    def test_player_internal_offset_time(self):
        player = _make_player()
        assert player.InternalOffsetTime == 0

    def test_player_supports_font_zoom_default(self):
        player = _make_player()
        assert player.SupportsFontZoom is False


class TestPykPlayerState:
    def test_close_sets_closing(self):
        player = _make_player()
        player.Close()
        assert player.State == STATE_CLOSING

    def test_shutdown_from_playing(self):
        player = _make_player()
        player.State = STATE_PLAYING
        player.shutdown()
        assert player.State == STATE_CLOSED

    def test_shutdown_calls_done_callback(self):
        cb = MagicMock()
        player = _make_player(done_cb=cb)
        player.State = STATE_PLAYING
        player.shutdown()
        cb.assert_called_once()

    def test_shutdown_no_callback(self):
        player = _make_player()
        player.State = STATE_PLAYING
        player.shutdown()
        assert player.State == STATE_CLOSED

    def test_shutdown_idempotent(self):
        player = _make_player()
        player.State = STATE_CLOSED
        player.shutdown()
        assert player.State == STATE_CLOSED


class TestPykPlayerMethods:
    def test_pause_from_playing(self):
        player = _make_player()
        player.State = STATE_PLAYING
        player.Pause()
        assert player.State == STATE_PAUSED

    def test_unpause(self):
        player = _make_player()
        player.State = STATE_PAUSED
        player.PlayTime = 1000
        player.Pause()
        assert player.State == STATE_PLAYING

    def test_validate_returns_true(self):
        player = _make_player()
        result = player.Validate()
        assert result is True

    def test_do_resize(self):
        player = _make_player()
        player.doResize((800, 600))

    def test_do_resize_begin(self):
        player = _make_player()
        player.doResizeBegin()

    def test_do_resize_end(self):
        player = _make_player()
        player.doResizeEnd()

    def test_rewind(self):
        player = _make_player()
        player.State = STATE_PLAYING
        player.PlayTime = 5000
        player.Rewind()
        assert player.PlayTime == 0
        assert player.State == STATE_NOT_PLAYING

    def test_stop(self):
        player = _make_player()
        player.State = STATE_PLAYING
        player.Stop()
        assert player.State == STATE_NOT_PLAYING

    def test_get_pos_not_playing(self):
        player = _make_player()
        player.State = STATE_NOT_PLAYING
        player.PlayTime = 2000
        assert player.GetPos() == 2000

    def test_get_length_returns_none(self):
        player = _make_player()
        result = player.GetLength()
        assert result is None

    def test_do_stuff_increments_frame(self):
        player = _make_player()
        player.State = STATE_PLAYING
        player.doStuff()
        assert player.PlayFrame == 1

    def test_handle_event_quit(self):
        player = _make_player()
        event = MagicMock()
        event.type = mock_pygame.QUIT
        player.handleEvent(event)
        assert player.State == STATE_CLOSING


class TestPykPlayerSongData:
    def test_player_has_song_datas(self):
        player = _make_player()
        assert hasattr(player, "SongDatas")

    def test_player_song_db(self):
        player = _make_player()
        assert hasattr(player, "songDb")
        assert player.songDb is not None
