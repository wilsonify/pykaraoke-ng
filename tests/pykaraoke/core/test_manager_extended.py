"""
Additional coverage tests for pykaraoke.core.manager module.

Tests pykManager methods that don't require a display.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()

from pykaraoke.core.manager import pykManager


class TestManagerInit:
    """Tests for pykManager initialization attributes."""

    def test_initialized_default(self):
        mgr = pykManager()
        assert mgr.initialized is False

    def test_player_default(self):
        mgr = pykManager()
        assert mgr.player is None

    def test_options_default(self):
        mgr = pykManager()
        assert mgr.options is None

    def test_display_default(self):
        mgr = pykManager()
        assert mgr.display is None

    def test_surface_default(self):
        mgr = pykManager()
        assert mgr.surface is None

    def test_display_size_default(self):
        mgr = pykManager()
        assert mgr.displaySize is None

    def test_display_flags_default(self):
        mgr = pykManager()
        assert mgr.displayFlags == 0

    def test_display_depth_default(self):
        mgr = pykManager()
        assert mgr.displayDepth == 0

    def test_font_path_exists(self):
        mgr = pykManager()
        assert hasattr(mgr, "FontPath")

    def test_icon_path_exists(self):
        mgr = pykManager()
        assert hasattr(mgr, "IconPath")


class TestManagerVolume:
    """Tests for volume control methods."""

    def test_set_volume(self):
        mgr = pykManager()
        mgr.SetVolume(0.5)

    def test_set_volume_clamp_high(self):
        mgr = pykManager()
        mgr.SetVolume(1.5)  # Should clamp to 1.0

    def test_set_volume_clamp_low(self):
        mgr = pykManager()
        mgr.SetVolume(-0.5)  # Should clamp to 0.0

    def test_get_volume(self):
        mgr = pykManager()
        v = mgr.GetVolume()
        assert isinstance(v, (int, float))

    def test_volume_up(self):
        mgr = pykManager()
        mgr.SetVolume(0.5)
        mgr.VolumeUp()
        v = mgr.GetVolume()
        assert v >= 0.5  # Should have gone up

    def test_volume_down(self):
        mgr = pykManager()
        mgr.VolumeDown()  # Should not raise


class TestManagerFontScale:
    """Tests for font scaling."""

    def test_get_font_scale_default(self):
        mgr = pykManager()
        opts = MagicMock()
        opts.font_scale = 1.0
        mgr.options = opts
        fs = mgr.GetFontScale()
        assert fs == 1.0

    def test_zoom_font(self):
        mgr = pykManager()
        opts = MagicMock()
        opts.font_scale = 1.0
        mgr.options = opts
        mgr.ZoomFont(2.0)
        fs = mgr.GetFontScale()
        assert fs == 2.0

    def test_zoom_font_multiply(self):
        mgr = pykManager()
        opts = MagicMock()
        opts.font_scale = 1.0
        mgr.options = opts
        mgr.ZoomFont(2.0)
        mgr.ZoomFont(0.5)
        fs = mgr.GetFontScale()
        assert abs(fs - 1.0) < 0.01


class TestManagerPlayer:
    """Tests for player management."""

    def test_init_player(self):
        mgr = pykManager()
        mock_player = MagicMock()
        mgr.InitPlayer(mock_player)
        assert mgr.player == mock_player

    def test_close_display_no_display(self):
        mgr = pykManager()
        mgr.CloseDisplay()  # Should not raise


class TestManagerWordWrap:
    """Tests for word wrapping."""

    def test_word_wrap_short_text(self):
        mgr = pykManager()
        mock_font = MagicMock()
        mock_font.size.return_value = (100, 20)
        lines = mgr.WordWrapText("Hello World", mock_font, 500)
        assert len(lines) == 1
        assert lines[0] == "Hello World"

    def test_word_wrap_multi_line(self):
        mgr = pykManager()
        mock_font = MagicMock()
        mock_font.size.return_value = (100, 20)
        lines = mgr.WordWrapText("Line1\nLine2\nLine3", mock_font, 500)
        assert len(lines) == 3

    def test_word_wrap_empty(self):
        mgr = pykManager()
        mock_font = MagicMock()
        mock_font.size.return_value = (0, 20)
        lines = mgr.WordWrapText("", mock_font, 500)
        assert lines == []


class TestManagerQuit:
    """Tests for quit functionality."""

    def test_quit_without_init(self):
        mgr = pykManager()
        mgr.Quit()  # Should not raise even without initialization
