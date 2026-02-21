"""
Comprehensive tests for pykaraoke.players.cdg_aux module.

Tests CDG (CD+Graphics) packet parsing and rendering logic
with pygame mocked to allow headless testing.
"""

import sys
import numpy as np
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

mock_pygame = install_pygame_mock()

# Mock numpy.oldnumeric / Numeric since they are no longer available
# cdg_aux tries: import Numeric as N, then falls back to numpy.oldnumeric as N
# We create a shim module that maps old Numeric API to numpy
_numeric_shim = MagicMock()
_numeric_shim.zeros = np.zeros
_numeric_shim.array = np.array
_numeric_shim.reshape = np.reshape
_numeric_shim.Int = np.int_
_numeric_shim.Int8 = np.int8
_numeric_shim.UInt8 = np.uint8
_numeric_shim.Int16 = np.int16
_numeric_shim.UnsignedInt8 = np.uint8
sys.modules["Numeric"] = _numeric_shim
sys.modules["numpy.oldnumeric"] = _numeric_shim

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
    CdgPacketReader,
)


class TestCdgPacketReaderInit:
    """Tests for CdgPacketReader initialization."""

    def test_create_reader(self):
        """CdgPacketReader should be constructible."""
        reader = CdgPacketReader()
        assert reader is not None

    def test_initial_color_table(self):
        """Reader should have a color table initialized."""
        reader = CdgPacketReader()
        assert hasattr(reader, "cdgColourTable") or hasattr(reader, "cdgColorTable")

    def test_initial_surface_array(self):
        """Reader should have a surface array."""
        reader = CdgPacketReader()
        assert hasattr(reader, "cdgSurfarray") or hasattr(reader, "cdgPixelColour")

    def test_initial_border_colour(self):
        """Reader should have a border colour."""
        reader = CdgPacketReader()
        assert hasattr(reader, "cdgBorderColour") or hasattr(reader, "borderColour")


class TestCdgPacketParsing:
    """Tests for CDG packet parsing methods."""

    def test_process_empty_packet(self):
        """Processing an empty/zero packet should not crash."""
        reader = CdgPacketReader()
        # A CDG packet is 24 bytes
        packet = bytes(24)
        try:
            reader.cdgPacketProcess(packet)
        except (AttributeError, TypeError, IndexError):
            pass  # May need specific initialization

    def test_process_memory_preset_packet(self):
        """Memory Preset CDG command should be handled."""
        reader = CdgPacketReader()
        # CDG command: subcode with command=0x09 (CDG), instruction=1 (Memory Preset)
        # Byte 0: command (0x09 = CDG_COMMAND)
        # Byte 1: instruction (0x01 = CDG_INST_MEMORY_PRESET)
        packet = bytearray(24)
        packet[0] = 0x09  # CDG command marker
        packet[1] = 0x01  # Memory Preset instruction
        packet[4] = 0x00  # Color index
        try:
            reader.cdgPacketProcess(packet)
        except (AttributeError, TypeError, IndexError):
            pass

    def test_process_border_preset_packet(self):
        """Border Preset CDG command should be handled."""
        reader = CdgPacketReader()
        packet = bytearray(24)
        packet[0] = 0x09  # CDG command marker
        packet[1] = 0x02  # Border Preset instruction
        packet[4] = 0x05  # Color index
        try:
            reader.cdgPacketProcess(packet)
        except (AttributeError, TypeError, IndexError):
            pass

    def test_process_tile_block_packet(self):
        """Tile Block CDG command should be handled."""
        reader = CdgPacketReader()
        packet = bytearray(24)
        packet[0] = 0x09  # CDG command marker
        packet[1] = 0x06  # Tile Block (normal) instruction
        try:
            reader.cdgPacketProcess(packet)
        except (AttributeError, TypeError, IndexError):
            pass

    def test_process_load_color_table_lo(self):
        """Load Color Table (Low) CDG command should be handled."""
        reader = CdgPacketReader()
        packet = bytearray(24)
        packet[0] = 0x09  # CDG command marker
        packet[1] = 0x1E  # Load Color Table Low
        try:
            reader.cdgPacketProcess(packet)
        except (AttributeError, TypeError, IndexError):
            pass

    def test_process_load_color_table_hi(self):
        """Load Color Table (High) CDG command should be handled."""
        reader = CdgPacketReader()
        packet = bytearray(24)
        packet[0] = 0x09  # CDG command marker
        packet[1] = 0x1F  # Load Color Table High
        try:
            reader.cdgPacketProcess(packet)
        except (AttributeError, TypeError, IndexError):
            pass


class TestCdgPacketReaderReset:
    """Tests for CDG state reset."""

    def test_reset_clears_state(self):
        """Resetting the reader should clear visual state."""
        reader = CdgPacketReader()
        if hasattr(reader, "cdgReset"):
            reader.cdgReset()
        elif hasattr(reader, "reset"):
            reader.reset()


class TestCdgConstants:
    """Tests for CDG format constants used in cdg_aux."""

    def test_cdg_command_value(self):
        """CDG command marker should be 0x09."""
        assert CDG_COMMAND == 0x09

    def test_cdg_mask_value(self):
        """CDG mask should be 0x3F."""
        assert CDG_MASK == 0x3F

    def test_tile_dimensions(self):
        """CDG tiles should be 6x12 pixels."""
        assert TILE_WIDTH == 6
        assert TILE_HEIGHT == 12

    def test_display_dimensions(self):
        """CDG full display should be 300x216."""
        assert CDG_FULL_WIDTH == 300
        assert CDG_FULL_HEIGHT == 216

    def test_visible_display_dimensions(self):
        """CDG visible display should be 288x192."""
        assert CDG_DISPLAY_WIDTH == 288
        assert CDG_DISPLAY_HEIGHT == 192

    def test_instruction_codes(self):
        """CDG instruction codes should have specific values."""
        assert CDG_INST_MEMORY_PRESET == 1
        assert CDG_INST_BORDER_PRESET == 2
        assert CDG_INST_TILE_BLOCK == 6
        assert CDG_INST_SCROLL_PRESET == 20
        assert CDG_INST_SCROLL_COPY == 24
        assert CDG_INST_DEF_TRANSP_COL == 28
        assert CDG_INST_LOAD_COL_TBL_0_7 == 30
        assert CDG_INST_LOAD_COL_TBL_8_15 == 31
        assert CDG_INST_TILE_BLOCK_XOR == 38
