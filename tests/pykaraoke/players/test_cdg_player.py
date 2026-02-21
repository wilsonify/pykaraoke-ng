"""
Tests for pykaraoke.players.cdg module.

Tests the CDG player module with pygame mocked for headless testing.
"""

import sys
from unittest.mock import MagicMock

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()

# Mock Numeric for cdg_aux dependency
import numpy as np

_numeric_shim = MagicMock()
_numeric_shim.zeros = np.zeros
_numeric_shim.array = np.array
_numeric_shim.reshape = np.reshape
_numeric_shim.Int = np.int_
_numeric_shim.UnsignedInt8 = np.uint8
sys.modules.setdefault("Numeric", _numeric_shim)
sys.modules.setdefault("numpy.oldnumeric", _numeric_shim)


class TestCdgModule:
    def test_module_importable(self):
        from pykaraoke.players import cdg

        assert cdg is not None

    def test_has_cdg_player_class(self):
        from pykaraoke.players import cdg

        assert hasattr(cdg, "cdgPlayer")

    def test_cdg_player_is_class(self):
        from pykaraoke.players import cdg

        assert isinstance(cdg.cdgPlayer, type)


class TestCdgPacketConstants:
    def test_cdg_command_code(self):
        from pykaraoke.players import cdg

        if hasattr(cdg, "CDG_COMMAND"):
            assert cdg.CDG_COMMAND == 0x09

    def test_cdg_packet_size(self):
        from pykaraoke.players import cdg

        if hasattr(cdg, "CDG_PACKET_SIZE"):
            assert cdg.CDG_PACKET_SIZE == 24

    def test_cdg_packets_per_second(self):
        from pykaraoke.players import cdg

        if hasattr(cdg, "CDG_PACKETS_PER_SECOND"):
            assert cdg.CDG_PACKETS_PER_SECOND == 300
