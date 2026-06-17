//! CDG packet decoder — pure Rust implementation of the CD+G graphics format.
//!
//! Port of `src/pykaraoke/players/cdg_aux.py` `CdgPacketReader`.
//! Processes 24-byte CDG packets into a 300×216 pixel buffer with
//! 16-colour palette, scroll, tile-block, and XOR commands.

use crate::format::cdg::*;
use crate::views::CdgFrameView;

// ---------------------------------------------------------------------------
// Colour table
// ---------------------------------------------------------------------------

/// A single RGB colour entry (0–255 each).
#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct Rgb {
    pub r: u8,
    pub g: u8,
    pub b: u8,
}

/// Converts a raw 14-bit packed colour value (from two CDG data bytes) into
/// an `Rgb`.  The encoding is `--RRRR--GGGG--BBBB`.
fn decode_colour_entry(high: u8, low: u8) -> Rgb {
    let entry = ((high as u16) << 8) | (low as u16);
    let entry = ((entry & 0x3F00) >> 2) | (entry & 0x003F);
    let r = ((entry & 0x0F00) >> 8) as u8 * 17;
    let g = ((entry & 0x00F0) >> 4) as u8 * 17;
    let b = (entry & 0x000F) as u8 * 17;
    Rgb { r, g, b }
}

// ---------------------------------------------------------------------------
// Tile bitmask helpers
// ---------------------------------------------------------------------------

/// Number of tile rows (horizontal tiles).
const TILES_PER_ROW: u8 = CDG_TILES_HORIZONTAL as u8;  // 6

/// Number of tile columns (vertical tiles).
const TILES_PER_COL: u8 = CDG_TILES_VERTICAL as u8;     // 4

const TILE_W: usize = CDG_TILE_WIDTH as usize;          // 48
const TILE_H: usize = CDG_TILE_HEIGHT as usize;         // 48

/// Marks a single tile (row, col) in the dirty bitmask.
fn set_tile_dirty(mask: &mut u32, row: u8, col: u8) {
    *mask |= (1u32 << row) << (col * 8);
}

/// Marks all 24 tiles dirty.
fn all_tiles_dirty() -> u32 {
    0xFFFF_FFFF
}

/// Collects dirty (row, col) pairs and resets the mask to zero.
fn drain_dirty_tiles(mask: &mut u32) -> Vec<(u8, u8)> {
    let m = *mask;
    *mask = 0;
    if m == 0 {
        return Vec::new();
    }
    let mut tiles = Vec::with_capacity(24);
    for col in 0..TILES_PER_COL {
        for row in 0..TILES_PER_ROW {
            if m & ((1u32 << row) << (col * 8)) != 0 {
                tiles.push((row, col));
            }
        }
    }
    tiles
}

// ---------------------------------------------------------------------------
// CdgPacketDecoder
// ---------------------------------------------------------------------------

/// Full state of a CD+G graphics decoder.
///
/// Maintains:
/// - The raw CDG packet data and current read position.
/// - A 300×216 pixel colour-index buffer (`pixel_indices`).
/// - A parallel 300×216 RGB buffer (`surfarray`), refreshed from
///   `pixel_indices` + `colour_table` whenever the colour table changes.
/// - A 16-entry RGB colour palette.
/// - Scroll offsets (h_offset, v_offset) for fine sub-tile scrolling.
/// - A dirty-tile bitmask for partial updates.
/// - The "just cleared" colour-index optimisation to skip redundant clears.
#[derive(Debug, Clone)]
pub struct CdgPacketDecoder {
    // Raw CDG file bytes and read position (in bytes).
    cdg_data: Vec<u8>,
    cdg_data_pos: usize,

    // Colour table: index → RGB.
    colour_table: [Rgb; COLOUR_TABLE_SIZE],

    // Pixel colour INDICES (0–15) for the full 300×216 buffer.
    pixel_indices: [[u8; CDG_FULL_WIDTH as usize]; CDG_FULL_HEIGHT as usize],

    // RGB surface array — mapped from pixel_indices through colour_table.
    surfarray: [[Rgb; CDG_FULL_WIDTH as usize]; CDG_FULL_HEIGHT as usize],

    // Fine scroll offsets (persistent until changed by scroll commands).
    h_offset: u8,
    v_offset: u8,

    // Border / preset colour indices (-1 = not yet set).
    just_cleared_colour_index: i8,
    preset_colour_index: i8,
    border_colour_index: i8,
    transparent_colour_index: i8,

    // Dirty tile bitmask (32 bits = 4 cols × 6 rows, 8 bits per col).
    dirty_tiles: u32,
}

