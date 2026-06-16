//! Backend service — command dispatch and IPC protocol.
//!
//! Mirrors `PyKaraokeBackend` from `src/pykaraoke/core/backend.py`.
//! Supports stdio JSON-line IPC (for Tauri) and a pure function API.

use crate::database::Persistence;
use crate::library::Library;
use crate::player::BackendState;
use crate::queue::{Queue, SongSummary};
use crate::song::SongStruct;
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Command request structure (matches Python protocol).
#[derive(Debug, Serialize, Deserialize)]
pub struct CommandRequest {
    pub action: String,
    #[serde(default)]
    pub params: Value,
}

/// Command response structure.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandResponse {
    pub status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
}

impl CommandResponse {
    pub fn ok() -> Self {
        Self {
            status: "ok".to_string(),
            message: None,
            data: None,
        }
    }

    pub fn ok_with_data(data: Value) -> Self {
        Self {
            status: "ok".to_string(),
            message: None,
            data: Some(data),
        }
    }

    pub fn error(msg: impl Into<String>) -> Self {
        Self {
            status: "error".to_string(),
            message: Some(msg.into()),
            data: None,
        }
    }

    pub fn ok_with_message(msg: impl Into<String>) -> Self {
        Self {
            status: "ok".to_string(),
            message: Some(msg.into()),
            data: None,
        }
    }
}

/// Full backend state for serialization to the frontend.
#[derive(Debug, Clone, Serialize)]
pub struct BackendFullState {
    pub playback_state: BackendState,
    pub current_song: Option<SongStruct>,
    pub playlist: Vec<SongSummary>,
    pub playlist_index: Option<usize>,
    pub volume: f64,
    pub position_ms: u64,
    pub song_length: f64,
}

/// Event emitted by the backend to the frontend.
#[derive(Debug, Clone, Serialize)]
#[serde(tag = "type")]
pub enum BackendEvent {
    #[serde(rename = "state_changed")]
    StateChanged { data: BackendFullState },
    #[serde(rename = "song_finished")]
    SongFinished,
    #[serde(rename = "playlist_updated")]
    PlaylistUpdated { data: serde_json::Value },
    #[serde(rename = "error")]
    Error { message: String },
}

/// Core backend — orchestrates queue, library, persistence, and playback.
#[derive(Debug)]
pub struct Backend {
    pub state: BackendState,
    pub queue: Queue,
    pub library: Library,
    pub persistence: Persistence,
    pub volume: f64,
    pub current_time_ms: u64,
}

impl Backend {
    pub fn new(persistence: Persistence) -> Self {
        Self {
            state: BackendState::Idle,
            queue: Queue::new(),
            library: Library::new(),
            persistence,
            volume: 0.8,
            current_time_ms: 0,
        }
    }

    /// Handle a command and return a response.
    pub fn handle_command(&mut self, request: CommandRequest) -> CommandResponse {
        match request.action.as_str() {
            "get_state" => self.handle_get_state(),
            "play" => self.handle_play(request.params),
            "pause" => self.handle_pause(),
            "stop" => self.handle_stop(),
            "next" => self.handle_next(),
            "previous" => self.handle_previous(),
            "seek" => self.handle_seek(request.params),
            "set_volume" => self.handle_set_volume(request.params),
            "add_to_playlist" => self.handle_add_to_playlist(request.params),
            "remove_from_playlist" => self.handle_remove_from_playlist(request.params),
            "clear_playlist" => self.handle_clear_playlist(),
            "search_songs" => self.handle_search(request.params),
            "get_library" => self.handle_get_library(),
            "scan_library" => self.handle_scan_library(),
            "add_folder" => self.handle_add_folder(request.params),
            "get_settings" => self.handle_get_settings(),
            "update_settings" => self.handle_update_settings(request.params),
            _ => CommandResponse::error(format!("Unknown action: {}", request.action)),
        }
    }

    /// Get the full backend state (for serialization).
    pub fn get_state(&self) -> BackendFullState {
        BackendFullState {
            playback_state: self.state,
            current_song: self.queue.current_song.clone(),
            playlist: self.queue.summaries(),
            playlist_index: self.queue.playlist_index,
            volume: self.volume,
            position_ms: 0,
            song_length: 0.0,
        }
    }

