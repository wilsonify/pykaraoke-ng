"""
Comprehensive tests for pykaraoke.core.manager module.

Tests the pykManager class with pygame mocked to allow headless testing.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

mock_pygame = install_pygame_mock()

from pykaraoke.core.manager import pykManager, manager


class TestPykManagerInit:
    """Tests for pykManager initialization."""

    def test_manager_exists(self):
        """Global manager instance should exist."""
        assert manager is not None
        assert isinstance(manager, pykManager)

    def test_manager_not_initialized(self):
        """Manager should start uninitialized."""
        mgr = pykManager()
        assert mgr.initialized is False

    def test_manager_no_player(self):
        """Manager should start with no player."""
        mgr = pykManager()
        assert mgr.player is None

    def test_manager_no_display(self):
        """Manager should start with no display."""
        mgr = pykManager()
        assert mgr.display is None

    def test_manager_no_surface(self):
        """Manager should start with no surface."""
        mgr = pykManager()
        assert mgr.surface is None

    def test_manager_display_flags_zero(self):
        """Manager display flags should default to 0."""
        mgr = pykManager()
        assert mgr.displayFlags == 0

    def test_manager_display_depth_zero(self):
        """Manager display depth should default to 0."""
        mgr = pykManager()
        assert mgr.displayDepth == 0

    def test_manager_has_font_path(self):
        """Manager should have a font path set."""
        mgr = pykManager()
        assert hasattr(mgr, "FontPath")
        assert isinstance(mgr.FontPath, str)

    def test_manager_has_icon_path(self):
        """Manager should have an icon path set."""
        mgr = pykManager()
        assert hasattr(mgr, "IconPath")
        assert isinstance(mgr.IconPath, str)

    def test_manager_font_scale_none(self):
        """Manager font scale should start as None."""
        mgr = pykManager()
        assert mgr.fontScale is None

    def test_manager_cpu_speed_none(self):
        """Manager CPU speed should start as None."""
        mgr = pykManager()
        assert mgr.cpuSpeed is None


class TestVolumeControl:
    """Tests for volume control methods."""

    def test_volume_up(self):
        """VolumeUp should increase volume."""
        mgr = pykManager()
        mock_pygame.mixer.music.get_volume.return_value = 0.5
        mgr.VolumeUp()
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        assert args[0] == pytest.approx(0.6, abs=0.01)

    def test_volume_up_capped_at_1(self):
        """VolumeUp should not exceed 1.0."""
        mgr = pykManager()
        mock_pygame.mixer.music.get_volume.return_value = 0.95
        mgr.VolumeUp()
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        assert args[0] <= 1.0

    def test_volume_down(self):
        """VolumeDown should decrease volume."""
        mgr = pykManager()
        mock_pygame.mixer.music.get_volume.return_value = 0.5
        mgr.VolumeDown()
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        assert args[0] == pytest.approx(0.4, abs=0.01)

    def test_volume_down_capped_at_0(self):
        """VolumeDown should not go below 0.0."""
        mgr = pykManager()
        mock_pygame.mixer.music.get_volume.return_value = 0.05
        mgr.VolumeDown()
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        assert args[0] >= 0.0

    def test_get_volume(self):
        """GetVolume should return current volume."""
        mgr = pykManager()
        mock_pygame.mixer.music.get_volume.return_value = 0.75
        volume = mgr.GetVolume()
        assert isinstance(volume, float)

    def test_set_volume(self):
        """SetVolume should set volume to specified level."""
        mgr = pykManager()
        mgr.SetVolume(0.6)
        mock_pygame.mixer.music.set_volume.assert_called_with(0.6)

    def test_set_volume_clamp_high(self):
        """SetVolume should clamp volume above 1.0."""
        mgr = pykManager()
        mgr.SetVolume(1.5)
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        assert args[0] <= 1.0

    def test_set_volume_clamp_low(self):
        """SetVolume should clamp volume below 0.0."""
        mgr = pykManager()
        mgr.SetVolume(-0.5)
        mock_pygame.mixer.music.set_volume.assert_called()
        args = mock_pygame.mixer.music.set_volume.call_args[0]
        assert args[0] >= 0.0

    def test_volume_up_handles_error(self):
        """VolumeUp should handle pygame errors gracefully."""
        mgr = pykManager()
        mock_pygame.mixer.music.get_volume.side_effect = mock_pygame.error("test")
        # Should not raise
        mgr.VolumeUp()
        # Reset side effect
        mock_pygame.mixer.music.get_volume.side_effect = None
        mock_pygame.mixer.music.get_volume.return_value = 0.75

    def test_volume_down_handles_error(self):
        """VolumeDown should handle pygame errors gracefully."""
        mgr = pykManager()
        mock_pygame.mixer.music.get_volume.side_effect = mock_pygame.error("test")
        # Should not raise
        mgr.VolumeDown()
        # Reset side effect
        mock_pygame.mixer.music.get_volume.side_effect = None
        mock_pygame.mixer.music.get_volume.return_value = 0.75


class TestFontScale:
    """Tests for font scale methods."""

    def test_get_font_scale_default(self):
        """GetFontScale should return default from options."""
        mgr = pykManager()
        mgr.options = MagicMock()
        mgr.options.font_scale = 1.0
        scale = mgr.GetFontScale()
        assert scale == 1.0

    def test_get_font_scale_cached(self):
        """GetFontScale should cache the value."""
        mgr = pykManager()
        mgr.fontScale = 2.0
        scale = mgr.GetFontScale()
        assert scale == 2.0

    def test_zoom_font(self):
        """ZoomFont should multiply font scale by factor."""
        mgr = pykManager()
        mgr.fontScale = 1.0
        mgr.options = MagicMock()
        mgr.options.font_scale = 1.0
        mgr.ZoomFont(2.0)
        assert mgr.fontScale == 2.0

    def test_zoom_font_with_player_resize(self):
        """ZoomFont should call player.doResize if player exists."""
        mgr = pykManager()
        mgr.fontScale = 1.0
        mgr.options = MagicMock()
        mgr.options.font_scale = 1.0
        mgr.displaySize = (640, 480)
        mgr.player = MagicMock()
        mgr.ZoomFont(1.5)
        mgr.player.doResize.assert_called_once_with((640, 480))


class TestPlayerManagement:
    """Tests for player initialization and lifecycle."""

    def test_init_player_sets_player(self):
        """InitPlayer should register the player."""
        mgr = pykManager()
        mgr.initialized = True
        mock_player = MagicMock()
        mock_player.WindowTitle = "Test Player"
        mgr.InitPlayer(mock_player)
        assert mgr.player == mock_player

    def test_init_player_shutdowns_previous(self):
        """InitPlayer should shutdown the previous player."""
        mgr = pykManager()
        mgr.initialized = True
        old_player = MagicMock()
        mgr.player = old_player
        new_player = MagicMock()
        new_player.WindowTitle = "New Player"
        mgr.InitPlayer(new_player)
        old_player.shutdown.assert_called_once()
        assert mgr.player == new_player


class TestDisplayManagement:
    """Tests for display open/close operations."""

    def test_close_display(self):
        """CloseDisplay should close the display and clear surface."""
        mgr = pykManager()
        mgr.display = MagicMock()
        mgr.surface = MagicMock()
        mgr.CloseDisplay()
        assert mgr.display is None
        assert mgr.surface is None

    def test_close_display_no_display(self):
        """CloseDisplay should handle no display gracefully."""
        mgr = pykManager()
        mgr.display = None
        mgr.surface = MagicMock()
        mgr.CloseDisplay()
        assert mgr.surface is None

    def test_flip_with_display(self):
        """Flip should call pygame.display.flip when display exists."""
        mgr = pykManager()
        mgr.display = MagicMock()
        mgr.Flip()
        mock_pygame.display.flip.assert_called()

    def test_flip_no_display(self):
        """Flip should not crash when no display."""
        mgr = pykManager()
        mgr.display = None
        mgr.Flip()  # Should not raise


class TestAudioManagement:
    """Tests for audio open/close operations."""

    def test_close_audio(self):
        """CloseAudio should quit pygame mixer."""
        mgr = pykManager()
        mgr.audioProps = (44100, -16, 2, 4096)
        mgr.CloseAudio()
        mock_pygame.mixer.quit.assert_called()
        assert mgr.audioProps is None


class TestQuit:
    """Tests for the Quit method."""

    def test_quit_shutdowns_player(self):
        """Quit should shutdown the current player."""
        mgr = pykManager()
        mgr.initialized = True
        mock_player = MagicMock()
        mgr.player = mock_player
        mgr.Quit()
        mock_player.shutdown.assert_called_once()
        assert mgr.player is None

    def test_quit_not_initialized(self):
        """Quit should handle not-initialized state."""
        mgr = pykManager()
        mgr.initialized = False
        mgr.Quit()  # Should not raise

    def test_quit_sets_initialized_false(self):
        """Quit should set initialized to False."""
        mgr = pykManager()
        mgr.initialized = True
        mgr.player = None
        mgr.Quit()
        assert mgr.initialized is False


class TestWordWrap:
    """Tests for text word wrapping."""

    def test_word_wrap_short_text(self):
        """Short text should not wrap."""
        mgr = pykManager()
        mock_font = MagicMock()
        mock_font.size.return_value = (100, 20)
        lines = mgr.WordWrapText("Hello", mock_font, 500)
        assert lines == ["Hello"]

    def test_word_wrap_empty_text(self):
        """Empty text should return one empty line."""
        mgr = pykManager()
        mock_font = MagicMock()
        mock_font.size.return_value = (0, 20)
        lines = mgr.WordWrapText("", mock_font, 500)
        assert lines == [""]

    def test_find_fold_point_empty_line(self):
        """FindFoldPoint should return 0 for empty line."""
        mgr = pykManager()
        mock_font = MagicMock()
        fold = mgr.FindFoldPoint("", mock_font, 500)
        assert fold == 0

    def test_find_fold_point_zero_width(self):
        """FindFoldPoint should return full length for zero maxWidth."""
        mgr = pykManager()
        mock_font = MagicMock()
        fold = mgr.FindFoldPoint("Hello World", mock_font, 0)
        assert fold == len("Hello World")


class TestHandleEvents:
    """Tests for event handling."""

    def test_handle_events_no_display(self):
        """handleEvents should be safe with no display."""
        mgr = pykManager()
        mgr.display = None
        mgr.handleEvents()  # Should not raise

    def test_handle_events_with_display(self):
        """handleEvents should call pygame.event.get with display."""
        mgr = pykManager()
        mgr.display = MagicMock()
        mock_pygame.event.get.return_value = []
        mgr.handleEvents()
        mock_pygame.event.get.assert_called()


class TestPoll:
    """Tests for the Poll method."""

    def test_poll_initializes_if_needed(self):
        """Poll should initialize pygame if not initialized."""
        mgr = pykManager()
        mgr.initialized = False
        mgr.display = None
        mgr.Poll()
        assert mgr.initialized is True

    def test_poll_calls_do_stuff_on_player(self):
        """Poll should call player.doStuff if player exists."""
        mgr = pykManager()
        mgr.initialized = True
        mgr.display = None
        mock_player = MagicMock()
        mock_player.State = 1  # STATE_NOT_PLAYING
        mgr.player = mock_player
        mgr.Poll()
        mock_player.doStuff.assert_called_once()


class TestSetCpuSpeed:
    """Tests for CPU speed management."""

    def test_set_cpu_speed_no_change(self):
        """setCpuSpeed should be a no-op if activity hasn't changed."""
        mgr = pykManager()
        mgr.cpuSpeed = "playing"
        mgr.setCpuSpeed("playing")
        # No error should occur

    def test_set_cpu_speed_change(self):
        """setCpuSpeed should update cpuSpeed on change."""
        mgr = pykManager()
        mgr.settings = MagicMock()
        mgr.settings.CPUSpeed_idle = 200
        mgr.cpuSpeed = None
        mgr.setCpuSpeed("idle")
        assert mgr.cpuSpeed == "idle"
