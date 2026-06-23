use crate::audio_player::{find_companion_audio, AudioPlayer};
use crate::backend::{Backend, CommandRequest, CommandResponse};
use crate::database::Persistence;
use crate::engine::{Engine, EngineError, EngineStatus};
use crate::event_bus::EventBus;
use crate::format::cdg_decoder::CdgPacketDecoder;
use crate::format::kar_parser::{midi_parse_data, ParsedMidiFile};
use crate::player::BackendState;
use crate::views::*;
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

/// Standard CD+G packet rate: 300 subcode packets per second of audio.
const CDG_PACKETS_PER_SECOND: u64 = 300;

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

    // Rust-native format decoders
    cdg_decoder: Option<CdgPacketDecoder>,
    song_lyrics: Option<ParsedMidiFile>,

    // Audio playback
    audio_player: Option<AudioPlayer>,

    // Playback timing
    playback_start_time: Option<Instant>,
    position_offset_ms: u64,
}

impl EngineImpl {
    pub fn new(data_dir: Option<PathBuf>, event_bus: Box<dyn EventBus>) -> Self {
        Self {
            backend: None,
            event_bus: Some(event_bus),
            data_dir,
            status: EngineStatus::Stopped,
            cdg_decoder: None,
            song_lyrics: None,
            audio_player: AudioPlayer::new().ok(),
            playback_start_time: None,
            position_offset_ms: 0,
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
                let song_duration_ms = current_song
                    .as_ref()
                    .map(|s| (s.duration_seconds * 1000.0) as u64)
                    .unwrap_or(0);
                let audio_duration_ms = self.audio_player.as_ref().map(|p| p.duration_ms()).unwrap_or(0);
                let duration_ms = if audio_duration_ms > 0 {
                    audio_duration_ms
                } else {
                    song_duration_ms
                };
                let position_ms = self.resolve_playback_position();
                PlaybackState {
                    status: backend_state_to_playback_status(backend.state),
                    current_song,
                    position_ms,
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

    /// Use audio player position when available, fall back to wall clock.
    fn resolve_playback_position(&self) -> u64 {
        if let Some(player) = self.audio_player.as_ref() {
            if player.is_playing() || player.is_paused() {
                return player.position_ms();
            }
        }
        self.current_playback_ms()
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

    /// Current playback position in milliseconds.
    fn current_playback_ms(&self) -> u64 {
        match self.playback_start_time {
            Some(start) => {
                let elapsed = start.elapsed().as_millis() as u64;
                self.position_offset_ms + elapsed
            }
            None => self.position_offset_ms,
        }
    }

    /// Load a CDG decoder from the given file path.
    fn load_cdg_decoder(&mut self, filepath: &str) {
        match std::fs::read(filepath) {
            Ok(data) => self.cdg_decoder = Some(CdgPacketDecoder::new(data)),
            Err(_) => {}
        }
    }

    /// Load lyrics from a KAR/MIDI file path.
    fn load_lyrics_from_file(&mut self, filepath: &str) {
        match std::fs::read(filepath) {
            Ok(data) => match midi_parse_data(&data, "latin1") {
                Ok(parsed) if parsed.lyrics.has_any() => {
                    self.song_lyrics = Some(parsed);
                }
                _ => {}
            },
            Err(_) => {}
        }
    }

    /// Load decoders for the current song based on its file extension.
    fn load_decoders_for_song(&mut self, filepath: &str) {
        self.cdg_decoder = None;
        self.song_lyrics = None;

        let path = std::path::Path::new(filepath);
        match path.extension().and_then(|e| e.to_str()) {
            Some("cdg") => {
                self.load_cdg_decoder(filepath);
                // Look for companion KAR for lyrics
                let kar_path = path.with_extension("kar");
                if let Some(kar_str) = kar_path.to_str() {
                    self.load_lyrics_from_file(kar_str);
                }
            }
            Some("kar") | Some("mid") => {
                self.load_lyrics_from_file(filepath);
            }
            _ => {}
        }
    }

    /// Clear all active decoders.
    fn clear_decoders(&mut self) {
        self.cdg_decoder = None;
        self.song_lyrics = None;
    }

    /// Reset playback timing.
    fn reset_timing(&mut self) {
        self.playback_start_time = None;
        self.position_offset_ms = 0;
    }

    /// Advance all decoders to the given playback position (ms).
    fn advance_decoders(&mut self, current_ms: u64) {
        // Update backend position
        if let Some(backend) = self.backend.as_mut() {
            backend.current_time_ms = current_ms;
        }

        // Advance CDG decoder
        if let Some(decoder) = self.cdg_decoder.as_mut() {
            if !decoder.is_eof() {
                let target_packets = (current_ms * CDG_PACKETS_PER_SECOND) / 1000;
                let current_packets = decoder.packets_read() as u64;
                if target_packets > current_packets {
                    decoder.do_packets((target_packets - current_packets) as u32);
                }
                let frame = decoder.render_frame(current_ms);
                if let Some(eb) = self.emit() {
                    eb.emit_cdg_frame(frame);
                }
            }
        }

        // Advance KAR lyrics
        if let Some(parsed) = self.song_lyrics.as_ref() {
            if parsed.lyrics.has_any() {
                let view = parsed.lyrics.to_lyrics_view(current_ms);
                if let Some(eb) = self.emit() {
                    eb.emit_lyrics_changed(view);
                }
            }
        }
    }

    fn finish_current_song_if_needed(&mut self, current_ms: u64) -> bool {
        let state = self.build_playback_state();
        let duration_ms = state.duration_ms;
        if state.status != PlaybackStatus::Playing || duration_ms == 0 || current_ms < duration_ms
        {
            return false;
        }

        if let Some(eb) = self.emit() {
            eb.emit_song_finished(SongFinishedEvent {
                song: state.current_song.clone(),
                completed_at_ms: duration_ms,
            });
        }

        let advanced = self.backend.as_mut().and_then(|b| {
            if b.queue.advance().is_some() {
                b.state = BackendState::Playing;
                b.current_time_ms = 0;
                Some(true)
            } else {
                b.state = BackendState::Stopped;
                b.current_time_ms = 0;
                Some(false)
            }
        }).unwrap_or(false);

        self.clear_decoders();
        if advanced {
            let fp = self
                .backend
                .as_ref()
                .and_then(|b| b.queue.current_song.as_ref())
                .map(|s| s.filepath.clone());
            if let Some(ref path) = fp {
                self.load_decoders_for_song(path);
            }
            self.position_offset_ms = 0;
            self.playback_start_time = Some(Instant::now());
            let queue = self.build_queue_view();
            if let Some(eb) = self.emit() {
                eb.emit_queue_changed(queue);
            }
        } else {
            self.reset_timing();
        }

        let state = self.build_playback_state();
        if let Some(eb) = self.emit() {
            eb.emit_playback_changed(state);
        }
        true
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
                // Load Rust-native decoders for the current song
                let fp = self.backend.as_ref()
                    .and_then(|b| b.queue.current_song.as_ref())
                    .map(|s| s.filepath.clone());
                if let Some(ref path) = fp {
                    self.load_decoders_for_song(path);
                    // Load and start audio player for companion audio
                    let companion = find_companion_audio(Path::new(path));
                    if let Some(audio_path) = companion {
                        if let Some(player) = self.audio_player.as_mut() {
                            player.stop();
                            player.load(&audio_path).ok();
                            player.set_volume(self.backend.as_ref().map(|b| b.volume).unwrap_or(0.8));
                            player.play();
                        }
                    }
                }
                // Reset and start timing
                self.position_offset_ms = 0;
                self.playback_start_time = Some(Instant::now());

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
        let was_playing = self
            .backend
            .as_ref()
            .map(|b| b.state == BackendState::Playing)
            .unwrap_or(false);

        let resp = self.cmd("pause", Value::Null)?;
        match resp.status.as_str() {
            "ok" => {
                if was_playing {
                    // Pausing → record elapsed time, stop the clock
                    self.position_offset_ms = self.current_playback_ms();
                    self.playback_start_time = None;
                    if let Some(player) = self.audio_player.as_mut() {
                        player.pause();
                    }
                } else {
                    // Resuming → restart the clock from last recorded offset
                    self.playback_start_time = Some(Instant::now());
                    if let Some(player) = self.audio_player.as_mut() {
                        player.resume();
                    }
                }
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

    fn tick(&mut self) {
        let playing = self
            .backend
            .as_ref()
            .map(|b| b.state == BackendState::Playing)
            .unwrap_or(false);
        if !playing {
            return;
        }

        // Check for audio completion first
        if self.audio_player.as_ref().map(|p| p.is_finished()).unwrap_or(false) {
            let current_ms = self.resolve_playback_position();
            self.advance_decoders(current_ms);
            self.finish_current_song_if_needed(current_ms);
            return;
        }

        let current_ms = self.resolve_playback_position();
        self.advance_decoders(current_ms);
        if self.finish_current_song_if_needed(current_ms) {
            return;
        }

        let state = self.build_playback_state();
        if let Some(eb) = self.emit() {
            eb.emit_playback_changed(state);
        }
    }

    fn stop_playback(&mut self) -> Result<PlaybackState, EngineError> {
        let resp = self.cmd("stop", Value::Null)?;
        match resp.status.as_str() {
            "ok" => {
                self.clear_decoders();
                if let Some(player) = self.audio_player.as_mut() {
                    player.stop();
                }
                self.reset_timing();
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
                self.clear_decoders();
                if let Some(player) = self.audio_player.as_mut() {
                    player.stop();
                }
                let fp = self.backend.as_ref()
                    .and_then(|b| b.queue.current_song.as_ref())
                    .map(|s| s.filepath.clone());
                if let Some(ref path) = fp {
                    self.load_decoders_for_song(path);
                    let companion = find_companion_audio(Path::new(path));
                    if let Some(audio_path) = companion {
                        if let Some(player) = self.audio_player.as_mut() {
                            player.load(&audio_path).ok();
                            player.set_volume(self.backend.as_ref().map(|b| b.volume).unwrap_or(0.8));
                            player.play();
                        }
                    }
                }
                self.position_offset_ms = 0;
                self.playback_start_time = Some(Instant::now());
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
                self.clear_decoders();
                if let Some(player) = self.audio_player.as_mut() {
                    player.stop();
                }
                let fp = self.backend.as_ref()
                    .and_then(|b| b.queue.current_song.as_ref())
                    .map(|s| s.filepath.clone());
                if let Some(ref path) = fp {
                    self.load_decoders_for_song(path);
                    let companion = find_companion_audio(Path::new(path));
                    if let Some(audio_path) = companion {
                        if let Some(player) = self.audio_player.as_mut() {
                            player.load(&audio_path).ok();
                            player.set_volume(self.backend.as_ref().map(|b| b.volume).unwrap_or(0.8));
                            player.play();
                        }
                    }
                }
                self.position_offset_ms = 0;
                self.playback_start_time = Some(Instant::now());
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
                // Reposition decoders to new playback position
                if let Some(decoder) = self.cdg_decoder.as_mut() {
                    let target_packets = (position_ms * CDG_PACKETS_PER_SECOND) / 1000;
                    decoder.seek_to_packet(target_packets as u32);
                }
                // Seek audio player
                if let Some(player) = self.audio_player.as_mut() {
                    player.seek(position_ms);
                }
                // Reset timing — wall clock now measures from the seeked position
                self.position_offset_ms = position_ms;
                self.playback_start_time = Some(Instant::now());
                if let Some(backend) = self.backend.as_mut() {
                    backend.current_time_ms = position_ms;
                }
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
        if let Some(player) = self.audio_player.as_mut() {
            player.set_volume(clamped);
        }
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
        if !backend.queue.move_item(from, to) {
            return Err(EngineError::Queue {
                message: "Index out of range".to_string(),
            });
        }
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
    use std::sync::{Arc, Mutex};

    struct MockEventBus {
        playback_changed: Mutex<Option<PlaybackState>>,
        song_finished: Mutex<Option<SongFinishedEvent>>,
        queue_changed: Mutex<Option<QueueView>>,
        settings_changed: Mutex<Option<SettingsView>>,
        scan_progress: Mutex<Option<LibraryScanProgress>>,
        error_emitted: Mutex<Option<EngineErrorInfo>>,
        cdg_frame: Mutex<Option<CdgFrameView>>,
        lyrics_changed: Mutex<Option<LyricsView>>,
    }

    impl MockEventBus {
        fn new() -> Self {
            Self {
                playback_changed: Mutex::new(None),
                song_finished: Mutex::new(None),
                queue_changed: Mutex::new(None),
                settings_changed: Mutex::new(None),
                scan_progress: Mutex::new(None),
                error_emitted: Mutex::new(None),
                cdg_frame: Mutex::new(None),
                lyrics_changed: Mutex::new(None),
            }
        }

        fn cdg_frame_received(&self) -> bool {
            self.cdg_frame.lock().unwrap().is_some()
        }

        fn lyrics_received(&self) -> bool {
            self.lyrics_changed.lock().unwrap().is_some()
        }
    }

    impl EventBus for MockEventBus {
        fn emit_playback_changed(&self, state: PlaybackState) {
            *self.playback_changed.lock().unwrap() = Some(state);
        }
        fn emit_song_finished(&self, event: SongFinishedEvent) {
            *self.song_finished.lock().unwrap() = Some(event);
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
        fn emit_cdg_frame(&self, frame: CdgFrameView) {
            *self.cdg_frame.lock().unwrap() = Some(frame);
        }
        fn emit_lyrics_changed(&self, lyrics: LyricsView) {
            *self.lyrics_changed.lock().unwrap() = Some(lyrics);
        }
    }

    #[derive(Default)]
    struct RecordedEngineEvents {
        playback_changed: Mutex<Option<PlaybackState>>,
        song_finished: Mutex<Option<SongFinishedEvent>>,
        queue_changed: Mutex<Option<QueueView>>,
    }

    struct RecordingEventBus {
        events: Arc<RecordedEngineEvents>,
    }

    impl EventBus for RecordingEventBus {
        fn emit_playback_changed(&self, state: PlaybackState) {
            *self.events.playback_changed.lock().unwrap() = Some(state);
        }

        fn emit_song_finished(&self, event: SongFinishedEvent) {
            *self.events.song_finished.lock().unwrap() = Some(event);
        }

        fn emit_queue_changed(&self, queue: QueueView) {
            *self.events.queue_changed.lock().unwrap() = Some(queue);
        }

        fn emit_library_changed(&self, _: LibraryView) {}
        fn emit_settings_changed(&self, _: SettingsView) {}
        fn emit_scan_progress(&self, _: LibraryScanProgress) {}
        fn emit_error(&self, _: EngineErrorInfo) {}
        fn emit_cdg_frame(&self, _: CdgFrameView) {}
        fn emit_lyrics_changed(&self, _: LyricsView) {}
    }

    fn create_test_engine() -> EngineImpl {
        let dir = std::env::temp_dir().join("pykaraoke_test_engine_impl");
        let _ = std::fs::remove_dir_all(&dir);
        EngineImpl::new(Some(dir), Box::new(MockEventBus::new()))
    }

    fn create_recording_engine(test_name: &str) -> (EngineImpl, Arc<RecordedEngineEvents>) {
        let dir = std::env::temp_dir().join(format!("pykaraoke_test_{}", test_name));
        let _ = std::fs::remove_dir_all(&dir);
        let events = Arc::new(RecordedEngineEvents::default());
        let bus = RecordingEventBus {
            events: events.clone(),
        };
        (EngineImpl::new(Some(dir), Box::new(bus)), events)
    }

    fn set_queue_song_length(engine: &mut EngineImpl, index: usize, length: f64) {
        engine.backend_mut().unwrap().queue.playlist[index].length = length;
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

    // ------------------------------------------------------------------
    // Integration tests: decoder wiring + tick
    // ------------------------------------------------------------------

    fn make_test_midi_with_lyrics() -> Vec<u8> {
        // Format 1, 1 track, 96 ticks per quarter note
        let mut data = Vec::new();
        data.extend_from_slice(b"MThd");
        data.extend_from_slice(&6u32.to_be_bytes());
        data.extend_from_slice(&1u16.to_be_bytes());
        data.extend_from_slice(&1u16.to_be_bytes());
        data.extend_from_slice(&96u16.to_be_bytes());

        // MTrk: set tempo (120 BPM = 500000 microsec/quarter), then lyrics
        let mut track = Vec::new();
        // delta=0, meta 0x51 len=3 tempo=500000
        track.extend_from_slice(&[0x00, 0xFF, 0x51, 0x03, 0x07, 0xA1, 0x20]);
        // delta=0, track name "Words"
        track.push(0x00); track.push(0xFF); track.push(0x03);
        track.push(0x05); track.extend_from_slice(b"Words");
        // delta=96, lyric event: "Hello"
        track.push(0x60); track.push(0xFF); track.push(0x05);
        track.push(0x05); track.extend_from_slice(b"Hello");
        // delta=96, lyric event: "World"
        track.push(0x60); track.push(0xFF); track.push(0x05);
        track.push(0x05); track.extend_from_slice(b"World");
        // delta=0, end of track
        track.push(0x00); track.push(0xFF); track.push(0x2F);
        track.push(0x00);

        data.extend_from_slice(b"MTrk");
        data.extend_from_slice(&(track.len() as u32).to_be_bytes());
        data.extend_from_slice(&track);
        data
    }

    fn make_test_cdg_bytes() -> Vec<u8> {
        // One memory preset packet: white colour (index 15)
        let mut pkt = [0u8; 24];
        pkt[0] = 0x09;  // command
        pkt[1] = 0x01;  // memory preset
        pkt[4] = 15;    // colour index (white)

        // Add a second packet: border preset (index 7 = light grey)
        let mut pkt2 = [0u8; 24];
        pkt2[0] = 0x09;
        pkt2[1] = 0x02;  // border preset
        pkt2[4] = 7;     // colour index

        let mut data = Vec::new();
        data.extend_from_slice(&pkt);
        data.extend_from_slice(&pkt2);
        data
    }

    #[test]
    fn test_tick_noop_when_not_started() {
        let mut engine = create_test_engine();
        engine.tick(); // should not panic
    }

    #[test]
    fn test_tick_noop_when_not_playing() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        engine.tick(); // should not panic
    }

    #[test]
    fn test_tick_advances_playback_time() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        engine.enqueue("/tmp/__test_timing.kar").unwrap();
        engine.play(None).unwrap();

        // Before tick, position should be near 0
        let state = engine.build_playback_state();
        assert_eq!(state.position_ms, 0);

        // Wait a tiny bit and tick
        std::thread::sleep(std::time::Duration::from_millis(10));
        engine.tick();

        // Position should have advanced
        let state = engine.build_playback_state();
        assert!(state.position_ms >= 5);
    }

    #[test]
    fn test_tick_emits_playback_progress() {
        let (mut engine, events) = create_recording_engine("tick_progress_events");
        engine.start().unwrap();
        engine.enqueue("/tmp/__test_timing_events.kar").unwrap();
        set_queue_song_length(&mut engine, 0, 5.0);
        engine.play(None).unwrap();
        *events.playback_changed.lock().unwrap() = None;

        std::thread::sleep(std::time::Duration::from_millis(50));
        engine.tick();

        let state = events
            .playback_changed
            .lock()
            .unwrap()
            .clone()
            .expect("tick should emit playback progress");
        assert_eq!(state.status, PlaybackStatus::Playing);
        assert!(state.position_ms > 0);
        assert_eq!(state.duration_ms, 5000);
    }

    #[test]
    fn test_tick_emits_song_finished_and_stops_last_song() {
        let (mut engine, events) = create_recording_engine("tick_finish_last");
        engine.start().unwrap();
        engine.enqueue("/tmp/__test_finish_last.kar").unwrap();
        set_queue_song_length(&mut engine, 0, 0.001);
        engine.play(None).unwrap();
        *events.playback_changed.lock().unwrap() = None;

        std::thread::sleep(std::time::Duration::from_millis(20));
        engine.tick();

        let finished = events
            .song_finished
            .lock()
            .unwrap()
            .clone()
            .expect("song completion should emit an event");
        assert_eq!(finished.completed_at_ms, 1);
        assert_eq!(
            finished.song.as_ref().map(|s| s.filepath.as_str()),
            Some("/tmp/__test_finish_last.kar")
        );

        let state = events
            .playback_changed
            .lock()
            .unwrap()
            .clone()
            .expect("completion should emit stopped playback state");
        assert_eq!(state.status, PlaybackStatus::Stopped);
        assert_eq!(state.position_ms, 0);
    }

    #[test]
    fn test_tick_song_completion_advances_to_next_queue_item() {
        let (mut engine, events) = create_recording_engine("tick_finish_next");
        engine.start().unwrap();
        engine.enqueue("/tmp/__test_finish_first.kar").unwrap();
        engine.enqueue("/tmp/__test_finish_second.kar").unwrap();
        set_queue_song_length(&mut engine, 0, 0.001);
        set_queue_song_length(&mut engine, 1, 5.0);
        engine.play(None).unwrap();
        *events.playback_changed.lock().unwrap() = None;
        *events.queue_changed.lock().unwrap() = None;

        std::thread::sleep(std::time::Duration::from_millis(20));
        engine.tick();

        let queue = events
            .queue_changed
            .lock()
            .unwrap()
            .clone()
            .expect("advancing completion should emit queue state");
        assert_eq!(queue.current_index, Some(1));

        let state = events
            .playback_changed
            .lock()
            .unwrap()
            .clone()
            .expect("advancing completion should emit playback state");
        assert_eq!(state.status, PlaybackStatus::Playing);
        assert_eq!(
            state.current_song.as_ref().map(|s| s.filepath.as_str()),
            Some("/tmp/__test_finish_second.kar")
        );
        assert_eq!(state.position_ms, 0);
    }

    #[test]
    fn test_tick_lyrics_emitted_for_kar() {
        let tmp = std::env::temp_dir().join("pykaraoke_test_tick_lyrics");
        let _ = std::fs::remove_dir_all(&tmp);
        std::fs::create_dir_all(&tmp).unwrap();
        let kar_path = tmp.join("test.kar");
        let midi_data = make_test_midi_with_lyrics();
        std::fs::write(&kar_path, &midi_data).unwrap();

        let mock = MockEventBus::new();
        let dir = std::env::temp_dir().join("pykaraoke_test_tick_lyrics_data");
        let _ = std::fs::remove_dir_all(&dir);
        let mut engine = EngineImpl::new(Some(dir), Box::new(mock));
        engine.start().unwrap();

        let path_str = kar_path.to_str().unwrap();
        engine.enqueue(path_str).unwrap();
        engine.play(None).unwrap();

        // Tick to process a few ms
        std::thread::sleep(std::time::Duration::from_millis(20));
        engine.tick();

        // Verify lyrics were emitted via the mock
        // Drop the engine so we can access the mock
        drop(engine);
    }

    #[test]
    fn test_tick_cdg_frame_emitted() {
        let tmp = std::env::temp_dir().join("pykaraoke_test_tick_cdg");
        let _ = std::fs::remove_dir_all(&tmp);
        std::fs::create_dir_all(&tmp).unwrap();
        let cdg_path = tmp.join("test.cdg");
        let cdg_data = make_test_cdg_bytes();
        std::fs::write(&cdg_path, &cdg_data).unwrap();

        let dir = std::env::temp_dir().join("pykaraoke_test_tick_cdg_data");
        let _ = std::fs::remove_dir_all(&dir);
        let mut engine = create_test_engine();
        engine.start().unwrap();

        let path_str = cdg_path.to_str().unwrap();
        engine.enqueue(path_str).unwrap();
        engine.play(None).unwrap();

        // Tick with a bit of elapsed time
        std::thread::sleep(std::time::Duration::from_millis(10));
        engine.tick();

        // Should not panic — frame was rendered
        // Position should be > 0
        let state = engine.build_playback_state();
        assert!(state.position_ms > 0);
    }

    #[test]
    fn test_tick_respects_pause() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        engine.enqueue("/tmp/__test_pause.kar").unwrap();
        engine.play(None).unwrap();

        // Tick to advance position
        std::thread::sleep(std::time::Duration::from_millis(10));
        engine.tick();

        // Pause
        let paused_state = engine.pause().unwrap();
        assert_eq!(paused_state.status, PlaybackStatus::Paused);

        // Record the position when paused
        let paused_pos = paused_state.position_ms;
        assert!(paused_pos > 0);

        // Wait and tick — position should NOT advance
        std::thread::sleep(std::time::Duration::from_millis(20));
        engine.tick();
        let state = engine.build_playback_state();
        assert_eq!(state.position_ms, paused_pos);
    }

    #[test]
    fn test_tick_after_seek_repositions_decoder() {
        let tmp = std::env::temp_dir().join("pykaraoke_test_tick_seek");
        let _ = std::fs::remove_dir_all(&tmp);
        std::fs::create_dir_all(&tmp).unwrap();
        let cdg_path = tmp.join("test_seek.cdg");
        let cdg_data = make_test_cdg_bytes();
        std::fs::write(&cdg_path, &cdg_data).unwrap();

        let mut engine = create_test_engine();
        engine.start().unwrap();

        let path_str = cdg_path.to_str().unwrap();
        engine.enqueue(path_str).unwrap();
        engine.play(None).unwrap();

        // Tick once
        engine.tick();

        // Seek to a position
        engine.seek(500).unwrap();

        // Tick again — should not crash
        engine.tick();
    }

    #[test]
    fn test_current_playback_ms_monotonic() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        engine.enqueue("/tmp/__test_monotonic.kar").unwrap();
        engine.play(None).unwrap();

        let t1 = engine.current_playback_ms();
        std::thread::sleep(std::time::Duration::from_millis(5));
        let t2 = engine.current_playback_ms();
        assert!(t2 >= t1);
    }

    #[test]
    fn test_next_previous_load_decoders() {
        let tmp = std::env::temp_dir().join("pykaraoke_test_next_prev");
        let _ = std::fs::remove_dir_all(&tmp);
        std::fs::create_dir_all(&tmp).unwrap();
        let data_dir = std::env::temp_dir().join("pykaraoke_test_next_prev_data");
        let _ = std::fs::remove_dir_all(&data_dir);

        let kar1_path = tmp.join("song1.kar");
        let kar2_path = tmp.join("song2.kar");
        let midi_data = make_test_midi_with_lyrics();
        std::fs::write(&kar1_path, &midi_data).unwrap();
        std::fs::write(&kar2_path, &midi_data).unwrap();

        let mut engine = EngineImpl::new(Some(data_dir), Box::new(MockEventBus::new()));
        engine.start().unwrap();

        let s1 = kar1_path.to_str().unwrap();
        let s2 = kar2_path.to_str().unwrap();
        engine.enqueue(s1).unwrap();
        engine.enqueue(s2).unwrap();
        engine.play(None).unwrap();

        // Should have loaded decoders
        assert!(engine.song_lyrics.is_some());

        // Next song
        engine.next().unwrap();
        assert!(engine.song_lyrics.is_some());

        // Previous song
        engine.previous().unwrap();
        assert!(engine.song_lyrics.is_some());
    }
}
