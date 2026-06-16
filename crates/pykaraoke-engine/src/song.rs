//! Song data structures.
//!
//! Mirrors `SongStruct`, `SongData`, `TitleStruct` from
//! `src/pykaraoke/core/database.py`.

use serde::{Deserialize, Serialize};
use std::path::Path;

/// Supported karaoke file extensions.
#[derive(Debug, Clone)]
pub struct SupportedExtensions {
    pub cdg: Vec<String>,
    pub kar: Vec<String>,
    pub mpg: Vec<String>,
}

impl Default for SupportedExtensions {
    fn default() -> Self {
        Self {
            cdg: vec![".cdg".to_string()],
            kar: vec![".kar".to_string(), ".mid".to_string()],
            mpg: vec![
                ".mpg".to_string(),
                ".mpeg".to_string(),
                ".avi".to_string(),
                ".divx".to_string(),
                ".xvid".to_string(),
                ".mp3".to_string(),
                ".ogg".to_string(),
            ],
        }
    }
}

impl SupportedExtensions {
    pub fn all(&self) -> Vec<&str> {
        let mut exts: Vec<&str> = Vec::new();
        for e in &self.cdg {
            exts.push(e);
        }
        for e in &self.kar {
            exts.push(e);
        }
        for e in &self.mpg {
            exts.push(e);
        }
        exts
    }

    pub fn is_valid(&self, extension: &str) -> bool {
        let ext = extension.to_lowercase();
        if ext.is_empty() {
            return false;
        }
        self.cdg.contains(&ext) || self.kar.contains(&ext) || self.mpg.contains(&ext)
    }
}

/// A single karaoke song entry, mirroring `SongStruct` from the Python database.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SongStruct {
    /// Display filename (basename)
    pub display_filename: String,
    /// Full file path
    pub filepath: String,
    /// ZIP member path (if inside a ZIP archive)
    pub zip_stored_name: Option<String>,
    /// Parsed or user-provided title
    pub title: String,
    /// Parsed or user-provided artist
    pub artist: String,
    /// Disc identifier
    pub disc: String,
    /// Track number
    pub track: String,
    /// File extension
    pub extension: String,
    /// Audio file path (CD+G only — separate .mp3/.ogg)
    pub audio_filepath: Option<String>,
    /// Song length in seconds (0 if unknown)
    pub length: f64,
    /// SHA-256 hash of file contents (for duplicate detection)
    pub file_hash: Option<String>,
}

impl SongStruct {
    /// Create a new `SongStruct` from a file path.
    /// Parses the filename to extract artist/title/disc/track.
    pub fn from_filepath(filepath: &str) -> Self {
        let path = Path::new(filepath);
        let display_filename = path
            .file_name()
            .map(|s| s.to_string_lossy().to_string())
            .unwrap_or_default();
        let extension = path
            .extension()
            .map(|s| format!(".{}", s.to_string_lossy().to_lowercase()))
            .unwrap_or_default();

        Self {
            display_filename,
            filepath: filepath.to_string(),
            zip_stored_name: None,
            title: String::new(),
            artist: String::new(),
            disc: String::new(),
            track: String::new(),
            extension,
            audio_filepath: None,
            length: 0.0,
            file_hash: None,
        }
    }

    /// Build a display string like `"Artist - Title"`.
    pub fn display_name(&self) -> String {
        if !self.artist.is_empty() {
            format!("{} - {}", self.artist, self.title)
        } else {
            self.title.clone()
        }
    }
}

/// Title file entry from `titles.txt`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TitleStruct {
    pub filepath: String,
    pub title: String,
    pub artist: String,
}

/// Song file data reference (from `SongStruct.get_song_datas()`).
#[derive(Debug, Clone)]
pub struct SongData {
    /// The karaoke data file (CDG, KAR, or MPG)
    pub data_filepath: String,
    /// Optional audio file (for CD+G: separate .mp3/.ogg)
    pub audio_filepath: Option<String>,
}
