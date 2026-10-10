"""Pure-Python CD+G decoder (Pyodide-compatible).

Port of the classic PyKaraoke CDG interpreter with no pygame/numpy
dependency.  Decodes a raw ``.cdg`` stream into a 300x216 framebuffer of
colour *indices*, tracking which of the 24 visible tiles changed, so a
web UI can replay only the dirty tiles onto a canvas.

All CDG format knowledge originates from the "CDG Revealed" tutorial at
www.jbum.com.
"""

from __future__ import annotations

# CDG Command Code
CDG_COMMAND = 0x09

# CDG Instruction Codes
CDG_INST_MEMORY_PRESET = 1
CDG_INST_BORDER_PRESET = 2
CDG_INST_TILE_BLOCK = 6
CDG_INST_SCROLL_PRESET = 20
CDG_INST_SCROLL_COPY = 24
CDG_INST_DEF_TRANSP_COL = 28
CDG_INST_LOAD_COL_TBL_0_7 = 30
CDG_INST_LOAD_COL_TBL_8_15 = 31
CDG_INST_TILE_BLOCK_XOR = 38

# Bitmask for all CDG fields
CDG_MASK = 0x3F

# Full framebuffer (includes the non-visible border area that scrolling
# rotates through).
CDG_FULL_WIDTH = 300
CDG_FULL_HEIGHT = 216

# The visible area: a centered 288x192 region starting at (6, 12) inside
# the full framebuffer, with 6px borders on the sides and 12px top/bottom.
CDG_DISPLAY_WIDTH = 288
CDG_DISPLAY_HEIGHT = 192
CDG_DISPLAY_X = 6
CDG_DISPLAY_Y = 12

# The visible area is divided into 24 tiles (6x4 of 48x48 each) so only
# the changed tiles need to be redrawn.
TILES_PER_ROW = 6
TILES_PER_COL = 4
TILE_WIDTH = CDG_DISPLAY_WIDTH // TILES_PER_ROW
TILE_HEIGHT = CDG_DISPLAY_HEIGHT // TILES_PER_COL

COLOUR_TABLE_SIZE = 16

# CDG streams carry 300 packets per second of audio.
PACKETS_PER_SECOND = 300

_BORDER_LEFT = CDG_DISPLAY_X  # 6
_BORDER_TOP = CDG_DISPLAY_Y  # 12


def packet_index_at(ms: int) -> int:
    """Return the CDG packet index that should be displayed at *ms*."""
    return int(ms * PACKETS_PER_SECOND / 1000)


