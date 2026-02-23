"""
Tests for pykaraoke.players.mpg module.

Tests MPEG player functionality with pygame mocked to allow headless testing.
"""

import sys
from unittest.mock import MagicMock

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()


class TestMpgModule:
    def test_module_importable(self):
        from pykaraoke.players import mpg

        assert mpg is not None

    def test_module_has_external_player(self):
        from pykaraoke.players import mpg

        assert hasattr(mpg, "ExternalPlayer")

    def test_external_player_is_class(self):
        from pykaraoke.players import mpg

        assert isinstance(mpg.ExternalPlayer, type)

    def test_module_has_movie_attribute(self):
        from pykaraoke.players import mpg

        assert hasattr(mpg, "movie")
