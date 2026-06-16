//! Database/persistence — settings and song database serialization.
//!
//! Mirrors `SongDB.save_database()`, `load_database()`, `save_settings()`,
//! and `load_settings()` from `src/pykaraoke/core/database.py`.
//!
//! Replaces Python pickle with JSON serialization.

use crate::song::SongStruct;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Current settings version (mirrors Python `SETTINGS_VERSION = 6`).
pub const SETTINGS_VERSION: u32 = 6;

/// Current database version (mirrors Python `DATABASE_VERSION = 2`).
pub const DATABASE_VERSION: u32 = 2;

/// Song database serialization wrapper.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Database {
    pub version: u32,
    pub full_song_list: Vec<SongStruct>,
    pub unique_song_list: Vec<SongStruct>,
    pub got_titles: bool,
    pub got_artists: bool,
}

impl Default for Database {
    fn default() -> Self {
        Self {
            version: DATABASE_VERSION,
            full_song_list: Vec::new(),
            unique_song_list: Vec::new(),
            got_titles: false,
            got_artists: false,
        }
    }
}

/// User settings, mirroring `SettingsStruct` from `pykaraoke.core.database`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Settings {
    pub version: u32,

    // Search paths
    pub folder_list: Vec<String>,

    // File extensions
    pub cdg_extensions: Vec<String>,
    pub kar_extensions: Vec<String>,
    pub mpg_extensions: Vec<String>,
    pub ignored_extensions: Vec<String>,

    // CD+G audio options
    pub cdg_uses_mp3: bool,
    pub cdg_uses_ogg: bool,
    pub cdg_derive_song_information: bool,

    // Display
    pub display_width: u32,
    pub display_height: u32,
    pub fullscreen: bool,
    pub always_on_top: bool,
    pub show_lyrics: bool,
    pub show_splash: bool,

    // Font
    pub font_name: String,
    pub font_size: u32,
    pub font_bold: bool,
    pub font_italic: bool,

    // Lyrics
    pub lyrics_color: String,
    pub lyrics_outline_color: String,
    pub lyrics_sweep_color: String,

    // Audio
    pub volume: f64,

    // Sync
    pub sync_delay_ms: i64,

    // Filename parsing
    pub file_name_type: String, // "ARTIST_TITLE", etc.
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            version: SETTINGS_VERSION,
            folder_list: Vec::new(),
            cdg_extensions: vec![".cdg".to_string()],
            kar_extensions: vec![".kar".to_string(), ".mid".to_string()],
            mpg_extensions: vec![
                ".mpg".to_string(),
                ".mpeg".to_string(),
                ".avi".to_string(),
                ".divx".to_string(),
                ".xvid".to_string(),
                ".mp3".to_string(),
                ".ogg".to_string(),
            ],
            ignored_extensions: Vec::new(),
            cdg_uses_mp3: true,
            cdg_uses_ogg: true,
            cdg_derive_song_information: true,
            display_width: 800,
            display_height: 600,
            fullscreen: false,
            always_on_top: false,
            show_lyrics: true,
            show_splash: true,
            font_name: "DejaVuSans".to_string(),
            font_size: 40,
            font_bold: false,
            font_italic: false,
            lyrics_color: "#FF0000".to_string(),
            lyrics_outline_color: "#000000".to_string(),
            lyrics_sweep_color: "#FFFFFF".to_string(),
            volume: 0.8,
            sync_delay_ms: 0,
            file_name_type: "ARTIST_TITLE".to_string(),
        }
    }
}

/// Persistence manager for settings and song database.
#[derive(Debug, Clone)]
pub struct Persistence {
    pub data_dir: PathBuf,
    pub settings: Settings,
    pub database: Database,
}

impl Persistence {
    /// Create a new persistence manager.
    ///
    /// `data_dir` defaults to `~/.pykaraoke/` (mirroring the Python location).
    pub fn new(data_dir: Option<PathBuf>) -> Self {
        let dir = data_dir.unwrap_or_else(|| {
            dirs::data_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join(".pykaraoke")
        });

        Self {
            data_dir: dir,
            settings: Settings::default(),
            database: Database::default(),
        }
    }

    /// Ensure the data directory exists.
    pub fn ensure_data_dir(&self) -> std::io::Result<()> {
        std::fs::create_dir_all(&self.data_dir)
    }

