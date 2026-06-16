//! CD+G format constants and definitions.
//!
//! Mirrors `src/pykaraoke/players/cdg_aux.py` and
//! `src/pykaraoke/players/cdg.py`.

/// CDG command byte value.
pub const CDG_COMMAND: u8 = 0x09;

/// CDG mask byte value.
pub const CDG_MASK: u8 = 0x3F;

/// Full CDG buffer width (300 pixels).
pub const CDG_FULL_WIDTH: u16 = 300;

/// Full CDG buffer height (216 pixels).
pub const CDG_FULL_HEIGHT: u16 = 216;

/// Visible display width (288 pixels).
pub const CDG_DISPLAY_WIDTH: u16 = 288;

/// Visible display height (192 pixels).
pub const CDG_DISPLAY_HEIGHT: u16 = 192;

/// Number of entries in the color table.
pub const COLOUR_TABLE_SIZE: usize = 16;

/// CDG packet size in bytes (24 bytes).
pub const CDG_PACKET_SIZE: usize = 24;

/// CDG instruction codes.
pub const CDG_INST_MEMORY_PRESET: u8 = 1;
pub const CDG_INST_BORDER_PRESET: u8 = 2;
pub const CDG_INST_TILE_BLOCK: u8 = 6;
pub const CDG_INST_SCROLL_PRESET: u8 = 20;
pub const CDG_INST_SCROLL_COPY: u8 = 24;
pub const CDG_INST_DEFINE_TRANSPARENT_COLOR: u8 = 28;
pub const CDG_INST_LOAD_COLOR_TABLE_0_7: u8 = 30;
pub const CDG_INST_LOAD_COLOR_TABLE_8_15: u8 = 31;
pub const CDG_INST_TILE_BLOCK_XOR: u8 = 38;

/// Number of tiles horizontally (6).
pub const CDG_TILES_HORIZONTAL: u16 = 6;

/// Number of tiles vertically (4).
pub const CDG_TILES_VERTICAL: u16 = 4;

/// Tile width in pixels (48).
pub const CDG_TILE_WIDTH: u16 = CDG_DISPLAY_WIDTH / CDG_TILES_HORIZONTAL;

/// Tile height in pixels (48).
pub const CDG_TILE_HEIGHT: u16 = CDG_DISPLAY_HEIGHT / CDG_TILES_VERTICAL;

/// A single CDG packet (24 bytes).
#[derive(Debug, Clone, Copy)]
pub struct CdgPacket {
    pub command: u8,
    pub instruction: u8,
    pub data: [u8; 16],
}

impl CdgPacket {
    /// Parse a 24-byte CDG packet from raw bytes.
    pub fn from_bytes(bytes: &[u8]) -> Option<Self> {
        if bytes.len() < 24 {
            return None;
        }

        let mut data = [0u8; 16];
        data.copy_from_slice(&bytes[8..24]);

        Some(Self {
            command: bytes[0] & CDG_MASK,
            instruction: bytes[1] & CDG_MASK,
            data,
        })
    }

    /// Check if this packet has the CDG command byte.
    pub fn is_cdg(&self) -> bool {
        self.command == CDG_COMMAND
    }
}

/// CDG color table entry (RGB).
#[derive(Debug, Clone, Copy, Default)]
pub struct CdgColor {
    pub r: u8,
    pub g: u8,
    pub b: u8,
}

/// CDG display state.
#[derive(Debug, Clone)]
pub struct CdgDisplay {
    /// Full 300x216 pixel buffer.
    pub pixels: [[u8; CDG_FULL_WIDTH as usize]; CDG_FULL_HEIGHT as usize],
    /// Color table (16 entries).
    pub color_table: [CdgColor; COLOUR_TABLE_SIZE],
}

impl Default for CdgDisplay {
    fn default() -> Self {
        Self {
            pixels: [[0u8; CDG_FULL_WIDTH as usize]; CDG_FULL_HEIGHT as usize],
            color_table: [CdgColor::default(); COLOUR_TABLE_SIZE],
        }
    }
}

/// Display zoom modes (mirrors Python).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ZoomMode {
    Quick,
    Int,
    Full,
    Soft,
    None,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cdg_constants() {
        assert_eq!(CDG_COMMAND, 0x09);
        assert_eq!(CDG_MASK, 0x3F);
        assert_eq!(CDG_PACKET_SIZE, 24);
        assert_eq!(CDG_FULL_WIDTH, 300);
        assert_eq!(CDG_FULL_HEIGHT, 216);
        assert_eq!(CDG_DISPLAY_WIDTH, 288);
        assert_eq!(CDG_DISPLAY_HEIGHT, 192);
        assert_eq!(COLOUR_TABLE_SIZE, 16);
    }

    #[test]
    fn test_tile_dimensions() {
        assert_eq!(CDG_TILES_HORIZONTAL, 6);
        assert_eq!(CDG_TILES_VERTICAL, 4);
        assert_eq!(CDG_TILE_WIDTH, 48);
        assert_eq!(CDG_TILE_HEIGHT, 48);
    }

    #[test]
    fn test_cdg_packet_parsing() {
        let mut raw = [0u8; 24];
        raw[0] = 0x09; // command
        raw[1] = 0x01; // instruction (memory preset)

        let packet = CdgPacket::from_bytes(&raw).unwrap();
        assert!(packet.is_cdg());
        assert_eq!(packet.instruction, 0x01);
    }

    #[test]
    fn test_cdg_packet_too_short() {
        let raw = [0u8; 16];
        assert!(CdgPacket::from_bytes(&raw).is_none());
    }

    #[test]
    fn test_cdg_instruction_constants() {
        assert_eq!(CDG_INST_MEMORY_PRESET, 1);
        assert_eq!(CDG_INST_BORDER_PRESET, 2);
        assert_eq!(CDG_INST_TILE_BLOCK, 6);
        assert_eq!(CDG_INST_SCROLL_PRESET, 20);
        assert_eq!(CDG_INST_SCROLL_COPY, 24);
        assert_eq!(CDG_INST_DEFINE_TRANSPARENT_COLOR, 28);
        assert_eq!(CDG_INST_LOAD_COLOR_TABLE_0_7, 30);
        assert_eq!(CDG_INST_LOAD_COLOR_TABLE_8_15, 31);
        assert_eq!(CDG_INST_TILE_BLOCK_XOR, 38);
    }
}
