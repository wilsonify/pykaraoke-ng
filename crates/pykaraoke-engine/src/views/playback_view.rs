use serde::{Deserialize, Serialize};
use crate::views::SongView;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PlaybackStatus {
    Idle,
    Playing,
    Paused,
    Stopped,
    Loading,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PlaybackState {
    pub status: PlaybackStatus,
    pub current_song: Option<SongView>,
    pub position_ms: u64,
    pub duration_ms: u64,
    pub volume: f64,
}