    /// Save settings to `settings.json` in the data directory.
    pub fn save_settings(&self) -> Result<(), String> {
        self.ensure_data_dir().map_err(|e| format!("Cannot create data dir: {}", e))?;

        let path = self.data_dir.join("settings.json");
        let json = serde_json::to_string_pretty(&self.settings)
            .map_err(|e| format!("Cannot serialize settings: {}", e))?;
        std::fs::write(&path, &json)
            .map_err(|e| format!("Cannot write settings: {}", e))
    }

    /// Load settings from `settings.json`.
    /// Returns default settings if the file does not exist.
    pub fn load_settings(&mut self) -> Result<(), String> {
        let path = self.data_dir.join("settings.json");
        if !path.exists() {
            return Ok(()); // Use defaults
        }

        let json = std::fs::read_to_string(&path)
            .map_err(|e| format!("Cannot read settings: {}", e))?;
        let settings: Settings = serde_json::from_str(&json)
            .map_err(|e| format!("Cannot parse settings: {}", e))?;
        self.settings = settings;
        Ok(())
    }

    /// Save the song database to `songdb.json`.
    pub fn save_database(&self) -> Result<(), String> {
        self.ensure_data_dir().map_err(|e| format!("Cannot create data dir: {}", e))?;

        let path = self.data_dir.join("songdb.json");
        let json = serde_json::to_string_pretty(&self.database)
            .map_err(|e| format!("Cannot serialize database: {}", e))?;
        std::fs::write(&path, &json)
            .map_err(|e| format!("Cannot write database: {}", e))
    }

    /// Load the song database from `songdb.json`.
    pub fn load_database(&mut self) -> Result<(), String> {
        let path = self.data_dir.join("songdb.json");
        if !path.exists() {
            return Ok(()); // No database yet
        }

        // Safety checks mirroring Python's `_is_safe_database_file()`
        let metadata = std::fs::metadata(&path)
            .map_err(|e| format!("Cannot read database metadata: {}", e))?;

        if metadata.len() > 50 * 1024 * 1024 {
            return Err("Database file exceeds 50MB limit".to_string());
        }

        let json = std::fs::read_to_string(&path)
            .map_err(|e| format!("Cannot read database: {}", e))?;
        let database: Database = serde_json::from_str(&json)
            .map_err(|e| format!("Cannot parse database: {}", e))?;
        self.database = database;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_settings_defaults() {
        let settings = Settings::default();
        assert_eq!(settings.version, SETTINGS_VERSION);
        assert!(settings.cdg_uses_mp3);
        assert_eq!(settings.display_width, 800);
        assert_eq!(settings.display_height, 600);
        assert!((settings.volume - 0.8).abs() < 0.001);
    }

    #[test]
    fn test_settings_roundtrip() {
        let dir = std::env::temp_dir().join("pykaraoke_test_settings");
        let _ = std::fs::remove_dir_all(&dir);

        let mut persistence = Persistence::new(Some(dir.clone()));
        persistence.settings.display_width = 1920;
        persistence.settings.display_height = 1080;
        persistence.settings.volume = 0.5;
        persistence.save_settings().unwrap();

        let mut loaded = Persistence::new(Some(dir.clone()));
        loaded.load_settings().unwrap();
        assert_eq!(loaded.settings.display_width, 1920);
        assert_eq!(loaded.settings.display_height, 1080);
        assert!((loaded.settings.volume - 0.5).abs() < 0.001);

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_database_roundtrip() {
        let dir = std::env::temp_dir().join("pykaraoke_test_db");
        let _ = std::fs::remove_dir_all(&dir);

        let mut persistence = Persistence::new(Some(dir.clone()));
        persistence.database.full_song_list.push(SongStruct {
            title: "Test Song".to_string(),
            artist: "Test Artist".to_string(),
            filepath: "/test/song.kar".to_string(),
            display_filename: "song.kar".to_string(),
            extension: ".kar".to_string(),
            ..Default::default()
        });
        persistence.save_database().unwrap();

        let mut loaded = Persistence::new(Some(dir.clone()));
        loaded.load_database().unwrap();
        assert_eq!(loaded.database.full_song_list.len(), 1);
        assert_eq!(loaded.database.full_song_list[0].title, "Test Song");

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_load_settings_nonexistent() {
        let dir = std::env::temp_dir().join("pykaraoke_test_nonexistent_settings");
        let _ = std::fs::remove_dir_all(&dir);

        let mut persistence = Persistence::new(Some(dir.clone()));
        assert!(persistence.load_settings().is_ok());

        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_database_version() {
        let db = Database::default();
        assert_eq!(db.version, DATABASE_VERSION);
    }
}
