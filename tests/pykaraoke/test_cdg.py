"""Tests for pykaraoke.cdg — the pure CD+G decoder."""


from pykaraoke.cdg import (
    CDG_COMMAND,
    CDG_DISPLAY_HEIGHT,
    CDG_DISPLAY_WIDTH,
    CDG_FULL_HEIGHT,
    CDG_FULL_WIDTH,
    CDG_INST_BORDER_PRESET,
    CDG_INST_LOAD_COL_TBL_0_7,
    CDG_INST_MEMORY_PRESET,
    CDG_INST_SCROLL_COPY,
    CDG_INST_TILE_BLOCK,
    CDG_INST_TILE_BLOCK_XOR,
    TILE_HEIGHT,
    TILE_WIDTH,
    TILES_PER_COL,
    TILES_PER_ROW,
    CdgDecoder,
    packet_index_at,
)

# ---------------------------------------------------------------------------
# Packet builders
# ---------------------------------------------------------------------------


def _packet(instruction, data: bytes) -> bytes:
    """Build a 24-byte CDG packet with the given instruction code + data."""
    p = bytearray(24)
    p[0] = CDG_COMMAND
    p[1] = instruction
    p[4 : 4 + len(data)] = data
    return bytes(p)


def _colour_pair(index, r, g, b) -> bytes:
    """Two data bytes for a colour-table entry at *index*.

    CDG packs the 12-bit colour (R G B nibbles) as
    ``hi = (R<<2)|(G>>2)``, ``lo = ((G&3)<<4)|B``; the decoder recovers
    ``(R<<8)|(G<<4)|B`` via ``((raw & 0x3F00) >> 2) | (raw & 0x3F)``.
    """
    R, G, B = r // 17, g // 17, b // 17
    hi = (R << 2) | (G >> 2)
    lo = ((G & 0x03) << 4) | B
    return bytes([hi & 0x3F, lo & 0x3F])


def _load_colour_table(entries: list[tuple[int, int, int]]) -> bytes:
    """A LOAD_COL_TBL_0_7 packet for up to 8 (r, g, b) entries."""
    data = bytearray()
    for i in range(8):
        rgb = entries[i] if i < len(entries) else (0, 0, 0)
        data += _colour_pair(i, *rgb)
    return _packet(CDG_INST_LOAD_COL_TBL_0_7, bytes(data))


def _memory_preset(colour: int) -> bytes:
    return _packet(CDG_INST_MEMORY_PRESET, bytes([colour]))


