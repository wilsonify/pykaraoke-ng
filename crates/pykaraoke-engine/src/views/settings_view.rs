use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DisplaySettings {
    pub fullscreen: bool,
    pub width: u32,
    pub height: u32,
    pub always_on_top: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AudioSettings {
    pub volume: f64,
    pub sync_delay_ms: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LyricsSettings {
    pub show: bool,
    pub font_size: u32,
    pub font_bold: bool,
    pub font_italic: bool,
    pub color: String,
    pub outline_color: String,
    pub sweep_color: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SettingsView {
    pub version: u8,
    pub display: DisplaySettings,
    pub audio: AudioSettings,
    pub lyrics: LyricsSettings,
    pub library_folders: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SettingsDelta {
    pub fullscreen: Option<bool>,
    pub width: Option<u32>,
    pub height: Option<u32>,
    pub always_on_top: Option<bool>,
    pub volume: Option<f64>,
    pub sync_delay_ms: Option<i64>,
    pub show_lyrics: Option<bool>,
    pub font_size: Option<u32>,
    pub font_bold: Option<bool>,
    pub font_italic: Option<bool>,
    pub lyrics_color: Option<String>,
    pub lyrics_outline_color: Option<String>,
    pub lyrics_sweep_color: Option<String>,
}
