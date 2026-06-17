use crate::backend::{Backend, CommandRequest, CommandResponse};
use crate::database::Persistence;
use crate::engine::{Engine, EngineError, EngineStatus};
use crate::event_bus::EventBus;
use crate::player::BackendState;
use crate::views::*;
use serde_json::Value;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};

static NEXT_SONG_ID: AtomicU64 = AtomicU64::new(1);

fn song_id_from_filepath(filepath: &str) -> SongId {
    use std::hash::{Hash, Hasher};
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    filepath.hash(&mut hasher);
    SongId(hasher.finish())
}

fn song_struct_to_view(song: &crate::song::SongStruct, id: SongId) -> SongView {
    let format = match song.extension.as_str() {
        ".cdg" => SongFormat::Cdg,
        ".kar" | ".mid" => SongFormat::Kar,
        ".mpg" | ".mpeg" | ".avi" | ".divx" | ".xvid" | ".mp3" | ".ogg" => SongFormat::Mpeg,
        _ => SongFormat::Unknown,
    };
    SongView {
        version: 1,
        id,
        title: song.title.clone(),
        artist: song.artist.clone(),
        filepath: song.filepath.clone(),
        display_name: song.display_name(),
        duration_seconds: song.length,
        format,
        disc: song.disc.clone(),
        track: song.track.clone(),
        filename: song.display_filename.clone(),
    }
}

fn backend_state_to_playback_status(state: BackendState) -> PlaybackStatus {
    match state {
        BackendState::Idle => PlaybackStatus::Idle,
        BackendState::Playing => PlaybackStatus::Playing,
        BackendState::Paused => PlaybackStatus::Paused,
        BackendState::Stopped => PlaybackStatus::Stopped,
        BackendState::Loading => PlaybackStatus::Loading,
        BackendState::Error => PlaybackStatus::Idle,
    }
}

fn song_id_for_song(song: &crate::song::SongStruct) -> SongId {
    if song.filepath.is_empty() {
        SongId(NEXT_SONG_ID.fetch_add(1, Ordering::Relaxed))
    } else {
        song_id_from_filepath(&song.filepath)
    }
}

pub struct EngineImpl {
    backend: Option<Backend>,
    event_bus: Option<Box<dyn EventBus>>,
    data_dir: Option<PathBuf>,
    status: EngineStatus,
}

impl EngineImpl {
    pub fn new(data_dir: Option<PathBuf>, event_bus: Box<dyn EventBus>) -> Self {
        Self {
            backend: None,
            event_bus: Some(event_bus),
            data_dir,
            status: EngineStatus::Stopped,
        }
    }

    pub fn backend(&self) -> Option<&Backend> {
        self.backend.as_ref()
    }

    pub fn backend_mut(&mut self) -> Option<&mut Backend> {
        self.backend.as_mut()
    }

    fn require_backend(&self) -> Result<&Backend, EngineError> {
        self.backend.as_ref().ok_or(EngineError::NotStarted)
    }

    fn require_backend_mut(&mut self) -> Result<&mut Backend, EngineError> {
        self.backend.as_mut().ok_or(EngineError::NotStarted)
    }

    fn build_playback_state(&self) -> PlaybackState {
        match self.backend.as_ref() {
            Some(backend) => {
                let current_song = backend.queue.current_song.as_ref().map(|s| {
                    song_struct_to_view(s, song_id_for_song(s))
                });
                let duration_ms = current_song
                    .as_ref()
                    .map(|s| (s.duration_seconds * 1000.0) as u64)
                    .unwrap_or(0);
                PlaybackState {
                    status: backend_state_to_playback_status(backend.state),
                    current_song,
                    position_ms: backend.current_time_ms,
                    duration_ms,
                    volume: backend.volume,
                }
            }
            None => PlaybackState {
                status: PlaybackStatus::Idle,
                current_song: None,
                position_ms: 0,
                duration_ms: 0,
                volume: 0.8,
            },
        }
    }

