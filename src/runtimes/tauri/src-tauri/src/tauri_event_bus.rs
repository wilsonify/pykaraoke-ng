use pykaraoke_engine::EventBus;
use pykaraoke_engine::views::*;
use tauri::{AppHandle, Manager};

pub struct TauriEventBus {
    app_handle: AppHandle,
}

impl TauriEventBus {
    pub fn new(app_handle: AppHandle) -> Self {
        Self { app_handle }
    }
}

impl EventBus for TauriEventBus {
    fn emit_playback_changed(&self, state: PlaybackState) {
        self.app_handle.emit_all("engine:playback_changed", state).ok();
    }

    fn emit_song_finished(&self, event: SongFinishedEvent) {
        self.app_handle.emit_all("engine:song_finished", event).ok();
    }

    fn emit_queue_changed(&self, queue: QueueView) {
        self.app_handle.emit_all("engine:queue_changed", queue).ok();
    }

    fn emit_library_changed(&self, library: LibraryView) {
        self.app_handle.emit_all("engine:library_changed", library).ok();
    }

    fn emit_settings_changed(&self, settings: SettingsView) {
        self.app_handle.emit_all("engine:settings_changed", settings).ok();
    }

    fn emit_scan_progress(&self, progress: LibraryScanProgress) {
        self.app_handle.emit_all("engine:scan_progress", progress).ok();
    }

    fn emit_error(&self, error: EngineErrorInfo) {
        self.app_handle.emit_all("engine:error", error).ok();
    }

    fn emit_cdg_frame(&self, frame: CdgFrameView) {
        self.app_handle.emit_all("engine:cdg_frame", frame).ok();
    }

    fn emit_lyrics_changed(&self, lyrics: LyricsView) {
        self.app_handle.emit_all("engine:lyrics_changed", lyrics).ok();
    }
}


