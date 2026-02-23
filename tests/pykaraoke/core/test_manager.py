"""
Comprehensive tests for pykaraoke.core.manager module.

Tests the PykManager class with pygame mocked to allow headless testing.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

mock_pygame = install_pygame_mock()

from pykaraoke.core.manager import PykManager, manager


class TestPykManagerInit:
    """Tests for PykManager initialization."""

    def test_manager_exists(self):
        """Global manager instance should exist."""
        assert manager is not None
        assert isinstance(manager, PykManager)

    def test_manager_not_initialized(self):
        """Manager should start uninitialized."""
        mgr = PykManager()
        assert mgr.initialized is False

    def test_manager_no_player(self):
        """Manager should start with no player."""
        mgr = PykManager()
        assert mgr.player is None

    def test_manager_no_display(self):
        """Manager should start with no display."""
        mgr = PykManager()
        assert mgr.display is None

    def test_manager_no_surface(self):
        """Manager should start with no surface."""
        mgr = PykManager()
        assert mgr.surface is None

    def test_manager_display_flags_zero(self):
        """Manager display flags should default to 0."""
        mgr = PykManager()
        assert mgr.display_flags == 0

    def test_manager_display_depth_zero(self):
        """Manager display depth should default to 0."""
        mgr = PykManager()
        assert mgr.display_depth == 0

    def test_manager_has_font_path(self):
        """Manager should have a font path set."""
        mgr = PykManager()
        assert hasattr(mgr, "font_path")
        assert isinstance(mgr.font_path, str)

    def test_manager_has_icon_path(self):
        """Manager should have an icon path set."""
        mgr = PykManager()
        assert hasattr(mgr, "icon_path")
        assert isinstance(mgr.icon_path, str)

    def test_manager_font_scale_none(self):
        """Manager font scale should start as None."""
        mgr = PykManager()
        assert mgr.font_scale is None

    def test_manager_cpu_speed_none(self):
        """Manager CPU speed should start as None."""
        mgr = PykManager()
        assert mgr.cpu_speed is None


class TestVolumeControl:
    """Tests for volume control methods."""

    def test_volume_up(self):
        """VolumeUp should increase volume."""
        mgr = PykManager()
        mock_pygame.mixer.music.get_volume.return_value = 0.5
        mgr.volume_up()
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        assert args[0] == pytest.approx(0.6, abs=0.01)

    def test_volume_up_capped_at_1(self):
        """VolumeUp should not exceed 1.0."""
        mgr = PykManager()
        mock_pygame.mixer.music.get_volume.return_value = 0.95
        mgr.volume_up()
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        assert args[0] <= 1.0

    def test_volume_down(self):
        """VolumeDown should decrease volume."""
        mgr = PykManager()
        mock_pygame.mixer.music.get_volume.return_value = 0.5
        mgr.volume_down()
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        assert args[0] == pytest.approx(0.4, abs=0.01)

    def test_volume_down_capped_at_0(self):
        """VolumeDown should not go below 0.0."""
        mgr = PykManager()
        mock_pygame.mixer.music.get_volume.return_value = 0.05
        mgr.volume_down()
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        assert args[0] >= 0.0

    def test_get_volume(self):
        """get_volume should return current volume."""
        mgr = PykManager()
        mock_pygame.mixer.music.get_volume.return_value = 0.75
        volume = mgr.get_volume()
        assert isinstance(volume, float)

    def test_set_volume(self):
        """set_volume should set volume to specified level."""
        mgr = PykManager()
        mgr.set_volume(0.6)
        mock_pygame.mixer.music.set_volume.assert_called_with(0.6)

    def test_set_volume_clamp_high(self):
        """set_volume should clamp volume above 1.0."""
        mgr = PykManager()
        mgr.set_volume(1.5)
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        assert args[0] <= 1.0

    def test_set_volume_clamp_low(self):
        """set_volume should clamp volume below 0.0."""
        mgr = PykManager()
        mgr.set_volume(-0.5)
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        assert args[0] >= 0.0

    def test_volume_up_handles_error(self):
        """VolumeUp should handle pygame errors gracefully."""
        mgr = PykManager()
        mock_pygame.mixer.music.get_volume.side_effect = mock_pygame.error("test")
        # Should not raise
        mgr.volume_up()
        # Reset side effect
        mock_pygame.mixer.music.get_volume.side_effect = None
        mock_pygame.mixer.music.get_volume.return_value = 0.75

    def test_volume_down_handles_error(self):
        """VolumeDown should handle pygame errors gracefully."""
        mgr = PykManager()
        mock_pygame.mixer.music.get_volume.side_effect = mock_pygame.error("test")
        # Should not raise
        mgr.volume_down()
        # Reset side effect
        mock_pygame.mixer.music.get_volume.side_effect = None
        mock_pygame.mixer.music.get_volume.return_value = 0.75


class TestFontScale:
    """Tests for font scale methods."""

    def test_get_font_scale_default(self):
        """GetFontScale should return default from options."""
        mgr = PykManager()
        mgr.options = MagicMock()
        mgr.options.font_scale = 1.0
        scale = mgr.get_font_scale()
        assert scale == 1.0

    def test_get_font_scale_cached(self):
        """GetFontScale should cache the value."""
        mgr = PykManager()
        mgr.font_scale = 2.0
        scale = mgr.get_font_scale()
        assert scale == 2.0

    def test_zoom_font(self):
        """ZoomFont should multiply font scale by factor."""
        mgr = PykManager()
        mgr.font_scale = 1.0
        mgr.options = MagicMock()
        mgr.options.font_scale = 1.0
        mgr.zoom_font(2.0)
        assert mgr.font_scale == 2.0

    def test_zoom_font_with_player_resize(self):
        """ZoomFont should call player.do_resize if player exists."""
        mgr = PykManager()
        mgr.font_scale = 1.0
        mgr.options = MagicMock()
        mgr.options.font_scale = 1.0
        mgr.display_size = (640, 480)
        mgr.player = MagicMock()
        mgr.zoom_font(1.5)
        mgr.player.do_resize.assert_called_once_with((640, 480))


class TestPlayerManagement:
    """Tests for player initialization and lifecycle."""

    def test_init_player_sets_player(self):
        """InitPlayer should register the player."""
        mgr = PykManager()
        mgr.initialized = True
        mock_player = MagicMock()
        mock_player.window_title = "Test Player"
        mgr.init_player(mock_player)
        assert mgr.player == mock_player

    def test_init_player_shutdowns_previous(self):
        """InitPlayer should shutdown the previous player."""
        mgr = PykManager()
        mgr.initialized = True
        old_player = MagicMock()
        mgr.player = old_player
        new_player = MagicMock()
        new_player.window_title = "New Player"
        mgr.init_player(new_player)
        old_player.shutdown.assert_called_once()
        assert mgr.player == new_player


class TestDisplayManagement:
    """Tests for display open/close operations."""

    def test_close_display(self):
        """CloseDisplay should close the display and clear surface."""
        mgr = PykManager()
        mgr.display = MagicMock()
        mgr.surface = MagicMock()
        mgr.close_display()
        assert mgr.display is None
        assert mgr.surface is None

    def test_close_display_no_display(self):
        """CloseDisplay should handle no display gracefully."""
        mgr = PykManager()
        mgr.display = None
        mgr.surface = MagicMock()
        mgr.close_display()
        assert mgr.surface is None

    def test_flip_with_display(self):
        """Flip should call pygame.display.flip when display exists."""
        mgr = PykManager()
        mgr.display = MagicMock()
        mgr.flip()
        mock_pygame.display.flip.assert_called()

    def test_flip_no_display(self):
        """Flip should not crash when no display."""
        mgr = PykManager()
        mgr.display = None
        mgr.flip()  # Should not raise


class TestAudioManagement:
    """Tests for audio open/close operations."""

    def test_close_audio(self):
        """CloseAudio should quit pygame mixer."""
        mgr = PykManager()
        mgr.audio_props = (44100, -16, 2, 4096)
        mgr.close_audio()
        mock_pygame.mixer.quit.assert_called()
        assert mgr.audio_props is None


class TestQuit:
    """Tests for the Quit method."""

    def test_quit_shutdowns_player(self):
        """Quit should shutdown the current player."""
        mgr = PykManager()
        mgr.initialized = True
        mock_player = MagicMock()
        mgr.player = mock_player
        mgr.quit()
        mock_player.shutdown.assert_called_once()
        assert mgr.player is None

    def test_quit_not_initialized(self):
        """Quit should handle not-initialized state."""
        mgr = PykManager()
        mgr.initialized = False
        mgr.quit()  # Should not raise

    def test_quit_sets_initialized_false(self):
        """Quit should set initialized to False."""
        mgr = PykManager()
        mgr.initialized = True
        mgr.player = None
        mgr.quit()
        assert mgr.initialized is False


class TestWordWrap:
    """Tests for text word wrapping."""

    def test_word_wrap_short_text(self):
        """Short text should not wrap."""
        mgr = PykManager()
        mock_font = MagicMock()
        mock_font.size.return_value = (100, 20)
        lines = mgr.word_wrap_text("Hello", mock_font, 500)
        assert lines == ["Hello"]

    def test_word_wrap_empty_text(self):
        """Empty text should return empty list (no lines from split)."""
        mgr = PykManager()
        mock_font = MagicMock()
        mock_font.size.return_value = (0, 20)
        lines = mgr.word_wrap_text("", mock_font, 500)
        assert lines == []

    def test_find_fold_point_empty_line(self):
        """FindFoldPoint should return 0 for empty line."""
        mgr = PykManager()
        mock_font = MagicMock()
        fold = mgr.find_fold_point("", mock_font, 500)
        assert fold == 0

    def test_find_fold_point_zero_width(self):
        """FindFoldPoint should return full length for zero maxWidth."""
        mgr = PykManager()
        mock_font = MagicMock()
        fold = mgr.find_fold_point("Hello World", mock_font, 0)
        assert fold == len("Hello World")


class TestHandleEvents:
    """Tests for event handling."""

    def test_handle_events_no_display(self):
        """handle_events should be safe with no display."""
        mgr = PykManager()
        mgr.display = None
        mgr.handle_events()  # Should not raise

    def test_handle_events_with_display(self):
        """handle_events should call pygame.event.get with display."""
        mgr = PykManager()
        mgr.display = MagicMock()
        mock_pygame.event.get.return_value = []
        mgr.handle_events()
        mock_pygame.event.get.assert_called()


class TestPoll:
    """Tests for the Poll method."""

    def test_poll_initializes_if_needed(self):
        """Poll should initialize pygame if not initialized."""
        mgr = PykManager()
        mgr.initialized = False
        mgr.display = None
        mgr.poll()
        assert mgr.initialized is True

    def test_poll_calls_do_stuff_on_player(self):
        """Poll should call player.do_stuff if player exists."""
        mgr = PykManager()
        mgr.initialized = True
        mgr.display = None
        mock_player = MagicMock()
        mock_player.state = 1  # STATE_NOT_PLAYING
        mgr.player = mock_player
        mgr.poll()
        mock_player.do_stuff.assert_called_once()


class TestSetCpuSpeed:
    """Tests for CPU speed management."""

    def test_set_cpu_speed_no_change(self):
        """setCpuSpeed should be a no-op if activity hasn't changed."""
        mgr = PykManager()
        mgr.cpu_speed = "playing"
        mgr.set_cpu_speed("playing")
        # No error should occur

    def test_set_cpu_speed_change(self):
        """setCpuSpeed should update cpuSpeed on change."""
        mgr = PykManager()
        mgr.settings = MagicMock()
        mgr.settings.CPUSpeed_idle = 200
        mgr.cpu_speed = None
        mgr.set_cpu_speed("idle")
        assert mgr.cpu_speed == "idle"