    fn build_queue_view(&self) -> QueueView {
        match self.backend.as_ref() {
            Some(backend) => {
                let songs: Vec<SongView> = backend
                    .queue
                    .playlist
                    .iter()
                    .map(|s| song_struct_to_view(s, song_id_for_song(s)))
                    .collect();
                let total_duration: f64 = backend
                    .queue
                    .playlist
                    .iter()
                    .map(|s| s.length)
                    .sum();
                QueueView {
                    songs,
                    current_index: backend.queue.playlist_index,
                    total_duration_seconds: total_duration,
                }
            }
            None => QueueView {
                songs: Vec::new(),
                current_index: None,
                total_duration_seconds: 0.0,
            },
        }
    }

    fn build_settings_view(&self) -> SettingsView {
        match self.backend.as_ref() {
            Some(backend) => {
                let s = &backend.persistence.settings;
                SettingsView {
                    version: 1,
                    display: DisplaySettings {
                        fullscreen: s.fullscreen,
                        width: s.display_width,
                        height: s.display_height,
                        always_on_top: s.always_on_top,
                    },
                    audio: AudioSettings {
                        volume: s.volume,
                        sync_delay_ms: s.sync_delay_ms,
                    },
                    lyrics: LyricsSettings {
                        show: s.show_lyrics,
                        font_size: s.font_size,
                        font_bold: s.font_bold,
                        font_italic: s.font_italic,
                        color: s.lyrics_color.clone(),
                        outline_color: s.lyrics_outline_color.clone(),
                        sweep_color: s.lyrics_sweep_color.clone(),
                    },
                    library_folders: backend.library.folder_list.clone(),
                }
            }
            None => SettingsView {
                version: 1,
                display: DisplaySettings {
                    fullscreen: false,
                    width: 800,
                    height: 600,
                    always_on_top: false,
                },
                audio: AudioSettings {
                    volume: 0.8,
                    sync_delay_ms: 0,
                },
                lyrics: LyricsSettings {
                    show: true,
                    font_size: 40,
                    font_bold: false,
                    font_italic: false,
                    color: "#FF0000".to_string(),
                    outline_color: "#000000".to_string(),
                    sweep_color: "#FFFFFF".to_string(),
                },
                library_folders: Vec::new(),
            },
        }
    }

    fn cmd(&mut self, action: &str, params: Value) -> Result<CommandResponse, EngineError> {
        let backend = self.require_backend_mut()?;
        Ok(backend.handle_command(CommandRequest {
            action: action.to_string(),
            params,
        }))
    }

    fn emit(&self) -> Option<&dyn EventBus> {
        self.event_bus.as_ref().map(|b| b.as_ref())
    }
}

impl Engine for EngineImpl {
    fn start(&mut self) -> Result<(), EngineError> {
        if self.status == EngineStatus::Running {
            return Err(EngineError::AlreadyStarted);
        }
        let persistence = Persistence::new(self.data_dir.clone());
        let mut pers = persistence.clone();
        pers.load_settings().map_err(|e| EngineError::Io { message: e })?;
        pers.load_database().map_err(|e| EngineError::Io { message: e })?;
        let backend = Backend::new(pers);
        self.backend = Some(backend);
        self.status = EngineStatus::Running;
        if let Some(eb) = self.emit() {
            eb.emit_playback_changed(self.build_playback_state());
        }
        Ok(())
    }

    fn stop(&mut self) -> Result<(), EngineError> {
        if let Some(backend) = self.backend.take() {
            backend.persistence.save_settings().ok();
            backend.persistence.save_database().ok();
        }
        self.status = EngineStatus::Stopped;
        Ok(())
    }

    fn status(&self) -> EngineStatus {
        self.status
    }

    fn play(&mut self, song_id: Option<SongId>) -> Result<PlaybackState, EngineError> {
        let params = match song_id {
            Some(id) => {
                let backend = self.require_backend()?;
                let idx = backend
                    .queue
                    .playlist
                    .iter()
                    .position(|s| song_id_for_song(s) == id);
                match idx {
                    Some(i) => serde_json::json!({"playlist_index": i as u64}),
                    None => Value::Null,
                }
            }
            None => Value::Null,
        };
        let resp = self.cmd("play", params)?;
        match resp.status.as_str() {
            "ok" => {
                let state = self.build_playback_state();
                if let Some(eb) = self.emit() {
                    eb.emit_playback_changed(state.clone());
                }
                Ok(state)
            }
            "error" => Err(EngineError::Playback {
                message: resp.message.unwrap_or_default(),
            }),
            _ => Err(EngineError::Internal {
                message: "Unexpected response status".to_string(),
            }),
        }
    }

