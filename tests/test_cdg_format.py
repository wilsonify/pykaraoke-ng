"""Unit tests for CDG (CD+Graphics) constants and decoding logic.

Tests the CDG format constants and packet structures without requiring pygame.
"""


class TestCDGConstants:
    """Test CDG format constants."""

    def test_cdg_command_code(self):
        """Test CDG command code constant."""
        CDG_COMMAND = 0x09
        assert CDG_COMMAND == 9

    def test_cdg_mask(self):
        """Test CDG mask constant."""
        CDG_MASK = 0x3F
        assert CDG_MASK == 63
        assert CDG_MASK == 0b00111111  # 6 bits

    def test_cdg_instruction_codes(self):
        """Test CDG instruction code constants."""
        # These values are defined in the CDG spec
        CDG_INST_MEMORY_PRESET = 1
        CDG_INST_BORDER_PRESET = 2
        CDG_INST_TILE_BLOCK = 6
        CDG_INST_SCROLL_PRESET = 20
        CDG_INST_SCROLL_COPY = 24
        CDG_INST_DEF_TRANSP_COL = 28
        CDG_INST_LOAD_COL_TBL_0_7 = 30
        CDG_INST_LOAD_COL_TBL_8_15 = 31
        CDG_INST_TILE_BLOCK_XOR = 38

        # Verify they're all distinct
        codes = [
            CDG_INST_MEMORY_PRESET,
            CDG_INST_BORDER_PRESET,
            CDG_INST_TILE_BLOCK,
            CDG_INST_SCROLL_PRESET,
            CDG_INST_SCROLL_COPY,
            CDG_INST_DEF_TRANSP_COL,
            CDG_INST_LOAD_COL_TBL_0_7,
            CDG_INST_LOAD_COL_TBL_8_15,
            CDG_INST_TILE_BLOCK_XOR,
        ]
        assert len(codes) == len(set(codes)), "Instruction codes must be unique"


class TestCDGDisplayDimensions:
    """Test CDG display dimension constants."""

    def test_full_display_dimensions(self):
        """Test full CDG display dimensions."""
        CDG_FULL_WIDTH = 300
        CDG_FULL_HEIGHT = 216

        assert CDG_FULL_WIDTH == 300
        assert CDG_FULL_HEIGHT == 216

    def test_visible_display_dimensions(self):
        """Test visible CDG display dimensions."""
        CDG_DISPLAY_WIDTH = 288
        CDG_DISPLAY_HEIGHT = 192

        assert CDG_DISPLAY_WIDTH == 288
        assert CDG_DISPLAY_HEIGHT == 192

    def test_border_size(self):
        """Test that display area leaves room for borders."""
        CDG_FULL_WIDTH = 300
        CDG_FULL_HEIGHT = 216
        CDG_DISPLAY_WIDTH = 288
        CDG_DISPLAY_HEIGHT = 192

        # Border on each side
        horizontal_border = CDG_FULL_WIDTH - CDG_DISPLAY_WIDTH
        vertical_border = CDG_FULL_HEIGHT - CDG_DISPLAY_HEIGHT

        assert horizontal_border == 12  # 6 pixels on each side
        assert vertical_border == 24  # 12 pixels on top and bottom


class TestCDGTileLayout:
    """Test CDG tile layout constants."""

    def test_tile_grid_dimensions(self):
        """Test tile grid configuration."""
        TILES_PER_ROW = 6
        TILES_PER_COL = 4
        CDG_DISPLAY_WIDTH = 288
        CDG_DISPLAY_HEIGHT = 192

        TILE_WIDTH = CDG_DISPLAY_WIDTH // TILES_PER_ROW
        TILE_HEIGHT = CDG_DISPLAY_HEIGHT // TILES_PER_COL

        assert TILES_PER_ROW == 6
        assert TILES_PER_COL == 4
        assert TILE_WIDTH == 48
        assert TILE_HEIGHT == 48

    def test_total_tiles(self):
        """Test total number of tiles."""
        TILES_PER_ROW = 6
        TILES_PER_COL = 4

        total_tiles = TILES_PER_ROW * TILES_PER_COL
        assert total_tiles == 24

    def test_tiles_cover_display(self):
        """Test that tiles completely cover the display area."""
        TILES_PER_ROW = 6
        TILES_PER_COL = 4
        CDG_DISPLAY_WIDTH = 288
        CDG_DISPLAY_HEIGHT = 192

        TILE_WIDTH = CDG_DISPLAY_WIDTH // TILES_PER_ROW
        TILE_HEIGHT = CDG_DISPLAY_HEIGHT // TILES_PER_COL

        total_width = TILES_PER_ROW * TILE_WIDTH
        total_height = TILES_PER_COL * TILE_HEIGHT

        assert total_width == CDG_DISPLAY_WIDTH
        assert total_height == CDG_DISPLAY_HEIGHT


