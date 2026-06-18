use crate::views::*;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EngineStatus {
    Starting,
    Running,
    Stopped,
    Error,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EngineError {
    #[serde(rename = "not_started")]
    NotStarted,

    #[serde(rename = "already_started")]
    AlreadyStarted,

    #[serde(rename = "io_error")]
    Io { message: String },

    #[serde(rename = "invalid_file")]
    InvalidFile { path: String, message: String },

    #[serde(rename = "playback_error")]
    Playback { message: String },

    #[serde(rename = "queue_error")]
    Queue { message: String },

    #[serde(rename = "settings_error")]
    Settings { message: String },

    #[serde(rename = "internal")]
    Internal { message: String },
}

impl std::fmt::Display for EngineError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EngineError::NotStarted => write!(f, "Engine not started"),
            EngineError::AlreadyStarted => write!(f, "Engine already started"),
            EngineError::Io { message } => write!(f, "IO error: {}", message),
            EngineError::InvalidFile { path, message } => {
                write!(f, "Invalid file {}: {}", path, message)
            }
            EngineError::Playback { message } => write!(f, "Playback error: {}", message),
            EngineError::Queue { message } => write!(f, "Queue error: {}", message),
            EngineError::Settings { message } => write!(f, "Settings error: {}", message),
            EngineError::Internal { message } => write!(f, "Internal error: {}", message),
        }
    }
}

impl std::error::Error for EngineError {}

pub trait Engine: Send {
    fn start(&mut self) -> Result<(), EngineError>;
    fn stop(&mut self) -> Result<(), EngineError>;
    fn status(&self) -> EngineStatus;

    fn play(&mut self, song_id: Option<SongId>) -> Result<PlaybackState, EngineError>;
    fn pause(&mut self) -> Result<PlaybackState, EngineError>;
    fn stop_playback(&mut self) -> Result<PlaybackState, EngineError>;
    fn next(&mut self) -> Result<PlaybackState, EngineError>;
    fn previous(&mut self) -> Result<PlaybackState, EngineError>;
    fn seek(&mut self, position_ms: u64) -> Result<PlaybackState, EngineError>;
    fn tick(&mut self);
    fn set_volume(&mut self, volume: f64) -> Result<PlaybackState, EngineError>;

    fn enqueue(&mut self, filepath: &str) -> Result<QueueView, EngineError>;
    fn remove_from_queue(&mut self, index: usize) -> Result<QueueView, EngineError>;
    fn clear_queue(&mut self) -> Result<QueueView, EngineError>;
    fn move_in_queue(&mut self, from: usize, to: usize) -> Result<QueueView, EngineError>;
    fn queue(&self) -> QueueView;

    fn scan_library(&mut self) -> Result<LibraryScanProgress, EngineError>;
    fn add_library_folder(&mut self, path: &str) -> Result<(), EngineError>;
    fn remove_library_folder(&mut self, path: &str) -> Result<(), EngineError>;
    fn library_folders(&self) -> Vec<String>;

    fn search(&self, query: &str) -> SearchResultsView;

    fn settings(&self) -> SettingsView;
    fn update_settings(&mut self, delta: SettingsDelta) -> Result<SettingsView, EngineError>;
}