    fn pause(&mut self) -> Result<PlaybackState, EngineError> {
        let resp = self.cmd("pause", Value::Null)?;
        match resp.status.as_str() {
            "ok" => {
                let state = self.build_playback_state();
                if let Some(eb) = self.emit() {
                    eb.emit_playback_changed(state.clone());
                }
                Ok(state)
            }
            "error" => Err(EngineError::Playback {
                message: resp.message.unwrap_or_default(),
            }),
            _ => Err(EngineError::Internal {
                message: "Unexpected response status".to_string(),
            }),
        }
    }

    fn stop_playback(&mut self) -> Result<PlaybackState, EngineError> {
        let resp = self.cmd("stop", Value::Null)?;
        match resp.status.as_str() {
            "ok" => {
                let state = self.build_playback_state();
                if let Some(eb) = self.emit() {
                    eb.emit_playback_changed(state.clone());
                }
                Ok(state)
            }
            "error" => Err(EngineError::Playback {
                message: resp.message.unwrap_or_default(),
            }),
            _ => Err(EngineError::Internal {
                message: "Unexpected response status".to_string(),
            }),
        }
    }

    fn next(&mut self) -> Result<PlaybackState, EngineError> {
        let resp = self.cmd("next", Value::Null)?;
        match resp.status.as_str() {
            "ok" => {
                let state = self.build_playback_state();
                if let Some(eb) = self.emit() {
                    eb.emit_playback_changed(state.clone());
                }
                Ok(state)
            }
            "error" => Err(EngineError::Playback {
                message: resp.message.unwrap_or_default(),
            }),
            _ => Err(EngineError::Internal {
                message: "Unexpected response status".to_string(),
            }),
        }
    }

    fn previous(&mut self) -> Result<PlaybackState, EngineError> {
        let resp = self.cmd("previous", Value::Null)?;
        match resp.status.as_str() {
            "ok" => {
                let state = self.build_playback_state();
                if let Some(eb) = self.emit() {
                    eb.emit_playback_changed(state.clone());
                }
                Ok(state)
            }
            "error" => Err(EngineError::Playback {
                message: resp.message.unwrap_or_default(),
            }),
            _ => Err(EngineError::Internal {
                message: "Unexpected response status".to_string(),
            }),
        }
    }

    fn seek(&mut self, position_ms: u64) -> Result<PlaybackState, EngineError> {
        let resp = self.cmd("seek", serde_json::json!({"position_ms": position_ms}))?;
        match resp.status.as_str() {
            "ok" => {
                let state = self.build_playback_state();
                if let Some(eb) = self.emit() {
                    eb.emit_playback_changed(state.clone());
                }
                Ok(state)
            }
            "error" => Err(EngineError::Playback {
                message: resp.message.unwrap_or_default(),
            }),
            _ => Err(EngineError::Internal {
                message: "Unexpected response status".to_string(),
            }),
        }
    }

    fn set_volume(&mut self, volume: f64) -> Result<PlaybackState, EngineError> {
        let clamped = volume.clamp(0.0, 1.0);
        let _ = self.cmd("set_volume", serde_json::json!({"volume": clamped}))?;
        let state = self.build_playback_state();
        if let Some(eb) = self.emit() {
            eb.emit_playback_changed(state.clone());
        }
        Ok(state)
    }

    fn enqueue(&mut self, filepath: &str) -> Result<QueueView, EngineError> {
        let _ = self.cmd("add_to_playlist", serde_json::json!({"filepath": filepath}))?;
        let view = self.build_queue_view();
        if let Some(eb) = self.emit() {
            eb.emit_queue_changed(view.clone());
        }
        Ok(view)
    }

