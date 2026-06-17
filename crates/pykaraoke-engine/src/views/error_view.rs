use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ErrorCode {
    IoError,
    FileNotFound,
    InvalidFileFormat,
    PlaybackFailed,
    QueueEmpty,
    QueueIndexOutOfRange,
    SettingsValidationFailed,
    BackendNotRunning,
    BackendAlreadyRunning,
    InternalError,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct EngineErrorInfo {
    pub code: ErrorCode,
    pub message: String,
    pub details: Option<String>,
    pub recoverable: bool,
}
