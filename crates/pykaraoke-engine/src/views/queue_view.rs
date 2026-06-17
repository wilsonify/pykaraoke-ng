use serde::{Deserialize, Serialize};
use crate::views::SongView;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct QueueView {
    pub songs: Vec<SongView>,
    pub current_index: Option<usize>,
    pub total_duration_seconds: f64,
}