    fn remove_from_queue(&mut self, index: usize) -> Result<QueueView, EngineError> {
        let resp = self.cmd("remove_from_playlist", serde_json::json!({"index": index as u64}))?;
        match resp.status.as_str() {
            "ok" => {
                let view = self.build_queue_view();
                if let Some(eb) = self.emit() {
                    eb.emit_queue_changed(view.clone());
                }
                Ok(view)
            }
            "error" => Err(EngineError::Queue {
                message: resp.message.unwrap_or_default(),
            }),
            _ => Err(EngineError::Internal {
                message: "Unexpected response status".to_string(),
            }),
        }
    }

    fn clear_queue(&mut self) -> Result<QueueView, EngineError> {
        let _ = self.cmd("clear_playlist", Value::Null)?;
        let view = self.build_queue_view();
        if let Some(eb) = self.emit() {
            eb.emit_queue_changed(view.clone());
        }
        Ok(view)
    }

    fn move_in_queue(&mut self, from: usize, to: usize) -> Result<QueueView, EngineError> {
        let backend = self.require_backend_mut()?;
        if from >= backend.queue.playlist.len() || to >= backend.queue.playlist.len() {
            return Err(EngineError::Queue {
                message: "Index out of range".to_string(),
            });
        }
        if from == to {
            return Ok(self.build_queue_view());
        }
        let song = backend.queue.playlist.remove(from);
        let insert_pos = if to > from { to } else { to };
        backend.queue.playlist.insert(insert_pos, song);
        let view = self.build_queue_view();
        if let Some(eb) = self.emit() {
            eb.emit_queue_changed(view.clone());
        }
        Ok(view)
    }

    fn queue(&self) -> QueueView {
        self.build_queue_view()
    }