impl CdgPacketDecoder {
    /// Creates a new decoder from the raw bytes of a `.cdg` file.
    pub fn new(cdg_data: Vec<u8>) -> Self {
        let mut s = Self {
            cdg_data,
            cdg_data_pos: 0,
            colour_table: [Rgb::default(); COLOUR_TABLE_SIZE],
            pixel_indices: [[0u8; CDG_FULL_WIDTH as usize]; CDG_FULL_HEIGHT as usize],
            surfarray: [[Rgb::default(); CDG_FULL_WIDTH as usize]; CDG_FULL_HEIGHT as usize],
            h_offset: 0,
            v_offset: 0,
            just_cleared_colour_index: -1,
            preset_colour_index: -1,
            border_colour_index: -1,
            transparent_colour_index: -1,
            dirty_tiles: all_tiles_dirty(),
        };
        s.rebuild_surfarray();
        s
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    /// Rewind to the start of the CDG data and reset all display state.
    pub fn rewind(&mut self) {
        self.cdg_data_pos = 0;
        self.colour_table = [Rgb::default(); COLOUR_TABLE_SIZE];
        self.pixel_indices = [[0u8; CDG_FULL_WIDTH as usize]; CDG_FULL_HEIGHT as usize];
        self.h_offset = 0;
        self.v_offset = 0;
        self.just_cleared_colour_index = -1;
        self.preset_colour_index = -1;
        self.border_colour_index = -1;
        self.transparent_colour_index = -1;
        self.dirty_tiles = all_tiles_dirty();
        self.rebuild_surfarray();
    }

    /// Seek to `packet_index` by rewinding and re-processing that many packets.
    pub fn seek_to_packet(&mut self, packet_index: u32) {
        self.rewind();
        if packet_index > 0 {
            self.do_packets(packet_index);
        }
        self.mark_tiles_dirty();
    }

    /// Process `num_packets` CDG packets from the current position.
    /// Returns `true` if all requested packets were processed,
    /// `false` if EOF was reached before processing all of them.
    pub fn do_packets(&mut self, num_packets: u32) -> bool {
        for _ in 0..num_packets {
            let Some(pkt) = self.read_next_packet() else {
                return false;
            };
            self.process_packet(&pkt);
        }
        true
    }

    /// Mark all tiles dirty.
    pub fn mark_tiles_dirty(&mut self) {
        self.dirty_tiles = all_tiles_dirty();
    }

    /// Consume and return the current dirty-tile list.
    pub fn get_dirty_tiles(&mut self) -> Vec<(u8, u8)> {
        drain_dirty_tiles(&mut self.dirty_tiles)
    }

    /// Returns the border colour as `Rgb` if it has been set, else `None`.
    pub fn get_border_colour(&self) -> Option<Rgb> {
        if self.border_colour_index < 0 {
            return None;
        }
        Some(self.colour_table[self.border_colour_index as usize])
    }

    /// Fill a caller-provided 48×48 pixel buffer (RGBA, 4 bytes per pixel)
    /// with the contents of tile `(row, col)`.
    ///
    /// The tile coordinates are in the visible 6×4 grid
    /// (row 0..5, col 0..3).
    pub fn fill_tile_rgba(&self, buf: &mut [u8], row: u8, col: u8) {
        let row_start = 6usize + self.h_offset as usize + (row as usize * TILE_W);
        let col_start = 12usize + self.v_offset as usize + (col as usize * TILE_H);

        for ty in 0..TILE_H {
            for tx in 0..TILE_W {
                let px = row_start + tx;
                let py = col_start + ty;
                let rgb = if px < CDG_FULL_WIDTH as usize && py < CDG_FULL_HEIGHT as usize {
                    self.surfarray[py][px]
                } else {
                    Rgb::default()
                };
                let idx = (ty * TILE_W + tx) * 4;
                buf[idx] = rgb.r;
                buf[idx + 1] = rgb.g;
                buf[idx + 2] = rgb.b;
                buf[idx + 3] = 255;
            }
        }
    }

    /// Render the visible 288×192 display area as RGBA pixels into a
    /// `CdgFrameView` at the given `timestamp_ms`.
    pub fn render_frame(&self, timestamp_ms: u64) -> CdgFrameView {
        let w = CDG_DISPLAY_WIDTH as usize;   // 288
        let h = CDG_DISPLAY_HEIGHT as usize;  // 192
        let mut pixels = vec![0u8; w * h * 4];

        for y in 0..h {
            for x in 0..w {
                let src_x = 6usize + self.h_offset as usize + x;
                let src_y = 12usize + self.v_offset as usize + y;
                let rgb = if src_x < CDG_FULL_WIDTH as usize && src_y < CDG_FULL_HEIGHT as usize {
                    self.surfarray[src_y][src_x]
                } else {
                    Rgb::default()
                };
                let idx = (y * w + x) * 4;
                pixels[idx] = rgb.r;
                pixels[idx + 1] = rgb.g;
                pixels[idx + 2] = rgb.b;
                pixels[idx + 3] = 255;
            }
        }

        CdgFrameView {
            pixels,
            width: CDG_DISPLAY_WIDTH,
            height: CDG_DISPLAY_HEIGHT,
            timestamp_ms,
        }
    }

    /// Render just a single tile (48×48) into the RGBA buffer portion of
    /// `CdgFrameView`, for incremental updates.
    pub fn render_tile_frame(&self, row: u8, col: u8, timestamp_ms: u64) -> CdgFrameView {
        let mut pixels = vec![0u8; TILE_W * TILE_H * 4];
        self.fill_tile_rgba(&mut pixels, row, col);
        CdgFrameView {
            pixels,
            width: TILE_W as u16,
            height: TILE_H as u16,
            timestamp_ms,
        }
    }

    /// Returns the number of packets processed so far.
    pub fn packets_read(&self) -> u32 {
        (self.cdg_data_pos / CDG_PACKET_SIZE) as u32
    }

    /// Returns `true` if all packet data has been consumed.
    pub fn is_eof(&self) -> bool {
        self.cdg_data_pos >= self.cdg_data.len()
    }

    // ------------------------------------------------------------------
    // Internal helpers
    // ------------------------------------------------------------------

    /// Read the next 24-byte packet; returns `None` at EOF.
    fn read_next_packet(&mut self) -> Option<CdgPacket> {
        let start = self.cdg_data_pos;
        if start + CDG_PACKET_SIZE > self.cdg_data.len() {
            self.cdg_data_pos = self.cdg_data.len();
            return None;
        }
        self.cdg_data_pos += CDG_PACKET_SIZE;
        let bytes = &self.cdg_data[start..start + CDG_PACKET_SIZE];
        CdgPacket::from_bytes(bytes)
    }

    /// Rebuild the surfarray from `pixel_indices` + `colour_table`.
    fn rebuild_surfarray(&mut self) {
        for y in 0..CDG_FULL_HEIGHT as usize {
            for x in 0..CDG_FULL_WIDTH as usize {
                let idx = self.pixel_indices[y][x] as usize;
                self.surfarray[y][x] = self.colour_table[idx];
            }
        }
    }

    // ------------------------------------------------------------------
    // Packet dispatch
    // ------------------------------------------------------------------

    fn process_packet(&mut self, pkt: &CdgPacket) {
        if (pkt.command & CDG_MASK) != CDG_COMMAND {
            return;
        }
        let inst = pkt.instruction & CDG_MASK;
        match inst {
            CDG_INST_MEMORY_PRESET => self.memory_preset(pkt),
            CDG_INST_BORDER_PRESET => self.border_preset(pkt),
            CDG_INST_TILE_BLOCK => self.tile_block_common(pkt, false),
            CDG_INST_SCROLL_PRESET => self.scroll_preset(pkt),
            CDG_INST_SCROLL_COPY => self.scroll_copy(pkt),
            CDG_INST_DEFINE_TRANSPARENT_COLOR => self.define_transparent_colour(pkt),
            CDG_INST_LOAD_COLOR_TABLE_0_7 => self.load_colour_table_common(pkt, 0),
            CDG_INST_LOAD_COLOR_TABLE_8_15 => self.load_colour_table_common(pkt, 1),
            CDG_INST_TILE_BLOCK_XOR => self.tile_block_common(pkt, true),
            _ => {
                // Unknown/unsupported command — ignore.
            }
        }
    }

    // ------------------------------------------------------------------
    // Command implementations
    // ------------------------------------------------------------------

    /// Memory Preset: Fill the entire 300×216 buffer with a single colour index.
    fn memory_preset(&mut self, pkt: &CdgPacket) {
        let colour = pkt.data[0] & 0x0F;
        if colour == self.just_cleared_colour_index as u8 {
            return;
        }
        self.just_cleared_colour_index = colour as i8;
        self.preset_colour_index = colour as i8;
        self.border_colour_index = colour as i8;

        // Fill pixel indices.
        for row in self.pixel_indices.iter_mut() {
            for px in row.iter_mut() {
                *px = colour;
            }
        }

        // Rebuild surfarray from indices.
        self.rebuild_surfarray();
        self.dirty_tiles = all_tiles_dirty();
    }

    /// Border Preset: Fill the border region only.
    fn border_preset(&mut self, pkt: &CdgPacket) {
        let colour = pkt.data[0] & 0x0F;
        if colour == self.border_colour_index as u8 {
            return;
        }
        self.border_colour_index = colour as i8;

        let fw = CDG_FULL_WIDTH as usize;   // 300
        let fh = CDG_FULL_HEIGHT as usize;  // 216

        // Top border: rows 0..11
        for y in 0..12 {
            for x in 0..fw {
                self.pixel_indices[y][x] = colour;
            }
        }
        // Bottom border: rows 204..215
        for y in (fh - 12)..fh {
            for x in 0..fw {
                self.pixel_indices[y][x] = colour;
            }
        }
        // Left border: columns 0..5, middle area
        for y in 12..(fh - 12) {
            for x in 0..6 {
                self.pixel_indices[y][x] = colour;
            }
        }
        // Right border: columns 294..299, middle area
        for y in 12..(fh - 12) {
            for x in (fw - 6)..fw {
                self.pixel_indices[y][x] = colour;
            }
        }

        self.rebuild_surfarray();
        self.dirty_tiles = all_tiles_dirty();
    }

    /// Scroll Preset: Scroll + fill new area with colour.
    fn scroll_preset(&mut self, pkt: &CdgPacket) {
        self.scroll_common(pkt, false);
    }

    /// Scroll Copy: Scroll + wrap scrolled-out area to opposite side.
    fn scroll_copy(&mut self, pkt: &CdgPacket) {
        self.scroll_common(pkt, true);
    }

    fn scroll_common(&mut self, pkt: &CdgPacket, copy: bool) {
        let d = &pkt.data;
        let colour = d[0] & 0x0F;
        let h_scroll = d[1] & 0x3F;
        let v_scroll = d[2] & 0x3F;
        let h_s_cmd = (h_scroll & 0x30) >> 4;
        let h_new_offset = h_scroll & 0x07;
        let v_s_cmd = (v_scroll & 0x30) >> 4;
        let v_new_offset = v_scroll & 0x0F;

        // Update offsets.
        let h_offset_changed = h_new_offset != self.h_offset || v_new_offset != self.v_offset;
        self.h_offset = h_new_offset.min(5);
        self.v_offset = v_new_offset.min(11);

        let v_px = calc_vertical_scroll(v_s_cmd);
        let h_px = calc_horizontal_scroll(h_s_cmd);

        if h_offset_changed {
            self.dirty_tiles = all_tiles_dirty();
        }

        if v_px == 0 && h_px == 0 {
            return;
        }

        if copy {
            self.apply_scroll_copy(v_px, h_px);
        } else {
            self.apply_scroll_preset(v_px, h_px, colour);
        }

        self.rebuild_surfarray();
        self.dirty_tiles = all_tiles_dirty();
    }

    /// Define Transparent Colour: mark a colour index as transparent (stored
    /// but not yet used for overlay).
    fn define_transparent_colour(&mut self, pkt: &CdgPacket) {
        self.transparent_colour_index = (pkt.data[0] & 0x0F) as i8;
    }

    /// Load Colour Table: load 8 entries into the palette.
    fn load_colour_table_common(&mut self, pkt: &CdgPacket, table: u8) {
        let start = if table == 0 { 0 } else { 8 };
        for i in 0..8 {
            let high = pkt.data[2 * i];
            let low = pkt.data[2 * i + 1];
            self.colour_table[start + i] = decode_colour_entry(high, low);
        }
        // Rebuild entire surfarray with new palette.
        self.rebuild_surfarray();
        self.dirty_tiles = all_tiles_dirty();
    }

    /// Tile Block (NORMAL or XOR): draw a 12×6 pixel tile.
    fn tile_block_common(&mut self, pkt: &CdgPacket, xor: bool) {
        let d = &pkt.data;

        // Some disks set bit 5 of byte 1 to mean "ignore".
        if d[1] & 0x20 != 0 && !xor {
            return;
        }

        let colour0 = d[0] & 0x0F;
        let colour1 = d[1] & 0x0F;

        let mut col_idx = (d[2] & 0x1F) as usize * 12;
        let mut row_idx = (d[3] & 0x3F) as usize * 6;

        // Bounds-check: clamp to full buffer dimensions.
        if col_idx > (CDG_FULL_HEIGHT as usize - 12) {
            col_idx = CDG_FULL_HEIGHT as usize - 12;
        }
        if row_idx > (CDG_FULL_WIDTH as usize - 6) {
            row_idx = CDG_FULL_WIDTH as usize - 6;
        }

        // Mark affected tiles dirty.
        self.update_tile_mask(row_idx, col_idx);

        // Draw the 12×6 tile.
        self.set_tile_pixels(d, row_idx, col_idx, colour0, colour1, xor);

        // A tile block means the screen has content; reset the memory-preset
        // optimisation so a subsequent clear is honoured.
        self.just_cleared_colour_index = -1;
    }

    fn update_tile_mask(&mut self, row_idx: usize, col_idx: usize) {
        // Col_idx is measured from the top in full-buffer coordinates.
        // The visible area starts at y=12.
        // Tile grid: (row, col) where row maps to x, col maps to y.
        let first_row = ((row_idx as i32 - 6 - self.h_offset as i32).max(0)) / TILE_W as i32;
        let last_row = ((row_idx as i32 - 1 - self.h_offset as i32)) / TILE_W as i32;
        let first_col = ((col_idx as i32 - 12 - self.v_offset as i32).max(0)) / TILE_H as i32;
        let last_col = ((col_idx as i32 - 1 - self.v_offset as i32)) / TILE_H as i32;

        // Clamp to valid tile range.
        let first_row = first_row.max(0).min((TILES_PER_ROW - 1) as i32) as u8;
        let last_row = last_row.max(0).min((TILES_PER_ROW - 1) as i32) as u8;
        let first_col = first_col.max(0).min((TILES_PER_COL - 1) as i32) as u8;
        let last_col = last_col.max(0).min((TILES_PER_COL - 1) as i32) as u8;

        for c in first_col..=last_col {
            for r in first_row..=last_row {
                set_tile_dirty(&mut self.dirty_tiles, r, c);
            }
        }
    }

    fn set_tile_pixels(
        &mut self,
        data: &[u8; 16],
        row_idx: usize,
        col_idx: usize,
        colour0: u8,
        colour1: u8,
        xor: bool,
    ) {
        for i in 0..12 {
            let byte = data[4 + i] & 0x3F;
            for j in 0..6 {
                let pixel = (byte >> (5 - j)) & 0x01;
                let new_col = if xor {
                    let xor_col = if pixel != 0 { colour1 } else { colour0 };
                    let current = self.pixel_indices[col_idx + i][row_idx + j];
                    current ^ xor_col
                } else {
                    if pixel != 0 { colour1 } else { colour0 }
                };
                self.pixel_indices[col_idx + i][row_idx + j] = new_col;
                self.surfarray[col_idx + i][row_idx + j] = self.colour_table[new_col as usize];
            }
        }
    }

    // ------------------------------------------------------------------
    // Scroll implementations
    // ------------------------------------------------------------------

    fn apply_scroll_copy(&mut self, v_px: i32, h_px: i32) {
        let fw = CDG_FULL_WIDTH as usize;
        let fh = CDG_FULL_HEIGHT as usize;

        // Circular shift: content that scrolls out one side wraps to the other.
        // Python equivalent:
        //   concat(original[:, v_px:], original[:, :v_px]) for vertical scroll
        // → src_y = (y + v_px) mod fh
        let mut tmp = [[0u8; CDG_FULL_WIDTH as usize]; CDG_FULL_HEIGHT as usize];
        for y in 0..fh {
            for x in 0..fw {
                let src_x = (x as i32 + h_px).rem_euclid(fw as i32) as usize;
                let src_y = (y as i32 + v_px).rem_euclid(fh as i32) as usize;
                tmp[y][x] = self.pixel_indices[src_y][src_x];
            }
        }
        self.pixel_indices = tmp;
    }

    fn apply_scroll_preset(&mut self, v_px: i32, h_px: i32, colour: u8) {
        // First apply a copy-scroll, then replace the wraparound area with
        // the fill colour.  This matches the Python two-step: concatenate
        // the stay region with a colour-filled block.
        self.apply_scroll_copy(v_px, h_px);

        let fw = CDG_FULL_WIDTH as usize;
        let fh = CDG_FULL_HEIGHT as usize;

        if v_px > 0 {
            // Bottom v_px rows get fill colour.
            for y in (fh - v_px as usize)..fh {
                for x in 0..fw {
                    self.pixel_indices[y][x] = colour;
                }
            }
        } else if v_px < 0 {
            let px = (-v_px) as usize;
            // Top px rows get fill colour.
            for y in 0..px {
                for x in 0..fw {
                    self.pixel_indices[y][x] = colour;
                }
            }
        } else if h_px > 0 {
            // Right h_px columns get fill colour.
            for y in 0..fh {
                for x in (fw - h_px as usize)..fw {
                    self.pixel_indices[y][x] = colour;
                }
            }
        } else if h_px < 0 {
            let px = (-h_px) as usize;
            // Left px columns get fill colour.
            for y in 0..fh {
                for x in 0..px {
                    self.pixel_indices[y][x] = colour;
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Free helper functions
// ---------------------------------------------------------------------------

fn calc_vertical_scroll(v_s_cmd: u8) -> i32 {
    match v_s_cmd {
        2 => 12,
        1 => -12,
        _ => 0,
    }
}

fn calc_horizontal_scroll(h_s_cmd: u8) -> i32 {
    match h_s_cmd {
        2 => 6,
        1 => -6,
        _ => 0,
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    // Helper: build a minimal valid CDG file with a sequence of packets.
    fn make_packet(instruction: u8, data: &[u8; 16]) -> [u8; 24] {
        let mut pkt = [0u8; 24];
        pkt[0] = CDG_COMMAND;
        pkt[1] = instruction;
        pkt[8..24].copy_from_slice(data);
        pkt
    }

    fn make_packet_short(instruction: u8, data: &[u8]) -> [u8; 24] {
        let mut d = [0u8; 16];
        let len = data.len().min(16);
        d[..len].copy_from_slice(&data[..len]);
        make_packet(instruction, &d)
    }

    /// Build a CDG byte sequence from packet arrays.
    fn pack(packets: &[[u8; 24]]) -> Vec<u8> {
        let mut v = Vec::with_capacity(packets.len() * 24);
        for p in packets {
            v.extend_from_slice(p);
        }
        v
    }

    #[test]
    fn test_new_decoder_default_state() {
        let data = vec![0u8; 24]; // one empty packet
        let dec = CdgPacketDecoder::new(data);
        assert_eq!(dec.packets_read(), 0);
        assert!(!dec.is_eof());
        assert_eq!(dec.h_offset, 0);
        assert_eq!(dec.v_offset, 0);
        assert_eq!(dec.get_border_colour(), None);
        // All pixels should be index 0, colour table entry 0 = Rgb(0,0,0)
        assert_eq!(dec.pixel_indices[0][0], 0);
    }

    #[test]
    fn test_rewind_resets_state() {
        let mut dec = CdgPacketDecoder::new(vec![0u8; 48]);
        dec.cdg_data_pos = 24;
        assert_eq!(dec.packets_read(), 1);
        dec.rewind();
        assert_eq!(dec.packets_read(), 0);
        assert_eq!(dec.h_offset, 0);
        assert_eq!(dec.v_offset, 0);
    }

    #[test]
    fn test_memory_preset_sets_all_pixels() {
        let data = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x03]);
        let cdg = pack(&[data]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(1); // process the memory preset
        // Every pixel should be colour index 3
        for y in 0..CDG_FULL_HEIGHT as usize {
            for x in 0..CDG_FULL_WIDTH as usize {
                assert_eq!(dec.pixel_indices[y][x], 3, "pixel ({},{})", x, y);
            }
        }
        // Border colour should be set
        assert_eq!(dec.border_colour_index, 3);
    }

    #[test]
    fn test_memory_preset_skip_repeat() {
        let p1 = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x05]);
        let p2 = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x05]); // should be skipped
        let cdg = pack(&[p1, p2]);
        let mut dec = CdgPacketDecoder::new(cdg);
        assert!(dec.do_packets(2));
        // All pixels should be 5
        assert_eq!(dec.pixel_indices[0][0], 5);
        assert_eq!(dec.just_cleared_colour_index, 5);
    }

    #[test]
    fn test_memory_preset_different_colour() {
        let p1 = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x02]);
        let p2 = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x07]); // different
        let cdg = pack(&[p1, p2]);
        let mut dec = CdgPacketDecoder::new(cdg);
        assert!(dec.do_packets(2));
        assert_eq!(dec.pixel_indices[100][100], 7);
    }

    #[test]
    fn test_border_preset_sets_border_only() {
        let mp = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x00]);
        let bp = make_packet_short(CDG_INST_BORDER_PRESET, &[0x0A]);
        let cdg = pack(&[mp, bp]);
        let mut dec = CdgPacketDecoder::new(cdg);
        assert!(dec.do_packets(2));

        let fw = CDG_FULL_WIDTH as usize;
        let fh = CDG_FULL_HEIGHT as usize;

        // Top border: rows 0..11 should be 0x0A
        for y in 0..12 {
            for x in 0..fw {
                assert_eq!(dec.pixel_indices[y][x], 0x0A, "top border ({},{})", x, y);
            }
        }
        // Bottom border: rows 204..215 should be 0x0A
        for y in (fh - 12)..fh {
            for x in 0..fw {
                assert_eq!(dec.pixel_indices[y][x], 0x0A, "bottom border ({},{})", x, y);
            }
        }
        // Left border: cols 0..5, middle rows
        for y in 12..(fh - 12) {
            for x in 0..6 {
                assert_eq!(dec.pixel_indices[y][x], 0x0A, "left border ({},{})", x, y);
            }
        }
        // Right border: cols 294..299, middle rows
        for y in 12..(fh - 12) {
            for x in (fw - 6)..fw {
                assert_eq!(dec.pixel_indices[y][x], 0x0A, "right border ({},{})", x, y);
            }
        }
        // Center pixel (visible area) should still be 0
        assert_eq!(dec.pixel_indices[100][100], 0);
    }

    #[test]
    fn test_load_colour_table() {
        // Load colours 0-7: set each to a different RGB.
        let mut data = [0u8; 16];
        for i in 0..8 {
            // Each entry: high byte = (i << 2), low byte = (i << 2)
            // This produces a predictable colour.
            data[2 * i] = (i as u8) << 2;
            data[2 * i + 1] = (i as u8) << 2;
        }
        let pkt = make_packet(CDG_INST_LOAD_COLOR_TABLE_0_7, &data);
        let cdg = pack(&[pkt]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(1);
        // First entry: high=0, low=0 → entry=0 → R=0,G=0,B=0
        assert_eq!(dec.colour_table[0], Rgb { r: 0, g: 0, b: 0 });
        // Second entry: high=1<<2=4, low=4
        // entry = ((4<<8)|4) = 1028
        // entry = ((1028&0x3F00)>>2)|(1028&0x003F) = (1024>>2)|4 = 256|4 = 260
        // R = ((260&0x0F00)>>8)*17 = (256>>8)*17 = 1*17 = 17
        // G = ((260&0x00F0)>>4)*17 = 0*17 = 0
        // B = (260&0x000F)*17 = 4*17 = 68
        let expected = Rgb { r: 17, g: 0, b: 68 };
        assert_eq!(dec.colour_table[1], expected);
    }

    #[test]
    fn test_load_colour_table_8_15() {
        let mut data = [0u8; 16];
        // Set entry 8 (index 0 in this packet) to a known colour.
        // high byte bits: --RRRR--
        let high = (0x0F << 2) as u8; // R = 15 → R=255
        let low = (0x0F << 2) as u8; // B=15 → B=255, G=15 → G=255
        data[0] = high;
        data[1] = low;
        let pkt = make_packet(CDG_INST_LOAD_COLOR_TABLE_8_15, &data);
        let cdg = pack(&[pkt]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(1);
        // Expected: entry = ((0x3C<<8)|0x3C) = 0x3C3C
        // (((0x3C3C & 0x3F00) >> 2) | (0x3C3C & 0x003F))
        // = (0x3C00 >> 2) | 0x003C = 0x0F00 | 0x003C = 0x0F3C
        // R = ((0x0F3C & 0x0F00) >> 8) * 17 = (0x0F00 >> 8) * 17 = 15 * 17 = 255
        // G = ((0x0F3C & 0x00F0) >> 4) * 17 = (0x0030 >> 4) * 17 = 3 * 17 = 51
        // B = (0x0F3C & 0x000F) * 17 = 12 * 17 = 204
        assert_eq!(
            dec.colour_table[8],
            Rgb { r: 255, g: 51, b: 204 }
        );
    }

    #[test]
    fn test_load_colour_table_redraws_screen() {
        // Memory preset to colour 1, then load colour table to change what
        // colour 1 looks like.
        let mp = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x01]);
        // Load colour table 0-7: set entry 1 to bright red.
        let mut ct_data = [0u8; 16];
        // Entry 1 is at bytes 2,3. Set R=15, G=0, B=0.
        // high byte: --1111-- = 0x3C, low byte: --0000-- = 0x00
        ct_data[2] = 0x3C; // high byte for entry 1
        ct_data[3] = 0x00; // low byte
        let ct = make_packet(CDG_INST_LOAD_COLOR_TABLE_0_7, &ct_data);
        let cdg = pack(&[mp, ct]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(2);
        // Pixel (100,100) should now have the colour table entry 1 mapped
        // through the new colour = bright red: R=255, G=0, B=0
        assert_eq!(dec.surfarray[100][100], Rgb { r: 255, g: 0, b: 0 });
    }

    #[test]
    fn test_tile_block_normal() {
        // Draw a simple tile where the first row has pixel (0) set.
        let mut data = [0u8; 16];
        data[0] = 0x01; // colour0 = 1
        data[1] = 0x02; // colour1 = 2 (but we won't use it in this test)
        data[2] = 0x00; // column index = 0 * 12 = 0
        data[3] = 0x00; // row index = 0 * 6 = 0
        data[4] = 0x01; // first row: bit 0 = 1 → colour1 = 2
        // All other rows = 0 → colour0 = 1
        let pkt = make_packet(CDG_INST_TILE_BLOCK, &data);
        let cdg = pack(&[pkt]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(1);
        // Pixel at (row=0, col=0) = first row, first pixel, bit 0 of byte 4 = bit 5 → 0 → colour0
        assert_eq!(dec.pixel_indices[0][0], 1);
        // Pixel at (row=0, col=5) = first row, last pixel, bit 5 of byte 4 = bit 0 → 1 → colour1
        assert_eq!(dec.pixel_indices[0][5], 2);
        // Row 1 should be all colour0
        assert_eq!(dec.pixel_indices[1][0], 1);
        assert_eq!(dec.pixel_indices[1][5], 1);
    }

    #[test]
    fn test_tile_block_xor() {
        // Set background to colour 3, then XOR a tile with colour 1.
        let mp = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x03]);
        let mut data = [0u8; 16];
        data[0] = 0x01; // colour0 = 1
        data[1] = 0x02; // colour1 = 2
        data[2] = 0x00;
        data[3] = 0x00;
        data[4] = 0x3F; // all 6 pixels set → colour1 = 2 for each
        let tb = make_packet(CDG_INST_TILE_BLOCK_XOR, &data);
        let cdg = pack(&[mp, tb]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(2);
        // Background was 3, XOR with 2 = 3 ^ 2 = 1
        assert_eq!(dec.pixel_indices[0][0], 3 ^ 2); // = 1
    }

    #[test]
    fn test_tile_block_out_of_bounds_clamped() {
        // Send a tile block with coordinates way beyond the buffer.
        let mut data = [0u8; 16];
        data[0] = 0x01;
        data[1] = 0x02;
        data[2] = 0xFF; // column index = 0x1F * 12 = 372, clamped to 204
        data[3] = 0xFF; // row index = 0x3F * 6 = 378, clamped to 294
        let pkt = make_packet(CDG_INST_TILE_BLOCK, &data);
        let cdg = pack(&[pkt]);
        let mut dec = CdgPacketDecoder::new(cdg);
        // Should not panic
        dec.do_packets(1);
        // The tile should be drawn at the clamped position.
        assert_eq!(
            dec.pixel_indices[CDG_FULL_HEIGHT as usize - 12][CDG_FULL_WIDTH as usize - 6],
            1
        );
    }

    #[test]
    fn test_scroll_copy_vertical() {
        // Create a pattern, then scroll copy upward.
        let mp = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x00]);
        // Draw a tile at vertical position 48 (col_idx), horizontal 0 (row_idx)
        let mut tb_data = [0u8; 16];
        tb_data[0] = 0x05; // colour0 = 5
        tb_data[1] = 0x05; // colour1 = 5
        tb_data[2] = ((50 / 12) as u8) & 0x1F; // 4 → col_idx = 4*12 = 48
        tb_data[3] = ((0 / 6) as u8) & 0x3F;  // 0 → row_idx = 0*6 = 0
        tb_data[4] = 0x3F; // first row: all 6 pixels set → colour1=5
        let tb = make_packet(CDG_INST_TILE_BLOCK, &tb_data);
        // Scroll copy: v_s_cmd=2 → +12 pixels (up)
        let sc_data = [0x00, 0x00, 0x20]; // v_s_cmd = 2 (bits 5,4 = 10 = 2)
        let sc = make_packet_short(CDG_INST_SCROLL_COPY, &sc_data);
        let cdg = pack(&[mp, tb, sc]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(3);
        // After scroll up by 12: tile at y=48..59 → y=36..47
        // pixel at y=36, x=0 should have colour 5 (moved from y=48, x=0)
        assert_eq!(dec.pixel_indices[36][0], 5);
        // Pixel that was at y=48 and wrapped around should be at y=216-12+48 = 252?
        // No, the wrap: src y=0 wraps to (y+v_px)%fh
        //   dest[(0-12)%216] = dest[204] ← src[0]
        //   It's a circular shift, not just wrapping the tile
        // Let's just verify the tile moved up by 12
        assert_eq!(dec.pixel_indices[47][0], 5); // last row of the moved tile
        assert_eq!(dec.pixel_indices[48][0], 0); // old position cleared
    }

    #[test]
    fn test_scroll_preset_vertical() {
        let mp = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x00]);
        let mut tb_data = [0u8; 16];
        tb_data[0] = 0x07;
        tb_data[1] = 0x07;
        tb_data[2] = 0x00;
        tb_data[3] = ((100 / 6) as u8) & 0x3F;
        tb_data[4] = 0x3F;
        let tb = make_packet(CDG_INST_TILE_BLOCK, &tb_data);
        // Scroll preset: v_s_cmd=2 (+12 up), colour=0x0A
        let sp_data = [0x0A, 0x00, 0x20];
        let sp = make_packet_short(CDG_INST_SCROLL_PRESET, &sp_data);
        let cdg = pack(&[mp, tb, sp]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(3);
        // The bottom 12 rows should be filled with colour 0x0A
        for y in (CDG_FULL_HEIGHT as usize - 12)..CDG_FULL_HEIGHT as usize {
            for x in 0..CDG_FULL_WIDTH as usize {
                assert_eq!(dec.pixel_indices[y][x], 0x0A,
                    "preset scroll fill at ({},{})", x, y);
            }
        }
    }

    #[test]
    fn test_dirty_tiles_after_memory_preset() {
        let pkt = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x01]);
        let cdg = pack(&[pkt]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(1);
        let tiles = dec.get_dirty_tiles();
        assert_eq!(tiles.len(), 24, "all 24 tiles should be dirty");
    }

    #[test]
    fn test_dirty_tiles_reset_after_read() {
        let mut dec = CdgPacketDecoder::new(vec![0u8; 24]);
        dec.dirty_tiles = all_tiles_dirty();
        let tiles = dec.get_dirty_tiles();
        assert_eq!(tiles.len(), 24);
        let tiles2 = dec.get_dirty_tiles();
        assert!(tiles2.is_empty());
    }

    #[test]
    fn test_tile_dirty_mask() {
        let mut mask: u32 = 0;
        set_tile_dirty(&mut mask, 2, 1);
        assert!(mask & ((1u32 << 2) << (1 * 8)) != 0);
        let tiles = drain_dirty_tiles(&mut mask);
        assert_eq!(tiles, vec![(2, 1)]);
    }

    #[test]
    fn test_render_frame_produces_correct_size() {
        let dec = CdgPacketDecoder::new(vec![0u8; 24]);
        let frame = dec.render_frame(0);
        assert_eq!(frame.width, CDG_DISPLAY_WIDTH);
        assert_eq!(frame.height, CDG_DISPLAY_HEIGHT);
        assert_eq!(frame.pixels.len(), CDG_DISPLAY_WIDTH as usize * CDG_DISPLAY_HEIGHT as usize * 4);
        assert_eq!(frame.timestamp_ms, 0);
    }

    #[test]
    fn test_render_frame_after_memory_preset() {
        let pkt = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x03]);
        // Also load a colour table so that colour 3 is visible.
        let mut ct_data = [0u8; 16];
        // Set entry 3 (bytes 6,7) to bright green: R=0, G=15, B=0
        ct_data[6] = 0x00;
        ct_data[7] = 0x0F;
        let ct = make_packet(CDG_INST_LOAD_COLOR_TABLE_0_7, &ct_data);
        let cdg = pack(&[ct, pkt]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(2);
        let frame = dec.render_frame(1234);
        assert_eq!(frame.timestamp_ms, 1234);
        // All visible pixels should be the mapped colour for index 3.
        // Entry 3: high=0, low=0x0F → entry = (0<<8)|0x0F = 0x0F
        // ((0x0F&0x3F00)>>2) | (0x0F&0x003F) = 0 | 0x0F = 0x0F
        // R=0, G=0, B=15*17=255 → Rgb(0, 0, 255)
        // Wait: entry 3 is at bytes 6,7 of the ct_data...
        // Actually, let me recalculate. Entry index=3, so 2*3=6 → data[6]=high, data[7]=low
        // high=0, low=0x0F
        // entry = (0<<8) | 0x0F = 0x0F
        // entry = ((0x0F & 0x3F00) >> 2) | (0x0F & 0x003F) = 0 | 0x0F = 0x0F
        // R = ((0x0F & 0x0F00) >> 8) * 17 = 0
        // G = ((0x0F & 0x00F0) >> 4) * 17 = 0
        // B = (0x0F & 0x000F) * 17 = 15 * 17 = 255
        assert_eq!(frame.pixels[0], 0);   // R
        assert_eq!(frame.pixels[1], 0);   // G
        assert_eq!(frame.pixels[2], 255); // B
        assert_eq!(frame.pixels[3], 255); // A
    }

    #[test]
    fn test_seek_to_packet() {
        let pkt = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x05]);
        let cdg = pack(&[pkt, pkt, pkt]); // 3 packets, 72 bytes
        let mut dec = CdgPacketDecoder::new(cdg);
        // Seek to packet 1 (process first packet) → memory preset to 5
        dec.seek_to_packet(1);
        assert_eq!(dec.pixel_indices[50][50], 5);
        assert_eq!(dec.packets_read(), 1);
    }

    #[test]
    fn test_is_eof() {
        let cdg = vec![0u8; 24];
        let mut dec = CdgPacketDecoder::new(cdg);
        assert!(!dec.is_eof());
        dec.do_packets(1);
        assert!(dec.is_eof());
    }

    #[test]
    fn test_do_packets_returns_false_at_eof() {
        let cdg = vec![0u8; 24];
        let mut dec = CdgPacketDecoder::new(cdg);
        assert!(dec.do_packets(1));  // one packet available
        assert!(!dec.do_packets(1)); // no more packets
    }

    #[test]
    fn test_do_packets_zero() {
        let mut dec = CdgPacketDecoder::new(vec![0u8; 24]);
        assert!(dec.do_packets(0));
        assert_eq!(dec.packets_read(), 0);
    }

    #[test]
    fn test_eof_on_empty_data() {
        let mut dec = CdgPacketDecoder::new(vec![]);
        assert!(dec.is_eof());
        let result = dec.do_packets(1);
        assert!(!result);
    }

    #[test]
    fn test_fill_tile_rgba_bounds() {
        let mp = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x01]);
        let cdg = pack(&[mp]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(1);
        let mut buf = vec![0u8; TILE_W * TILE_H * 4];
        dec.fill_tile_rgba(&mut buf, 0, 0);
        // All pixels should be colour index 1, but we haven't set a colour table
        // so it defaults to Rgb(0,0,0). Let's set colour 1 first.
        // Actually, the colour table entry 1 defaults to (0,0,0).
        assert_eq!(buf[0], 0);
    }

    #[test]
    fn test_scroll_copy_horizontal() {
        let mp = make_packet_short(CDG_INST_MEMORY_PRESET, &[0x00]);
        // Draw a tile at vertical pos 0, horizontal pos 0 (row_idx=0, col_idx=0)
        let mut tb_data = [0u8; 16];
        tb_data[0] = 0x07; // colour0 = 7
        tb_data[1] = 0x07; // colour1 = 7
        tb_data[2] = ((50 / 12) as u8) & 0x1F; // 4 → col_idx = 48 (vertical)
        tb_data[3] = ((0 / 6) as u8) & 0x3F;  // 0 → row_idx = 0 (horizontal)
        tb_data[4] = 0x3F; // first row: all 6 pixels set → colour1=7
        let tb = make_packet(CDG_INST_TILE_BLOCK, &tb_data);
        // Scroll copy: h_s_cmd=2 → +6 pixels (left)
        // data: [colour=0, h_scroll, v_scroll]
        // h_scroll = 0x20 → h_s_cmd=2 (bits 5,4), h_offset=0
        let sc = make_packet_short(CDG_INST_SCROLL_COPY, &[0x00, 0x20, 0x00]);
        let cdg = pack(&[mp, tb, sc]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(3);
        // After scroll left by 6: tile at x=0..5 → x=294..299
        // dest[y][x] = src[y][(x+6)%300]
        // dest[48][294] = src[48][(294+6)%300] = src[48][0] = 7
        assert_eq!(dec.pixel_indices[48][294], 7);
        // Old position x=0 should have scrolled-in content (from x=6, which was 0)
        assert_eq!(dec.pixel_indices[48][0], 0);
    }

    #[test]
    fn test_define_transparent_colour() {
        let pkt = make_packet_short(CDG_INST_DEFINE_TRANSPARENT_COLOR, &[0x09]);
        let cdg = pack(&[pkt]);
        let mut dec = CdgPacketDecoder::new(cdg);
        dec.do_packets(1);
        assert_eq!(dec.transparent_colour_index, 9);
    }

    #[test]
    fn test_unknown_instruction_is_ignored() {
        let pkt = make_packet_short(42, &[0x00; 16]); // no such instruction
        let cdg = pack(&[pkt]);
        let mut dec = CdgPacketDecoder::new(cdg);
        // Should not panic, just ignore.
        dec.do_packets(1);
        // State unchanged
        assert_eq!(dec.just_cleared_colour_index, -1);
    }

    #[test]
    fn test_render_tile_frame() {
        let dec = CdgPacketDecoder::new(vec![0u8; 24]);
        let frame = dec.render_tile_frame(0, 0, 500);
        assert_eq!(frame.width, 48);
        assert_eq!(frame.height, 48);
        assert_eq!(frame.timestamp_ms, 500);
        assert_eq!(frame.pixels.len(), 48 * 48 * 4);
    }

    #[test]
    fn test_full_pipeline_no_crash() {
        // Build a realistic CDG sequence with colour table + memory preset +
        // border + tile blocks.
        let mut packets = Vec::new();

        // Load colour table 0-7
        let mut ct = [0u8; 16];
        ct[0] = 0x00; ct[1] = 0x00; // entry 0: black
        ct[2] = 0x3C; ct[3] = 0x00; // entry 1: red
        ct[4] = 0x00; ct[5] = 0x3C; // entry 2: blue
        ct[6] = 0x00; ct[7] = 0x0F; // entry 3: green-ish
        packets.push(make_packet(CDG_INST_LOAD_COLOR_TABLE_0_7, &ct));

        // Memory preset to colour 1 (red)
        packets.push(make_packet_short(CDG_INST_MEMORY_PRESET, &[0x01]));

        // Border preset to colour 2 (blue)
        packets.push(make_packet_short(CDG_INST_BORDER_PRESET, &[0x02]));

        // A few tile blocks
        for t in 0..3 {
            let mut td = [0u8; 16];
            td[0] = 0x03; td[1] = 0x01;
            td[2] = (t as u8) & 0x1F;
            td[3] = (t as u8) & 0x3F;
            td[4] = 0x2A; // random pixel pattern
            packets.push(make_packet(CDG_INST_TILE_BLOCK, &td));
        }

        let cdg = pack(&packets);
        let mut dec = CdgPacketDecoder::new(cdg);
        // Process all packets
        assert!(dec.do_packets(packets.len() as u32));
        // Render a frame
        let frame = dec.render_frame(1000);
        assert_eq!(frame.pixels.len(), 288 * 192 * 4);
        // Should have some colour data
        let has_nonzero = frame.pixels.iter().any(|&b| b != 0);
        assert!(has_nonzero, "frame should have non-zero pixel data");
    }
}
