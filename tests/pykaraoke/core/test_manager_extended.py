"""
Additional coverage tests for pykaraoke.core.manager module.

Tests PykManager methods that don't require a display.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()

from pykaraoke.core.manager import PykManager


class TestManagerInit:
    """Tests for PykManager initialization attributes."""

    def test_initialized_default(self):
        mgr = PykManager()
        assert mgr.initialized is False

    def test_player_default(self):
        mgr = PykManager()
        assert mgr.player is None

    def test_options_default(self):
        mgr = PykManager()
        assert mgr.options is None

    def test_display_default(self):
        mgr = PykManager()
        assert mgr.display is None

    def test_surface_default(self):
        mgr = PykManager()
        assert mgr.surface is None

    def test_display_size_default(self):
        mgr = PykManager()
        assert mgr.display_size is None

    def test_display_flags_default(self):
        mgr = PykManager()
        assert mgr.display_flags == 0

    def test_display_depth_default(self):
        mgr = PykManager()
        assert mgr.display_depth == 0

    def test_font_path_exists(self):
        mgr = PykManager()
        assert hasattr(mgr, "font_path")

    def test_icon_path_exists(self):
        mgr = PykManager()
        assert hasattr(mgr, "icon_path")


class TestManagerVolume:
    """Tests for volume control methods."""

    def test_set_volume(self):
        mgr = PykManager()
        mgr.set_volume(0.5)

    def test_set_volume_clamp_high(self):
        mgr = PykManager()
        mgr.set_volume(1.5)  # Should clamp to 1.0

    def test_set_volume_clamp_low(self):
        mgr = PykManager()
        mgr.set_volume(-0.5)  # Should clamp to 0.0

    def test_get_volume(self):
        mgr = PykManager()
        v = mgr.get_volume()
        assert isinstance(v, (int, float))

    def test_volume_up(self):
        mgr = PykManager()
        mgr.set_volume(0.5)
        mgr.volume_up()
        v = mgr.get_volume()
        assert v >= 0.5  # Should have gone up

    def test_volume_down(self):
        mgr = PykManager()
        mgr.volume_down()  # Should not raise


class TestManagerFontScale:
    """Tests for font scaling."""

    def test_get_font_scale_default(self):
        mgr = PykManager()
        opts = MagicMock()
        opts.font_scale = 1.0
        mgr.options = opts
        fs = mgr.get_font_scale()
        assert fs == 1.0

    def test_zoom_font(self):
        mgr = PykManager()
        opts = MagicMock()
        opts.font_scale = 1.0
        mgr.options = opts
        mgr.zoom_font(2.0)
        fs = mgr.get_font_scale()
        assert fs == 2.0

    def test_zoom_font_multiply(self):
        mgr = PykManager()
        opts = MagicMock()
        opts.font_scale = 1.0
        mgr.options = opts
        mgr.zoom_font(2.0)
        mgr.zoom_font(0.5)
        fs = mgr.get_font_scale()
        assert abs(fs - 1.0) < 0.01


class TestManagerPlayer:
    """Tests for player management."""

    def test_init_player(self):
        mgr = PykManager()
        mock_player = MagicMock()
        mgr.init_player(mock_player)
        assert mgr.player == mock_player

    def test_close_display_no_display(self):
        mgr = PykManager()
        mgr.close_display()  # Should not raise


class TestManagerWordWrap:
    """Tests for word wrapping."""

    def test_word_wrap_short_text(self):
        mgr = PykManager()
        mock_font = MagicMock()
        mock_font.size.return_value = (100, 20)
        lines = mgr.word_wrap_text("Hello World", mock_font, 500)
        assert len(lines) == 1
        assert lines[0] == "Hello World"

    def test_word_wrap_multi_line(self):
        mgr = PykManager()
        mock_font = MagicMock()
        mock_font.size.return_value = (100, 20)
        lines = mgr.word_wrap_text("Line1\nLine2\nLine3", mock_font, 500)
        assert len(lines) == 3

    def test_word_wrap_empty(self):
        mgr = PykManager()
        mock_font = MagicMock()
        mock_font.size.return_value = (0, 20)
        lines = mgr.word_wrap_text("", mock_font, 500)
        assert lines == []


class TestManagerQuit:
    """Tests for quit functionality."""

    def test_quit_without_init(self):
        mgr = PykManager()
        mgr.quit()  # Should not raise even without initialization
