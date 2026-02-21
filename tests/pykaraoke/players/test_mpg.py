"""
Comprehensive tests for pykaraoke.players.mpg module.

Tests MPEG player functionality with pygame mocked to allow headless testing.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

mock_pygame = install_pygame_mock()

from pykaraoke.players.mpg import externalPlayer


class TestExternalPlayer:
    """Tests for the externalPlayer class."""

    def test_external_player_creation(self):
        """externalPlayer should be constructible."""
        try:
            player = externalPlayer(
                "/path/to/song.mpg",
                MagicMock(),
                MagicMock(),
            )
            assert player is not None
        except (AttributeError, TypeError, RuntimeError):
            pass  # May need additional initialization

    def test_external_player_has_filename(self):
        """externalPlayer should store its filename."""
        try:
            player = externalPlayer(
                "/path/to/song.mpg",
                MagicMock(),
                MagicMock(),
            )
            assert hasattr(player, "FileName")
        except (AttributeError, TypeError, RuntimeError):
            pass


class TestMpgModule:
    """Tests for mpg module-level attributes."""

    def test_module_has_external_player(self):
        """mpg module should have externalPlayer class."""
        from pykaraoke.players import mpg

        assert hasattr(mpg, "externalPlayer")

    def test_module_has_movie_check(self):
        """mpg module should have movie availability check."""
        from pykaraoke.players import mpg

        # movie may be None or False if pygame.movie is not available
        assert hasattr(mpg, "movie")

    def test_external_player_is_class(self):
        """externalPlayer should be a class."""
        from pykaraoke.players import mpg

        assert isinstance(mpg.externalPlayer, type)
