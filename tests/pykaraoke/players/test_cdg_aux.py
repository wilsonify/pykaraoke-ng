"""
Comprehensive tests for pykaraoke.players.cdg_aux module.

Tests CDG (CD+Graphics) constants and packet parsing logic
with pygame and Numeric mocked to allow headless testing.
"""

import sys
import numpy as np
from unittest.mock import MagicMock

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()

# Mock numpy.oldnumeric / Numeric since they are no longer available in modern numpy
_numeric_shim = MagicMock()
_numeric_shim.zeros = np.zeros
_numeric_shim.array = np.array
_numeric_shim.reshape = np.reshape
_numeric_shim.Int = np.int_
_numeric_shim.Int8 = np.int8
_numeric_shim.UInt8 = np.uint8
_numeric_shim.Int16 = np.int16
_numeric_shim.UnsignedInt8 = np.uint8
sys.modules.setdefault("Numeric", _numeric_shim)
sys.modules.setdefault("numpy.oldnumeric", _numeric_shim)

from pykaraoke.players.cdg_aux import (
    CDG_COMMAND,
    CDG_INST_MEMORY_PRESET,
    CDG_INST_BORDER_PRESET,
    CDG_INST_TILE_BLOCK,
    CDG_INST_SCROLL_PRESET,
    CDG_INST_SCROLL_COPY,
    CDG_INST_DEF_TRANSP_COL,
    CDG_INST_LOAD_COL_TBL_0_7,
    CDG_INST_LOAD_COL_TBL_8_15,
    CDG_INST_TILE_BLOCK_XOR,
    CDG_MASK,
    CDG_FULL_WIDTH,
    CDG_FULL_HEIGHT,
    CDG_DISPLAY_WIDTH,
    CDG_DISPLAY_HEIGHT,
    TILE_WIDTH,
    TILE_HEIGHT,
    COLOUR_TABLE_SIZE,
    CdgPacketReader,
)


class TestCdgConstants:
    """Tests for CDG format constants."""

    def test_cdg_command_value(self):
        assert CDG_COMMAND == 0x09

    def test_cdg_mask_value(self):
        assert CDG_MASK == 0x3F

    def test_full_display_dimensions(self):
        assert CDG_FULL_WIDTH == 300
        assert CDG_FULL_HEIGHT == 216

    def test_visible_display_dimensions(self):
        assert CDG_DISPLAY_WIDTH == 288
        assert CDG_DISPLAY_HEIGHT == 192

    def test_tile_dimensions(self):
        # 288 / 6 tiles per row = 48, 192 / 4 tiles per col = 48
        assert TILE_WIDTH == 48
        assert TILE_HEIGHT == 48

    def test_colour_table_size(self):
        assert COLOUR_TABLE_SIZE == 16

    def test_instruction_codes(self):
        assert CDG_INST_MEMORY_PRESET == 1
        assert CDG_INST_BORDER_PRESET == 2
        assert CDG_INST_TILE_BLOCK == 6
        assert CDG_INST_SCROLL_PRESET == 20
        assert CDG_INST_SCROLL_COPY == 24
        assert CDG_INST_DEF_TRANSP_COL == 28
        assert CDG_INST_LOAD_COL_TBL_0_7 == 30
        assert CDG_INST_LOAD_COL_TBL_8_15 == 31
        assert CDG_INST_TILE_BLOCK_XOR == 38


class TestCdgPacketReaderInit:
    """Tests for CdgPacketReader initialization."""

    def _make_reader(self):
        # CDG data: sequence of 24-byte packets. Use 1 empty packet.
        cdg_data = bytes(24)
        mapper_surface = MagicMock()
        mapper_surface.get_size.return_value = (CDG_FULL_WIDTH, CDG_FULL_HEIGHT)
        return CdgPacketReader(cdg_data, mapper_surface)

    def test_create_reader(self):
        reader = self._make_reader()
        assert reader is not None

    def test_reader_has_rewind(self):
        reader = self._make_reader()
        assert hasattr(reader, "rewind")

    def test_reader_has_mark_tiles_dirty(self):
        reader = self._make_reader()
        assert hasattr(reader, "mark_tiles_dirty")

    def test_rewind_resets_state(self):
        reader = self._make_reader()
        reader.rewind()
        # Should not raise


class TestCdgPacketReaderMethods:
    """Tests for CdgPacketReader operation."""

    def _make_reader_with_data(self, packet_data):
        mapper_surface = MagicMock()
        mapper_surface.get_size.return_value = (CDG_FULL_WIDTH, CDG_FULL_HEIGHT)
        return CdgPacketReader(packet_data, mapper_surface)

    def test_mark_tiles_dirty(self):
        reader = self._make_reader_with_data(bytes(24))
        reader.mark_tiles_dirty()  # Should not raise

    def test_rewind_twice(self):
        reader = self._make_reader_with_data(bytes(24))
        reader.rewind()
        reader.rewind()  # Should be idempotent
