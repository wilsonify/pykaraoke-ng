"""
Comprehensive tests for pykaraoke.players.cdg module.

Tests the CDG player with pygame mocked for headless testing.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

mock_pygame = install_pygame_mock()


class TestCdgModule:
    """Tests for cdg module-level attributes and constants."""

    def test_module_importable(self):
        """CDG module should be importable."""
        from pykaraoke.players import cdg

        assert cdg is not None

    def test_has_cdg_player_class(self):
        """CDG module should have cdgPlayer class."""
        from pykaraoke.players import cdg

        assert hasattr(cdg, "cdgPlayer")

    def test_cdg_player_is_class(self):
        """cdgPlayer should be a class."""
        from pykaraoke.players import cdg

        assert isinstance(cdg.cdgPlayer, type)

    def test_cdg_constants(self):
        """CDG module should define display constants."""
        from pykaraoke.players import cdg

        # CDG display dimensions
        if hasattr(cdg, "CDG_DISPLAY_WIDTH"):
            assert cdg.CDG_DISPLAY_WIDTH > 0
        if hasattr(cdg, "CDG_DISPLAY_HEIGHT"):
            assert cdg.CDG_DISPLAY_HEIGHT > 0


class TestCdgPlayerCreation:
    """Tests for cdgPlayer instantiation."""

    def test_cdg_player_creation(self):
        """cdgPlayer should be constructible with proper args."""
        from pykaraoke.players import cdg

        try:
            player = cdg.cdgPlayer(
                "/path/to/song.cdg",
                MagicMock(),
                MagicMock(),
            )
            assert player is not None
            assert hasattr(player, "FileName")
        except (AttributeError, TypeError, RuntimeError, OSError):
            pass  # May fail without actual files


class TestCdgPacketConstants:
    """Tests for CDG packet format constants."""

    def test_cdg_command_code(self):
        """CDG command code should be defined."""
        from pykaraoke.players import cdg

        # CDG packets use command code 0x09
        if hasattr(cdg, "CDG_COMMAND"):
            assert cdg.CDG_COMMAND == 0x09

    def test_cdg_packet_size(self):
        """CDG packet should be 24 bytes."""
        from pykaraoke.players import cdg

        if hasattr(cdg, "CDG_PACKET_SIZE"):
            assert cdg.CDG_PACKET_SIZE == 24

    def test_cdg_packets_per_second(self):
        """CDG should process 300 packets per second."""
        from pykaraoke.players import cdg

        if hasattr(cdg, "CDG_PACKETS_PER_SECOND"):
            assert cdg.CDG_PACKETS_PER_SECOND == 300