def _tile_block(x, y, colour0, colour1, rows: list[int], xor=False) -> bytes:
    """A 12x6 tile block at pixel position (x, y) with 12 pixel bytes."""
    data = bytearray(16)
    data[0] = colour0 & 0x0F
    data[1] = colour1 & 0x0F
    data[2] = (y // 12) & 0x1F
    data[3] = (x // 6) & 0x3F
    for i in range(12):
        data[4 + i] = rows[i] & 0x3F
    inst = CDG_INST_TILE_BLOCK_XOR if xor else CDG_INST_TILE_BLOCK
    return _packet(inst, bytes(data))


def _border_preset(colour: int) -> bytes:
    return _packet(CDG_INST_BORDER_PRESET, bytes([colour]))


def _scroll_copy(h_s_cmd, v_s_cmd, h_offset=0, v_offset=0, colour=0) -> bytes:
    h_scroll = ((h_s_cmd & 0x03) << 4) | (h_offset & 0x07)
    v_scroll = ((v_s_cmd & 0x03) << 4) | (v_offset & 0x0F)
    return _packet(CDG_INST_SCROLL_COPY, bytes([colour, h_scroll, v_scroll]))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_dimensions(self):
        assert CDG_FULL_WIDTH == 300
        assert CDG_FULL_HEIGHT == 216
        assert CDG_DISPLAY_WIDTH == 288
        assert CDG_DISPLAY_HEIGHT == 192
        assert (CDG_FULL_WIDTH - CDG_DISPLAY_WIDTH) / 2 == 6
        assert (CDG_FULL_HEIGHT - CDG_DISPLAY_HEIGHT) / 2 == 12

    def test_tiles(self):
        assert TILES_PER_ROW * TILE_WIDTH == CDG_DISPLAY_WIDTH
        assert TILES_PER_COL * TILE_HEIGHT == CDG_DISPLAY_HEIGHT
        assert TILES_PER_ROW == 6
        assert TILES_PER_COL == 4

    def test_packet_index_at(self):
        assert packet_index_at(0) == 0
        assert packet_index_at(1000) == 300
        assert packet_index_at(500) == 150
        assert packet_index_at(333) == 99


# ---------------------------------------------------------------------------
# Decoding behaviour
# ---------------------------------------------------------------------------


class TestDecode:
    def test_blank_file(self):
        # The initial state is "everything dirty", so the first update
        # returns a full black frame with no border colour.
        dec = CdgDecoder(b"")
        upd = dec.update()
        assert upd is not None
        assert upd["border"] is None
        assert len(upd["tiles"]) == 24
        assert dec.update() is None

    def test_memory_preset_fills_screen_and_border(self):
        data = _load_colour_table([(255, 255, 255)]) + _memory_preset(0)
        dec = CdgDecoder(data)
        dec.process_until(10)
        assert dec.get_border_colour() == (255, 255, 255)
        upd = dec.update()
        assert upd is not None
        assert upd["border"] == [255, 255, 255]
        assert len(upd["tiles"]) == 24  # everything dirty

    def test_tile_block_draws_pixels(self):
        # White background, red 12x6 block at (6, 12): every byte is
        # 0b111111 (masked to 6 pixels), so all 6 columns x 12 rows red.
        data = (
            _load_colour_table([(255, 255, 255), (255, 0, 0)])
            + _memory_preset(0)
            + _tile_block(6, 12, 0, 1, [0b111111] * 12)
        )
        dec = CdgDecoder(data)
        dec.process_until(10)
        upd = dec.update()
        assert upd is not None
        tiles = {(t["x"], t["y"]): t for t in upd["tiles"]}
        assert (0, 0) in tiles
        tile = tiles[(0, 0)]

        def px_at(x_off, y_off):
            i = (y_off * TILE_WIDTH + x_off) * 3
            return tuple(tile["data"][i : i + 3])

        # The block covers visible (6..12, 12..24) = tile (0,0) x_off 0..5,
        # and is 12 rows tall (y_off 0..11).
        assert px_at(0, 0) == (255, 0, 0)
        assert px_at(5, 0) == (255, 0, 0)
        assert px_at(6, 0) == (255, 255, 255)  # beyond the block's width
        assert px_at(0, 1) == (255, 0, 0)
        assert px_at(0, 11) == (255, 0, 0)  # last row of the block
        assert px_at(0, 12) == (255, 255, 255)  # beyond the block's height

    def test_xor_tile_block(self):
        data = (
            _load_colour_table([(0, 0, 0), (255, 0, 0)])
            + _memory_preset(0)
            + _tile_block(6, 12, 0, 1, [0b111111] * 12)  # red block
            + _tile_block(6, 12, 0, 1, [0b111111] * 12, xor=True)  # XOR red
            + _tile_block(12, 12, 0, 1, [0b111111] * 12)  # red block next door
        )
        dec = CdgDecoder(data)
        dec.process_until(10)
        upd = dec.update()
        tiles = {(t["x"], t["y"]): t for t in upd["tiles"]}

        def px(tx, x_off, y_off):
            t = tiles[(tx, 0)]
            i = (y_off * TILE_WIDTH + x_off) * 3
            return tuple(t["data"][i : i + 3])

        # x=6..12 (tile 0, x_off 0..5): drawn red then XOR red -> black.
        assert px(0, 0, 0) == (0, 0, 0)
        # x=12..18 (tile 0, x_off 6..11): only the plain red block.
        assert px(0, 6, 0) == (255, 0, 0)

    def test_border_preset(self):
        data = (
            _load_colour_table([(0, 0, 0), (0, 0, 255)])
            + _memory_preset(0)
            + _border_preset(1)
        )
        dec = CdgDecoder(data)
        dec.process_until(10)
        assert dec.get_border_colour() == (0, 0, 255)

    def test_scroll_copy_shifts_pixels(self):
        # Draw a red block in tile (1,0) (visible x=54..59), then scroll
        # left by 6: its content moves into tile (0,0) x_off 42..47.
        data = (
            _load_colour_table([(0, 0, 0), (255, 0, 0)])
            + _memory_preset(0)
            + _tile_block(54, 12, 0, 1, [0b111111] * 12)
            + _scroll_copy(h_s_cmd=2, v_s_cmd=0)  # scroll left by 6
        )
        dec = CdgDecoder(data)
        dec.process_until(10)
        upd = dec.update()
        tiles = {(t["x"], t["y"]): t for t in upd["tiles"]}

        def px(tx, x_off, y_off):
            t = tiles[(tx, 0)]
            i = (y_off * TILE_WIDTH + x_off) * 3
            return tuple(t["data"][i : i + 3])

        # Tile 0 x_off 42..47 now holds the old tile-1 content (red).
        assert px(0, 42, 0) == (255, 0, 0)
        assert px(0, 41, 0) == (0, 0, 0)

    def test_seek_rewinds_and_redraws(self):
        data = (
            _load_colour_table([(255, 255, 255)])
            + _memory_preset(0)
            + _tile_block(6, 12, 0, 0, [0] * 12)
        )
        dec = CdgDecoder(data)
        dec.process_until(10)
        dec.update()
        # Advance past everything: no new packets -> no updates.
        assert dec.update() is None
        # Seek back to start forces a full redraw.
        dec.seek(0)
        upd = dec.update()
        assert upd is not None
        assert len(upd["tiles"]) == 24

    def test_dirty_tiles_only(self):
        data = (
            _load_colour_table([(255, 255, 255)])
            + _memory_preset(0)
            + _tile_block(6, 12, 0, 0, [0] * 12)
        )
        dec = CdgDecoder(data)
        dec.process_until(10)
        upd = dec.update()
        assert upd is not None
        # The tile block only touches tile (0,0); but the memory preset
        # dirtied everything, then the tile block touched (0,0) again.
        # So after consuming the first update, a second update is clean.
        assert dec.update() is None

    def test_unknown_instruction_ignored(self):
        dec = CdgDecoder(_packet(0x7F, bytes(16)))
        dec.process_until(1)
        # The unknown instruction changes nothing: only the initial
        # blank frame is produced, then the decoder is clean.
        upd = dec.update()
        assert upd is not None and upd["border"] is None
        assert dec.update() is None

    def test_short_final_packet_ignored(self):
        # A truncated final packet must not raise or be processed.
        dec = CdgDecoder(_packet(CDG_INST_MEMORY_PRESET, bytes([0]))[:20])
        dec.process_until(10)
        upd = dec.update()
        assert upd is not None and upd["border"] is None
        assert dec.update() is None