    // ── Command handlers ──────────────────────────────────────────

    fn handle_get_state(&self) -> CommandResponse {
        CommandResponse::ok_with_data(serde_json::to_value(self.get_state()).unwrap())
    }

    fn handle_play(&mut self, params: Value) -> CommandResponse {
        // If a playlist_index is given, select that song
        if let Some(index) = params.get("playlist_index").and_then(|v| v.as_u64()) {
            let idx = index as usize;
            if self.queue.select(idx).is_none() {
                return CommandResponse::error(format!(
                    "Playlist index {} is out of range",
                    idx
                ));
            }
        } else if self.queue.current_song.is_none() && !self.queue.is_empty() {
            // Auto-play from queue start
            self.queue.select(0);
        }

        if self.queue.current_song.is_none() {
            return CommandResponse::error("No song to play");
        }

        self.state = BackendState::Playing;
        CommandResponse::ok()
    }

    fn handle_pause(&mut self) -> CommandResponse {
        match self.state {
            BackendState::Playing => {
                self.state = BackendState::Paused;
                CommandResponse::ok_with_message("Paused")
            }
            BackendState::Paused => {
                self.state = BackendState::Playing;
                CommandResponse::ok_with_message("Resumed")
            }
            _ => CommandResponse::error("Not playing"),
        }
    }

    fn handle_stop(&mut self) -> CommandResponse {
        self.state = BackendState::Stopped;
        CommandResponse::ok()
    }

    fn handle_next(&mut self) -> CommandResponse {
        if self.queue.advance().is_some() {
            self.state = BackendState::Playing;
            CommandResponse::ok()
        } else {
            CommandResponse::error("No next song in playlist")
        }
    }

    fn handle_previous(&mut self) -> CommandResponse {
        if self.queue.previous().is_some() {
            self.state = BackendState::Playing;
            CommandResponse::ok()
        } else {
            CommandResponse::error("No previous song in playlist")
        }
    }

    fn handle_seek(&mut self, params: Value) -> CommandResponse {
        match params.get("position_ms").and_then(|v| v.as_u64()) {
            Some(_pos) => CommandResponse::ok(),
            None => CommandResponse::error("Missing position_ms parameter"),
        }
    }

    fn handle_set_volume(&mut self, params: Value) -> CommandResponse {
        match params.get("volume").and_then(|v| v.as_f64()) {
            Some(vol) => {
                self.volume = vol.clamp(0.0, 1.0);
                CommandResponse::ok()
            }
            None => CommandResponse::error("Missing volume parameter"),
        }
    }

    fn handle_add_to_playlist(&mut self, params: Value) -> CommandResponse {
        let filepath = match params.get("filepath").and_then(|v| v.as_str()) {
            Some(fp) => fp.to_string(),
            None => return CommandResponse::error("Missing filepath parameter"),
        };

        let song = SongStruct::from_filepath(&filepath);

        // Parse filename for artist/title
        let parsed = self.library.filename_parser.parse(&filepath);
        let mut song = song;
        song.artist = parsed.artist;
        song.title = parsed.title;

        self.queue.add(song);

        CommandResponse::ok()
    }

    fn handle_remove_from_playlist(&mut self, params: Value) -> CommandResponse {
        match params.get("index").and_then(|v| v.as_u64()) {
            Some(idx) => {
                if self.queue.remove(idx as usize).is_some() {
                    CommandResponse::ok()
                } else {
                    CommandResponse::error(format!("Index {} out of range", idx))
                }
            }
            None => CommandResponse::error("Missing index parameter"),
        }
    }

    fn handle_clear_playlist(&mut self) -> CommandResponse {
        self.queue.clear();
        CommandResponse::ok()
    }

    fn handle_search(&self, params: Value) -> CommandResponse {
        let query = params
            .get("query")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let results = self.library.search(query);

        let song_values: Vec<Value> = results
            .into_iter()
            .map(|r| serde_json::to_value(r.song).unwrap())
            .collect();

        CommandResponse::ok_with_data(serde_json::json!({
            "results": song_values,
            "count": song_values.len(),
        }))
    }