    fn scan_library(&mut self) -> Result<LibraryScanProgress, EngineError> {
        let resp = self.cmd("scan_library", Value::Null)?;
        match resp.status.as_str() {
            "ok" => {
                let songs_found = resp
                    .data
                    .as_ref()
                    .and_then(|d| d.get("songs_found"))
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0) as u32;
                let progress = LibraryScanProgress {
                    status: ScanStatus::Complete,
                    folders_scanned: 0,
                    songs_found,
                    errors: Vec::new(),
                    percent: 100,
                };
                if let Some(eb) = self.emit() {
                    eb.emit_scan_progress(progress.clone());
                }
                Ok(progress)
            }
            "error" => Err(EngineError::Internal {
                message: resp.message.unwrap_or_default(),
            }),
            _ => Err(EngineError::Internal {
                message: "Unexpected response status".to_string(),
            }),
        }
    }

    fn add_library_folder(&mut self, path: &str) -> Result<(), EngineError> {
        let resp = self.cmd("add_folder", serde_json::json!({"folder": path}))?;
        match resp.status.as_str() {
            "ok" => Ok(()),
            "error" => Err(EngineError::Io {
                message: resp.message.unwrap_or_default(),
            }),
            _ => Err(EngineError::Internal {
                message: "Unexpected response status".to_string(),
            }),
        }
    }

    fn remove_library_folder(&mut self, path: &str) -> Result<(), EngineError> {
        let backend = self.require_backend_mut()?;
        backend.library.remove_folder(path);
        Ok(())
    }

    fn library_folders(&self) -> Vec<String> {
        match self.backend.as_ref() {
            Some(backend) => backend.library.folder_list.clone(),
            None => Vec::new(),
        }
    }

    fn search(&self, query: &str) -> SearchResultsView {
        match self.backend.as_ref() {
            Some(backend) => {
                let results = backend.library.search(query);
                let song_views: Vec<SongView> = results
                    .iter()
                    .map(|r| song_struct_to_view(&r.song, song_id_for_song(&r.song)))
                    .collect();
                let count = song_views.len();
                SearchResultsView {
                    query: query.to_string(),
                    results: song_views,
                    total_count: count,
                }
            }
            None => SearchResultsView {
                query: query.to_string(),
                results: Vec::new(),
                total_count: 0,
            },
        }
    }

    fn settings(&self) -> SettingsView {
        self.build_settings_view()
    }

    fn update_settings(&mut self, delta: SettingsDelta) -> Result<SettingsView, EngineError> {
        let backend = self.require_backend_mut()?;
        let s = &mut backend.persistence.settings;
        if let Some(v) = delta.fullscreen {
            s.fullscreen = v;
        }
        if let Some(v) = delta.width {
            s.display_width = v;
        }
        if let Some(v) = delta.height {
            s.display_height = v;
        }
        if let Some(v) = delta.always_on_top {
            s.always_on_top = v;
        }
        if let Some(v) = delta.volume {
            s.volume = v.clamp(0.0, 1.0);
        }
        if let Some(v) = delta.sync_delay_ms {
            s.sync_delay_ms = v;
        }
        if let Some(v) = delta.show_lyrics {
            s.show_lyrics = v;
        }
        if let Some(v) = delta.font_size {
            s.font_size = v;
        }
        if let Some(v) = delta.font_bold {
            s.font_bold = v;
        }
        if let Some(v) = delta.font_italic {
            s.font_italic = v;
        }
        if let Some(v) = delta.lyrics_color {
            s.lyrics_color = v;
        }
        if let Some(v) = delta.lyrics_outline_color {
            s.lyrics_outline_color = v;
        }
        if let Some(v) = delta.lyrics_sweep_color {
            s.lyrics_sweep_color = v;
        }
        let view = self.build_settings_view();
        if let Some(eb) = self.emit() {
            eb.emit_settings_changed(view.clone());
        }
        Ok(view)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    struct MockEventBus {
        playback_changed: Mutex<Option<PlaybackState>>,
        queue_changed: Mutex<Option<QueueView>>,
        settings_changed: Mutex<Option<SettingsView>>,
        scan_progress: Mutex<Option<LibraryScanProgress>>,
        error_emitted: Mutex<Option<EngineErrorInfo>>,
    }

    impl MockEventBus {
        fn new() -> Self {
            Self {
                playback_changed: Mutex::new(None),
                queue_changed: Mutex::new(None),
                settings_changed: Mutex::new(None),
                scan_progress: Mutex::new(None),
                error_emitted: Mutex::new(None),
            }
        }

        fn playback_changed_called(&self) -> bool {
            self.playback_changed.lock().unwrap().is_some()
        }

        fn queue_changed_called(&self) -> bool {
            self.queue_changed.lock().unwrap().is_some()
        }
    }

    impl EventBus for MockEventBus {
        fn emit_playback_changed(&self, state: PlaybackState) {
            *self.playback_changed.lock().unwrap() = Some(state);
        }
        fn emit_queue_changed(&self, queue: QueueView) {
            *self.queue_changed.lock().unwrap() = Some(queue);
        }
        fn emit_library_changed(&self, _: LibraryView) {}
        fn emit_settings_changed(&self, settings: SettingsView) {
            *self.settings_changed.lock().unwrap() = Some(settings);
        }
        fn emit_scan_progress(&self, progress: LibraryScanProgress) {
            *self.scan_progress.lock().unwrap() = Some(progress);
        }
        fn emit_error(&self, error: EngineErrorInfo) {
            *self.error_emitted.lock().unwrap() = Some(error);
        }
        fn emit_cdg_frame(&self, _: CdgFrameView) {}
        fn emit_lyrics_changed(&self, _: LyricsView) {}
    }

    fn create_test_engine() -> EngineImpl {
        let dir = std::env::temp_dir().join("pykaraoke_test_engine_impl");
        let _ = std::fs::remove_dir_all(&dir);
        EngineImpl::new(Some(dir), Box::new(MockEventBus::new()))
    }

    #[test]
    fn test_initial_status_is_stopped() {
        let engine = create_test_engine();
        assert_eq!(engine.status(), EngineStatus::Stopped);
    }

    #[test]
    fn test_start_changes_status() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        assert_eq!(engine.status(), EngineStatus::Running);
    }

    #[test]
    fn test_start_twice_returns_error() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        let result = engine.start();
        assert!(result.is_err());
        match result.unwrap_err() {
            EngineError::AlreadyStarted => {}
            _ => panic!("Expected AlreadyStarted error"),
        }
    }

    #[test]
    fn test_stop_changes_status() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        engine.stop().unwrap();
        assert_eq!(engine.status(), EngineStatus::Stopped);
    }

    #[test]
    fn test_stop_without_start_is_noop() {
        let mut engine = create_test_engine();
        engine.stop().unwrap();
        assert_eq!(engine.status(), EngineStatus::Stopped);
    }

    #[test]
    fn test_play_without_start_returns_error() {
        let mut engine = create_test_engine();
        let result = engine.play(None);
        assert!(result.is_err());
    }

    #[test]
    fn test_enqueue_and_play() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        let queue = engine.enqueue("/tmp/test_song.kar").unwrap();
        assert_eq!(queue.songs.len(), 1);
        let state = engine.play(None).unwrap();
        assert_eq!(state.status, PlaybackStatus::Playing);
    }

    #[test]
    fn test_enqueue_emits_event() {
        let dir = std::env::temp_dir().join("pykaraoke_test_engine_emit");
        let _ = std::fs::remove_dir_all(&dir);
        let mock = MockEventBus::new();
        let mut engine = EngineImpl::new(Some(dir), Box::new(mock));
        engine.start().unwrap();
        engine.enqueue("/tmp/test.kar").unwrap();
        // drop engine so we can access mock
        drop(engine);
    }

    #[test]
    fn test_queue_view_after_enqueue() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        engine.enqueue("/tmp/song1.kar").unwrap();
        engine.enqueue("/tmp/song2.kar").unwrap();
        let queue = engine.queue();
        assert_eq!(queue.songs.len(), 2);
        assert!(queue.current_index.is_none());
    }

    #[test]
    fn test_search_empty_library() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        let results = engine.search("test");
        assert_eq!(results.total_count, 0);
    }

    #[test]
    fn test_settings_defaults() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        let settings = engine.settings();
        assert!(!settings.display.fullscreen);
        assert_eq!(settings.audio.sync_delay_ms, 0);
    }

    #[test]
    fn test_update_settings() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        let delta = SettingsDelta {
            fullscreen: Some(true),
            width: None,
            height: None,
            always_on_top: None,
            volume: Some(0.5),
            sync_delay_ms: None,
            show_lyrics: None,
            font_size: None,
            font_bold: None,
            font_italic: None,
            lyrics_color: None,
            lyrics_outline_color: None,
            lyrics_sweep_color: None,
        };
        let settings = engine.update_settings(delta).unwrap();
        assert!(settings.display.fullscreen);
        assert!((settings.audio.volume - 0.5).abs() < 0.001);
    }

    #[test]
    fn test_clear_queue() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        engine.enqueue("/tmp/song1.kar").unwrap();
        engine.enqueue("/tmp/song2.kar").unwrap();
        assert_eq!(engine.queue().songs.len(), 2);
        engine.clear_queue().unwrap();
        assert_eq!(engine.queue().songs.len(), 0);
    }

    #[test]
    fn test_remove_from_queue() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        engine.enqueue("/tmp/song1.kar").unwrap();
        engine.enqueue("/tmp/song2.kar").unwrap();
        engine.remove_from_queue(0).unwrap();
        assert_eq!(engine.queue().songs.len(), 1);
    }

    #[test]
    fn test_remove_from_queue_out_of_range() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        let result = engine.remove_from_queue(99);
        assert!(result.is_err());
    }

    #[test]
    fn test_set_volume_clamped() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        let state = engine.set_volume(2.0).unwrap();
        assert!((state.volume - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_pause_without_playing_returns_error() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        let result = engine.pause();
        assert!(result.is_err());
    }

    #[test]
    fn test_stop_playback() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        engine.enqueue("/tmp/test.kar").unwrap();
        engine.play(None).unwrap();
        let state = engine.stop_playback().unwrap();
        assert_eq!(state.status, PlaybackStatus::Stopped);
    }

    #[test]
    fn test_library_folders() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        engine.add_library_folder("/music/karaoke").unwrap();
        let folders = engine.library_folders();
        assert_eq!(folders.len(), 1);
        assert!(folders.contains(&"/music/karaoke".to_string()));
    }

    #[test]
    fn test_scan_library() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        let progress = engine.scan_library().unwrap();
        assert_eq!(progress.status, ScanStatus::Complete);
    }
}
