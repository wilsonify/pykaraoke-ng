use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SongId(pub u64);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SongFormat {
    Cdg,
    Kar,
    Mpeg,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SongView {
    pub version: u8,
    pub id: SongId,
    pub title: String,
    pub artist: String,
    pub filepath: String,
    pub display_name: String,
    #[serde(default)]
    pub duration_seconds: f64,
    pub format: SongFormat,
    #[serde(default)]
    pub disc: String,
    #[serde(default)]
    pub track: String,
    pub filename: String,
}