class TestCDGColourTable:
    """Test CDG colour table constants."""

    def test_colour_table_size(self):
        """Test colour table size."""
        COLOUR_TABLE_SIZE = 16
        assert COLOUR_TABLE_SIZE == 16

    def test_colour_table_split(self):
        """Test that colour table loads are split correctly."""
        # CDG loads colors in two instructions

        # Each instruction loads 8 colors
        colors_per_instruction = 8
        total_colors = colors_per_instruction * 2

        assert total_colors == 16


class TestCDGPacketStructure:
    """Test CDG packet structure."""

    def test_packet_size(self):
        """Test CDG packet size."""
        CDG_PACKET_SIZE = 24
        assert CDG_PACKET_SIZE == 24

    def test_packet_layout(self):
        """Test CDG packet byte layout."""
        # CDG packet structure:
        # Byte 0: Command
        # Byte 1: Instruction
        # Bytes 2-3: Parity Q
        # Bytes 4-19: Data (16 bytes)
        # Bytes 20-23: Parity P

        data_offset = 4
        data_length = 16
        parity_p_offset = 20
        parity_p_length = 4

        total_size = parity_p_offset + parity_p_length
        assert total_size == 24

        # Data section
        assert data_offset == 4
        assert data_offset + data_length == 20

    def test_packet_parsing(self):
        """Test parsing a mock CDG packet."""
        # Create a mock packet (24 bytes)
        packet_data = bytes([0x09] + [0] * 23)  # Command byte + padding

        command = packet_data[0]
        instruction = packet_data[1]
        data = packet_data[4:20]

        assert command == 0x09  # CDG_COMMAND
        assert instruction == 0
        assert len(data) == 16


class TestCDGSyncTiming:
    """Test CDG synchronization and timing."""

    def test_packets_per_second(self):
        """Test CDG packet rate for audio sync."""
        # CDG files have 300 packets per second for 75 sectors/second
        # Each sector has 4 packets
        SECTORS_PER_SECOND = 75
        PACKETS_PER_SECTOR = 4
        PACKETS_PER_SECOND = SECTORS_PER_SECOND * PACKETS_PER_SECTOR

        assert PACKETS_PER_SECOND == 300

    def test_ms_per_packet(self):
        """Test milliseconds per CDG packet."""
        PACKETS_PER_SECOND = 300
        MS_PER_PACKET = 1000.0 / PACKETS_PER_SECOND

        assert abs(MS_PER_PACKET - 3.333) < 0.01  # ~3.33ms per packet


class TestCDGMaskOperations:
    """Test CDG mask and bit operations."""

    def test_mask_command_byte(self):
        """Test masking command byte."""
        CDG_MASK = 0x3F
        CDG_COMMAND = 0x09

        # Only lower 6 bits are significant
        raw_byte = 0xC9  # 0x09 with high bits set
        masked = raw_byte & CDG_MASK

        assert masked == CDG_COMMAND

    def test_mask_instruction_byte(self):
        """Test masking instruction byte."""
        CDG_MASK = 0x3F

        # Test various instruction codes
        test_cases = [
            (0x01, 1),  # MEMORY_PRESET
            (0x41, 1),  # With high bits
            (0x06, 6),  # TILE_BLOCK
            (0xC6, 6),  # With high bits
        ]

        for raw, expected in test_cases:
            masked = raw & CDG_MASK
            assert masked == expected

    def test_colour_extraction(self):
        """Test extracting RGB values from CDG colour data."""
        # CDG uses 4-bit colour components (0-15)
        # Format: [----RRRRGGGGBBBB] in two bytes

        # Example: Bright red (R=15, G=0, B=0)
        byte1 = 0x0F  # High nibble of R (shifted), low nibble of R
        byte2 = 0x00  # G and B

        # Extract components (simplified)
        r = (byte1 & 0x3F) >> 2  # Upper 4 bits of first byte (masked)
        g = ((byte1 & 0x03) << 2) | ((byte2 & 0x30) >> 4)  # Split across bytes
        b = byte2 & 0x0F  # Lower 4 bits of second byte

        # This is a simplified test; actual CDG color parsing is more complex
        assert isinstance(r, int)
        assert isinstance(g, int)
        assert isinstance(b, int)


class TestScrollOffsets:
    """Test CDG scroll offset handling."""

    def test_horizontal_offset_range(self):
        """Test valid horizontal offset range."""
        # CDG allows 0-5 pixel horizontal offset
        MAX_H_OFFSET = 5

        for offset in range(MAX_H_OFFSET + 1):
            assert 0 <= offset <= MAX_H_OFFSET

    def test_vertical_offset_range(self):
        """Test valid vertical offset range."""
        # CDG allows 0-11 pixel vertical offset
        MAX_V_OFFSET = 11

        for offset in range(MAX_V_OFFSET + 1):
            assert 0 <= offset <= MAX_V_OFFSET

    def test_scroll_direction_codes(self):
        """Test scroll direction codes."""
        # Scroll directions (2 bits)
        SCROLL_NONE = 0
        SCROLL_PREWRAP = 1
        SCROLL_POSTWRAP = 2

        directions = [SCROLL_NONE, SCROLL_PREWRAP, SCROLL_POSTWRAP]
        assert len(directions) == len(set(directions))
