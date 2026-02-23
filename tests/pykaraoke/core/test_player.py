"""
Comprehensive tests for pykaraoke.core.player module.

Tests the base PykPlayer class with pygame mocked to allow headless testing.
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
    """Create a PykPlayer with manager.options pre-set to avoid setup_options call."""
    from pykaraoke.core.manager import manager

    # Pre-set options so PykPlayer.__init__ skips setup_options/parse_args
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
    mock_settings.cdg_extensions = [".cdg"]
    mock_settings.kar_extensions = [".kar", ".mid"]
    mock_settings.mpg_extensions = [".mpg", ".mpeg"]
    mock_settings.cdg_derive_song_information = False
    mock_settings.filesystem_coding = "utf-8"
    mock_settings.zipfile_coding = "cp1252"
    mock_db.settings = mock_settings

    # Create a mock song object
    mock_song = MagicMock()
    mock_song.filepath = song_filepath
    mock_song.display_filename = song_filepath
    mock_song.get_song_datas.return_value = []
    mock_db.makeSongStruct.return_value = mock_song

    from pykaraoke.core.player import PykPlayer
    return PykPlayer(
        song_filepath,
        mock_db,
        error_notify_callback=error_cb,
        done_callback=done_cb,
        window_title=window_title,
    )


class TestPykPlayerInit:
    def test_player_has_song(self):
        player = _make_player()
        assert hasattr(player, "song")
        assert player.song is not None

    def test_player_has_error_callback(self):
        err_cb = MagicMock()
        player = _make_player(error_cb=err_cb)
        assert player.error_notify_callback == err_cb

    def test_player_has_done_callback(self):
        done_cb = MagicMock()
        player = _make_player(done_cb=done_cb)
        assert player.song_finished_callback == done_cb

    def test_player_initial_state(self):
        player = _make_player()
        assert player.state == STATE_INIT

    def test_player_has_window_title(self):
        player = _make_player(window_title="My Song")
        assert player.window_title == "My Song"

    def test_player_default_window_title(self):
        player = _make_player()
        assert hasattr(player, "window_title")

    def test_player_play_time_zero(self):
        player = _make_player()
        assert player.play_time == 0

    def test_player_play_frame_zero(self):
        player = _make_player()
        assert player.play_frame == 0

    def test_player_internal_offset_time(self):
        player = _make_player()
        assert player.internal_offset_time == 0

    def test_player_supports_font_zoom_default(self):
        player = _make_player()
        assert player.supports_font_zoom is False


class TestPykPlayerState:
    def test_close_sets_closing(self):
        player = _make_player()
        player.close()
        assert player.state == STATE_CLOSING

    def test_shutdown_from_playing(self):
        player = _make_player()
        player.state = STATE_PLAYING
        player.shutdown()
        assert player.state == STATE_CLOSED

    def test_shutdown_calls_done_callback(self):
        cb = MagicMock()
        player = _make_player(done_cb=cb)
        player.state = STATE_PLAYING
        player.shutdown()
        cb.assert_called_once()

    def test_shutdown_no_callback(self):
        player = _make_player()
        player.state = STATE_PLAYING
        player.shutdown()
        assert player.state == STATE_CLOSED

    def test_shutdown_idempotent(self):
        player = _make_player()
        player.state = STATE_CLOSED
        player.shutdown()
        assert player.state == STATE_CLOSED


class TestPykPlayerMethods:
    def test_pause_from_playing(self):
        player = _make_player()
        player.state = STATE_PLAYING
        player.pause()
        assert player.state == STATE_PAUSED

    def test_unpause(self):
        player = _make_player()
        player.state = STATE_PAUSED
        player.play_time = 1000
        player.pause()
        assert player.state == STATE_PLAYING

    def test_validate_returns_true(self):
        player = _make_player()
        result = player.validate()
        assert result is True

    def test_do_resize(self):
        player = _make_player()
        player.do_resize((800, 600))

    def test_do_resize_begin(self):
        player = _make_player()
        player.do_resize_begin()

    def test_do_resize_end(self):
        player = _make_player()
        player.do_resize_end()

    def test_rewind(self):
        player = _make_player()
        player.state = STATE_PLAYING
        player.play_time = 5000
        player.rewind()
        assert player.play_time == 0
        assert player.state == STATE_NOT_PLAYING

    def test_stop(self):
        player = _make_player()
        player.state = STATE_PLAYING
        player.stop()
        assert player.state == STATE_NOT_PLAYING

    def test_get_pos_not_playing(self):
        player = _make_player()
        player.state = STATE_NOT_PLAYING
        player.play_time = 2000
        assert player.get_pos() == 2000

    def test_get_length_returns_none(self):
        player = _make_player()
        result = player.get_length()
        assert result is None

    def test_do_stuff_increments_frame(self):
        player = _make_player()
        player.state = STATE_PLAYING
        player.do_stuff()
        assert player.play_frame == 1

    def test_handle_event_quit(self):
        player = _make_player()
        event = MagicMock()
        event.type = mock_pygame.QUIT
        player.handle_event(event)
        assert player.state == STATE_CLOSING


class TestPykPlayerSongData:
    def test_player_has_song_datas(self):
        player = _make_player()
        assert hasattr(player, "song_datas")

    def test_player_song_db(self):
        player = _make_player()
        assert hasattr(player, "song_db")
        assert player.song_db is not None
