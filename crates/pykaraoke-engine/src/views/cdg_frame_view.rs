use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CdgFrameView {
    pub pixels: Vec<u8>,
    pub width: u16,
    pub height: u16,
    pub timestamp_ms: u64,
}
