use serde::{Deserialize, Serialize};
use crate::views::SongView;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SearchResultsView {
    pub query: String,
    pub results: Vec<SongView>,
    pub total_count: usize,
}