    fn handle_get_library(&self) -> CommandResponse {
        let songs: Vec<Value> = self
            .library
            .unique_song_list
            .iter()
            .map(|s| serde_json::to_value(s).unwrap())
            .collect();

        CommandResponse::ok_with_data(serde_json::json!({
            "songs": songs,
            "count": songs.len(),
        }))
    }

    fn handle_scan_library(&mut self) -> CommandResponse {
        let results = self.library.scan();
        let mut messages = Vec::new();

        if !results.errors.is_empty() {
            for err in &results.errors {
                messages.push(err.clone());
            }
        }

        CommandResponse::ok_with_data(serde_json::json!({
            "songs_found": results.songs.len(),
            "errors": messages,
        }))
    }

    fn handle_add_folder(&mut self, params: Value) -> CommandResponse {
        let folder = match params.get("folder").and_then(|v| v.as_str()) {
            Some(f) => f.to_string(),
            None => return CommandResponse::error("Missing folder parameter"),
        };
        self.library.add_folder(folder);
        CommandResponse::ok()
    }

    fn handle_get_settings(&self) -> CommandResponse {
        CommandResponse::ok_with_data(
            serde_json::to_value(&self.persistence.settings).unwrap(),
        )
    }

    fn handle_update_settings(&mut self, params: Value) -> CommandResponse {
        // Merge provided settings into current settings
        if let Some(settings) = params.get("settings") {
            if let Ok(new_settings) =
                serde_json::from_value::<crate::database::Settings>(settings.clone())
            {
                self.persistence.settings = new_settings;
                return CommandResponse::ok();
            }
        }
        CommandResponse::error("Invalid settings")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_backend() -> Backend {
        let dir = std::env::temp_dir().join("pykaraoke_test_backend");
        let _ = std::fs::remove_dir_all(&dir);
        let persistence = Persistence::new(Some(dir));
        Backend::new(persistence)
    }

    #[test]
    fn test_initial_state() {
        let backend = test_backend();
        assert_eq!(backend.state, BackendState::Idle);
        assert!((backend.volume - 0.8).abs() < 0.001);
    }

    #[test]
    fn test_unknown_command() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "invalid_action".to_string(),
            params: Value::Null,
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "error");
        assert!(resp.message.unwrap().contains("Unknown action"));
    }

    #[test]
    fn test_get_state() {
        let backend = test_backend();
        let state = backend.get_state();
        assert_eq!(state.playback_state, BackendState::Idle);
        assert!(state.playlist.is_empty());
    }

    #[test]
    fn test_play_error_no_songs() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "play".to_string(),
            params: Value::Null,
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "error");
    }

    #[test]
    fn test_add_to_playlist() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "add_to_playlist".to_string(),
            params: serde_json::json!({"filepath": "/tmp/test.kar"}),
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
        assert_eq!(backend.queue.len(), 1);
    }

    #[test]
    fn test_add_to_playlist_missing_filepath() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "add_to_playlist".to_string(),
            params: serde_json::json!({}),
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "error");
        assert!(resp.message.unwrap().contains("filepath"));
    }

    #[test]
    fn test_clear_playlist() {
        let mut backend = test_backend();
        backend.queue.add(SongStruct::from_filepath("/tmp/test.kar"));
        assert_eq!(backend.queue.len(), 1);

        let req = CommandRequest {
            action: "clear_playlist".to_string(),
            params: Value::Null,
        };
        backend.handle_command(req);
        assert_eq!(backend.queue.len(), 0);
    }

    #[test]
    fn test_play_from_queue() {
        let mut backend = test_backend();
        backend.queue.add(SongStruct::from_filepath("/tmp/test.kar"));

        let req = CommandRequest {
            action: "play".to_string(),
            params: Value::Null,
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
        assert_eq!(backend.state, BackendState::Playing);
        assert!(backend.queue.current_song.is_some());
    }

    #[test]
    fn test_play_with_index() {
        let mut backend = test_backend();
        backend.queue.add(SongStruct::from_filepath("/tmp/first.kar"));
        backend.queue.add(SongStruct::from_filepath("/tmp/second.kar"));

        let req = CommandRequest {
            action: "play".to_string(),
            params: serde_json::json!({"playlist_index": 1}),
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
        assert_eq!(backend.queue.playlist_index, Some(1));
    }

    #[test]
    fn test_play_with_invalid_index() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "play".to_string(),
            params: serde_json::json!({"playlist_index": 99}),
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "error");
    }

    #[test]
    fn test_set_volume() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "set_volume".to_string(),
            params: serde_json::json!({"volume": 0.5}),
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
        assert!((backend.volume - 0.5).abs() < 0.001);
    }

    #[test]
    fn test_set_volume_clamped() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "set_volume".to_string(),
            params: serde_json::json!({"volume": 2.0}),
        };
        backend.handle_command(req);
        assert!((backend.volume - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_next_previous() {
        let mut backend = test_backend();
        backend.queue.add(SongStruct::from_filepath("/tmp/first.kar"));
        backend.queue.add(SongStruct::from_filepath("/tmp/second.kar"));
        backend.queue.select(0);

        let next_req = CommandRequest {
            action: "next".to_string(),
            params: Value::Null,
        };
        let resp = backend.handle_command(next_req);
        assert_eq!(resp.status, "ok");
        assert_eq!(backend.queue.playlist_index, Some(1));

        let prev_req = CommandRequest {
            action: "previous".to_string(),
            params: Value::Null,
        };
        let resp = backend.handle_command(prev_req);
        assert_eq!(resp.status, "ok");
        assert_eq!(backend.queue.playlist_index, Some(0));
    }

    #[test]
    fn test_search() {
        let mut backend = test_backend();
        backend.library.unique_song_list.push(SongStruct {
            title: "Bohemian Rhapsody".to_string(),
            artist: "Queen".to_string(),
            filepath: "/music/queen/bohemian.kar".to_string(),
            ..Default::default()
        });

        let req = CommandRequest {
            action: "search_songs".to_string(),
            params: serde_json::json!({"query": "Queen"}),
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
        let data = resp.data.unwrap();
        assert_eq!(data["count"], 1);
    }

    #[test]
    fn test_scan_library_empty() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "scan_library".to_string(),
            params: Value::Null,
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
    }

    #[test]
    fn test_add_folder() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "add_folder".to_string(),
            params: serde_json::json!({"folder": "/music/karaoke"}),
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
        assert_eq!(backend.library.folder_list.len(), 1);
    }

    #[test]
    fn test_pause_resume() {
        let mut backend = test_backend();
        backend.state = BackendState::Playing;

        let pause_req = CommandRequest {
            action: "pause".to_string(),
            params: Value::Null,
        };
        let resp = backend.handle_command(pause_req);
        assert_eq!(resp.status, "ok");
        assert_eq!(backend.state, BackendState::Paused);

        let resume_req = CommandRequest {
            action: "pause".to_string(),
            params: Value::Null,
        };
        let resp = backend.handle_command(resume_req);
        assert_eq!(resp.status, "ok");
        assert_eq!(backend.state, BackendState::Playing);
    }

    #[test]
    fn test_stop() {
        let mut backend = test_backend();
        backend.state = BackendState::Playing;

        let req = CommandRequest {
            action: "stop".to_string(),
            params: Value::Null,
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
        assert_eq!(backend.state, BackendState::Stopped);
    }

    #[test]
    fn test_get_settings() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "get_settings".to_string(),
            params: Value::Null,
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
        assert!(resp.data.is_some());
    }

    #[test]
    fn test_remove_from_playlist() {
        let mut backend = test_backend();
        backend.queue.add(SongStruct::from_filepath("/tmp/song0.kar"));
        backend.queue.add(SongStruct::from_filepath("/tmp/song1.kar"));
        backend.queue.add(SongStruct::from_filepath("/tmp/song2.kar"));

        let req = CommandRequest {
            action: "remove_from_playlist".to_string(),
            params: serde_json::json!({"index": 1}),
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
        assert_eq!(backend.queue.len(), 2);
    }

    #[test]
    fn test_remove_from_playlist_out_of_range() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "remove_from_playlist".to_string(),
            params: serde_json::json!({"index": 99}),
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "error");
    }

    #[test]
    fn test_get_library_empty() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "get_library".to_string(),
            params: Value::Null,
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
        assert_eq!(resp.data.unwrap()["count"], 0);
    }
}
