use crate::views::*;

pub trait EventBus: Send + Sync {
    fn emit_playback_changed(&self, state: PlaybackState);
    fn emit_queue_changed(&self, queue: QueueView);
    fn emit_library_changed(&self, library: LibraryView);
    fn emit_settings_changed(&self, settings: SettingsView);
    fn emit_scan_progress(&self, progress: LibraryScanProgress);
    fn emit_error(&self, error: EngineErrorInfo);
    fn emit_cdg_frame(&self, frame: CdgFrameView);
    fn emit_lyrics_changed(&self, lyrics: LyricsView);
}
