//! MPEG format constants and definitions.
//!
//! Mirrors `src/pykaraoke/players/mpg.py`.

/// Default external player command for Windows.
pub const DEFAULT_WINDOWS_PLAYER: &str =
    r#"C:\Program Files\Windows Media Player\wmplayer.exe" "%(file)s" /play /close /fullscreen"#;

/// Default external player command for Linux/GP2X.
pub const DEFAULT_LINUX_PLAYER: &str = r#"mplayer -fs "%(file)s""#;

/// Default external player command for GP2X.
pub const DEFAULT_GP2X_PLAYER: &str = r#"./mplayer_cmdline "%(file)s""#;

/// MPEG sync word byte 1 (0x00).
pub const MPEG_SYNC_WORD_1: u8 = 0xFF;

/// MPEG sync word byte 2 (top 3 bits = 0x7, i.e. 0xE0 mask).
pub const MPEG_SYNC_WORD_2_MASK: u8 = 0xE0;

/// MPEG version 1 ID.
pub const MPEG_VERSION_1: u8 = 3;

/// MPEG version 2 ID.
pub const MPEG_VERSION_2: u8 = 2;

/// MPEG version 2.5 ID.
pub const MPEG_VERSION_2_5: u8 = 0;

/// MPEG layer 3.
pub const MPEG_LAYER_3: u8 = 1;

/// MPEG layer 2.
pub const MPEG_LAYER_2: u8 = 2;

/// MPEG layer 1.
pub const MPEG_LAYER_1: u8 = 3;

/// Supported MPEG video file extensions.
pub const MPEG_VIDEO_EXTENSIONS: &[&str] = &[".mpg", ".mpeg", ".avi", ".divx", ".xvid"];

/// Supported MPEG audio file extensions.
pub const MPEG_AUDIO_EXTENSIONS: &[&str] = &[".mp3", ".ogg"];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mpeg_sync_word() {
        assert_eq!(MPEG_SYNC_WORD_1, 0xFF);
        assert_eq!(MPEG_SYNC_WORD_2_MASK, 0xE0);
    }

    #[test]
    fn test_mpeg_versions() {
        assert_eq!(MPEG_VERSION_1, 3);
        assert_eq!(MPEG_VERSION_2, 2);
        assert_eq!(MPEG_VERSION_2_5, 0);
    }

    #[test]
    fn test_mpeg_layers() {
        assert_eq!(MPEG_LAYER_1, 3);
        assert_eq!(MPEG_LAYER_2, 2);
        assert_eq!(MPEG_LAYER_3, 1);
    }

    #[test]
    fn test_video_extensions() {
        assert!(MPEG_VIDEO_EXTENSIONS.contains(&".mpg"));
        assert!(MPEG_VIDEO_EXTENSIONS.contains(&".avi"));
    }

    #[test]
    fn test_audio_extensions() {
        assert!(MPEG_AUDIO_EXTENSIONS.contains(&".mp3"));
        assert!(MPEG_AUDIO_EXTENSIONS.contains(&".ogg"));
    }
}