class CdgDecoder:
    """Decodes a CDG byte stream into colour-index pixels and dirty tiles.

    The decoder is incremental: call :meth:`process_until` (or
    :meth:`seek`) to advance, then :meth:`update` to collect the tiles
    that changed since the last call.
    """

    def __init__(self, data: bytes):
        self.data = data
        self.packet_pos = 0
        self.rewind()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def rewind(self) -> None:
        """Reset to the start of the stream with a blank screen."""
        self.packet_pos = 0

        # Default colour for any CDG that draws before loading a table.
        self.colour_table = [(0, 0, 0)] * COLOUR_TABLE_SIZE

        self.just_cleared_colour_index = -1
        self.preset_colour_index = -1
        self.border_colour_index = -1
        self.transparent_colour = -1  # reserved, currently unused

        # Screen-shift state (used with scrolling for 1-pixel-at-a-time
        # scrolls).
        self.h_offset = 0
        self.v_offset = 0

        # Colour index of every pixel, x-major: index = y*WIDTH + x.
        self.pixels = bytearray(CDG_FULL_WIDTH * CDG_FULL_HEIGHT)

        # Start with all tiles requiring update.
        self.updated_tiles = 0xFFFFFFFF

    def mark_all_dirty(self) -> None:
        self.updated_tiles = 0xFFFFFFFF

    def seek(self, ms: int) -> None:
        """Rewind and decode up to the packet for time *ms* (milliseconds)."""
        self.rewind()
        self.process_until(packet_index_at(ms))
        self.mark_all_dirty()

    # ------------------------------------------------------------------
    # Packet processing
    # ------------------------------------------------------------------

    def process_until(self, packet_index: int) -> None:
        """Decode all packets between the current position and *packet_index*."""
        if packet_index <= self.packet_pos:
            return
        remaining = packet_index - self.packet_pos
        for _ in range(remaining):
            packet = self._next_packet()
            if packet is None:
                break
            self._process_packet(packet)

    def _next_packet(self):
        start = self.packet_pos
        self.packet_pos += 24
        if start + 24 <= len(self.data):
            return self.data[start : start + 24]
        self.packet_pos = len(self.data)
        return None

    def _process_packet(self, packet: bytes) -> None:
        if (packet[0] & CDG_MASK) != CDG_COMMAND:
            return
        inst = packet[1] & CDG_MASK
        data = packet[4:20]
        if inst == CDG_INST_MEMORY_PRESET:
            self._memory_preset(data)
        elif inst == CDG_INST_BORDER_PRESET:
            self._border_preset(data)
        elif inst == CDG_INST_TILE_BLOCK:
            self._tile_block(data, xor=False)
        elif inst == CDG_INST_SCROLL_PRESET:
            self._scroll(data, copy=False)
        elif inst == CDG_INST_SCROLL_COPY:
            self._scroll(data, copy=True)
        elif inst == CDG_INST_DEF_TRANSP_COL:
            self.transparent_colour = data[0] & 0x0F
        elif inst in (CDG_INST_LOAD_COL_TBL_0_7, CDG_INST_LOAD_COL_TBL_8_15):
            start = 0 if inst == CDG_INST_LOAD_COL_TBL_0_7 else 8
            self._load_colour_table(data, start)
        elif inst == CDG_INST_TILE_BLOCK_XOR:
            self._tile_block(data, xor=True)
        # Unknown instructions are ignored.

    def _memory_preset(self, data: bytes) -> None:
        colour = data[0] & 0x0F
        if colour == self.just_cleared_colour_index:
            return
        self.just_cleared_colour_index = colour
        self.preset_colour_index = colour
        self.border_colour_index = colour
        # Some CDGs preset before loading the colour table; that is fine
        # because pixels store indices and the table maps them to RGB.
        self.pixels[:] = b"\x00" * len(self.pixels)
        self.pixels[:] = bytes([colour]) * len(self.pixels)
        self.updated_tiles = 0xFFFFFFFF

    def _border_preset(self, data: bytes) -> None:
        colour = data[0] & 0x0F
        if colour == self.border_colour_index:
            return
        self.border_colour_index = colour
        w, h = CDG_FULL_WIDTH, CDG_FULL_HEIGHT
        # Left and right borders.
        for y in range(h):
            base = y * w
            for x in range(_BORDER_LEFT):
                self.pixels[base + x] = colour
            for x in range(w - _BORDER_LEFT, w):
                self.pixels[base + x] = colour
        # Top and bottom borders (between the side borders).
        for y in range(_BORDER_TOP):
            base = y * w
            for x in range(_BORDER_LEFT, w - _BORDER_LEFT):
                self.pixels[base + x] = colour
        for y in range(h - _BORDER_TOP, h):
            base = y * w
            for x in range(_BORDER_LEFT, w - _BORDER_LEFT):
                self.pixels[base + x] = colour
        self.updated_tiles = 0xFFFFFFFF

    def _scroll(self, data: bytes, copy: bool) -> None:
        colour = data[0] & 0x0F
        h_scroll = data[1] & CDG_MASK
        v_scroll = data[2] & CDG_MASK
        h_s_cmd = (h_scroll & 0x30) >> 4
        h_offset = h_scroll & 0x07
        v_s_cmd = (v_scroll & 0x30) >> 4
        v_offset = v_scroll & 0x0F

        v_pixels = 12 if v_s_cmd == 2 else (-12 if v_s_cmd == 1 else 0)
        h_pixels = 6 if h_s_cmd == 2 else (-6 if h_s_cmd == 1 else 0)

        if h_offset != self.h_offset or v_offset != self.v_offset:
            self.h_offset = min(h_offset, 5)
            self.v_offset = min(v_offset, 11)
            self.updated_tiles = 0xFFFFFFFF

        if h_pixels == 0 and v_pixels == 0:
            return

        self._apply_scroll(v_pixels, h_pixels, colour, copy)
        self.updated_tiles = 0xFFFFFFFF

    @staticmethod
    def _shift_line(
        line: bytearray, n: int, direction: int, fill: bytearray, copy: bool
    ) -> bytearray:
        """Shift *line* by *n* cells (positive *direction* moves towards index 0)."""
        if copy:
            return line[n:] + line[:n] if direction > 0 else line[-n:] + line[:-n]
        if direction > 0:
            return line[n:] + fill
        return fill + line[:-n]

    def _scroll_columns(self, v_pixels: int, colour: int, copy: bool) -> None:
        """Shift columns (y direction) by *v_pixels*."""
        w, h = CDG_FULL_WIDTH, CDG_FULL_HEIGHT
        n = abs(v_pixels)
        direction = 1 if v_pixels > 0 else -1
        fill = bytearray([colour]) * n
        for x in range(w):
            col = bytearray(self.pixels[x::w])  # all y for this x
            new_col = self._shift_line(col, n, direction, fill, copy)
            for y in range(h):
                self.pixels[y * w + x] = new_col[y]

    def _scroll_rows(self, h_pixels: int, colour: int, copy: bool) -> None:
        """Shift rows (x direction) by *h_pixels*."""
        w, h = CDG_FULL_WIDTH, CDG_FULL_HEIGHT
        n = abs(h_pixels)
        direction = 1 if h_pixels > 0 else -1
        fill = bytearray([colour]) * n
        for y in range(h):
            base = y * w
            row = self._shift_line(
                bytearray(self.pixels[base : base + w]), n, direction, fill, copy
            )
            self.pixels[base : base + w] = row

    def _apply_scroll(self, v_pixels: int, h_pixels: int, colour: int, copy: bool) -> None:
        if v_pixels:
            self._scroll_columns(v_pixels, colour, copy)
        if h_pixels:
            self._scroll_rows(h_pixels, colour, copy)

    def _load_colour_table(self, data: bytes, start: int) -> None:
        for i in range(8):
            entry = ((data[2 * i] & CDG_MASK) << 8) + (data[2 * i + 1] & CDG_MASK)
            entry = ((entry & 0x3F00) >> 2) | (entry & 0x003F)
            red = ((entry & 0x0F00) >> 8) * 17
            green = ((entry & 0x00F0) >> 4) * 17
            blue = (entry & 0x000F) * 17
            self.colour_table[start + i] = (red, green, blue)
        # The whole screen must be redrawn under the new palette.
        self.updated_tiles = 0xFFFFFFFF

    @staticmethod
    def _clamp_tile_origin(data: bytes) -> tuple[int, int]:
        """Tile-block origin, clamped in case a corrupt CDG goes out of bounds."""
        x = (data[3] & CDG_MASK) * 6
        y = (data[2] & 0x1F) * 12
        if y > CDG_FULL_HEIGHT - 12:
            y = CDG_FULL_HEIGHT - 12
        if x > CDG_FULL_WIDTH - 6:
            x = CDG_FULL_WIDTH - 6
        return x, y

    def _draw_tile_pixel(
        self, index: int, pixel: int, colour0: int, colour1: int, xor: bool
    ) -> None:
        if xor:
            xor_col = colour1 if pixel else colour0
            self.pixels[index] = self.pixels[index] ^ xor_col
        else:
            self.pixels[index] = colour1 if pixel else colour0

    def _draw_tile_row(
        self, byte: int, x: int, py: int, colour0: int, colour1: int, xor: bool
    ) -> None:
        w = CDG_FULL_WIDTH
        for j in range(6):
            pixel = (byte >> (5 - j)) & 0x01
            self._draw_tile_pixel(py * w + x + j, pixel, colour0, colour1, xor)

    def _tile_block(self, data: bytes, xor: bool) -> None:
        if data[1] & 0x20:
            # Some discs set this bit to mean "ignore this command".
            return
        colour0 = data[0] & 0x0F
        colour1 = data[1] & 0x0F
        x, y = self._clamp_tile_origin(data)

        self._mark_tile_dirty(x, y)

        for i in range(12):
            self._draw_tile_row(data[4 + i] & CDG_MASK, x, y + i, colour0, colour1, xor)

    def _mark_tile_dirty(self, x: int, y: int) -> None:
        """Mark the tiles overlapped by the tile block at (x, y)."""
        first_row = max((x - _BORDER_LEFT - self.h_offset) // TILE_WIDTH, 0)
        last_row = (x - 1 - self.h_offset) // TILE_WIDTH
        first_col = max((y - _BORDER_TOP - self.v_offset) // TILE_HEIGHT, 0)
        last_col = (y - 1 - self.v_offset) // TILE_HEIGHT

        for col in range(first_col, last_col + 1):
            for row in range(first_row, last_row + 1):
                if 0 <= row < TILES_PER_ROW and 0 <= col < TILES_PER_COL:
                    self.updated_tiles |= (1 << row) << (col * 8)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def get_border_colour(self):
        """Return the current border colour as (r, g, b) or None."""
        if self.border_colour_index == -1:
            return None
        return self.colour_table[self.border_colour_index]

    def update(self) -> dict | None:
        """Return changed tiles plus the border colour, or None if clean.

        The returned dict has the form::

            {
              "border": [r, g, b] | None,
              "tiles": [{"x": tx, "y": ty, "data": <bytes 48*48*3>}, ...]
            }

        ``data`` holds RGB bytes for the 48x48 tile at visible position
        (tx, ty), ready to drop into a canvas.  The dirty mask is cleared.
        """
        if self.updated_tiles == 0:
            return None

        border = self.get_border_colour()
        tiles = []
        for ty in range(TILES_PER_COL):
            for tx in range(TILES_PER_ROW):
                if not self.updated_tiles & ((1 << tx) << (ty * 8)):
                    continue
                tiles.append({"x": tx, "y": ty, "data": self._tile_rgb(tx, ty)})
        self.updated_tiles = 0
        return {"border": list(border) if border else None, "tiles": tiles}

    def _tile_rgb(self, tx: int, ty: int) -> bytes:
        """Return RGB bytes for the 48x48 tile at (tx, ty)."""
        w = CDG_FULL_WIDTH
        x0 = _BORDER_LEFT + self.h_offset + tx * TILE_WIDTH
        y0 = _BORDER_TOP + self.v_offset + ty * TILE_HEIGHT
        out = bytearray(TILE_WIDTH * TILE_HEIGHT * 3)
        o = 0
        for yy in range(TILE_HEIGHT):
            py = y0 + yy
            for xx in range(TILE_WIDTH):
                r, g, b = self.colour_table[self.pixels[py * w + (x0 + xx)]]
                out[o] = r
                out[o + 1] = g
                out[o + 2] = b
                o += 3
        return bytes(out)
