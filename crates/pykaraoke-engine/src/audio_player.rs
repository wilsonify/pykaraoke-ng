use rodio::{Decoder, OutputStream, Sink, Source};
use std::fs::File;
use std::io::BufReader;
use std::path::{Path, PathBuf};
use std::time::Instant;

/// Safe wrapper: `OutputStream` is !Send on Windows (cpal marks it so platform-agnostically),
/// but in practice sending is safe because we only access it via `&mut self` (exclusive
/// access) and it's never moved while being used. `EngineImpl` holds this behind a `Mutex`
/// in Tauri, so single-threaded access is guaranteed.
#[allow(dead_code)]
struct SendOutputStream(OutputStream);
unsafe impl Send for SendOutputStream {}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum AudioState {
    Stopped,
    Playing,
    Paused,
}

#[derive(Debug)]
pub enum AudioError {
    NoDevice,
    StreamError(String),
    LoadError(String),
}

pub struct AudioPlayer {
    sink: Option<Sink>,
    _stream: Option<SendOutputStream>,
    filepath: Option<PathBuf>,
    duration_ms: u64,
    state: AudioState,
    play_start: Option<Instant>,
    seek_offset: u64,
    paused_position: u64,
    volume: f64,
}

impl AudioPlayer {
    pub fn new() -> Result<Self, AudioError> {
        let (stream, stream_handle) = OutputStream::try_default()
            .map_err(|e| AudioError::StreamError(e.to_string()))?;
        let sink = Sink::try_new(&stream_handle)
            .map_err(|_| AudioError::NoDevice)?;
        Ok(Self {
            sink: Some(sink),
            _stream: Some(SendOutputStream(stream)),
            filepath: None,
            duration_ms: 0,
            state: AudioState::Stopped,
            play_start: None,
            seek_offset: 0,
            paused_position: 0,
            volume: 0.8,
        })
    }

    pub fn load(&mut self, path: &Path) -> Result<(), AudioError> {
        self.sink_stop_and_clear();

        let file = File::open(path)
            .map_err(|e| AudioError::LoadError(format!("Cannot open {}: {}", path.display(), e)))?;
        let reader = BufReader::new(file);
        let source = Decoder::new(reader)
            .map_err(|e| AudioError::LoadError(format!("Cannot decode {}: {}", path.display(), e)))?;
        let duration = source.total_duration().unwrap_or_default();
        let duration_ms = duration.as_millis() as u64;

        self.filepath = Some(path.to_path_buf());
        self.duration_ms = duration_ms;
        self.state = AudioState::Stopped;

        Ok(())
    }

    pub fn play(&mut self) {
        self.sink_stop_and_clear();
        if let Some(ref path) = self.filepath.clone() {
            if let Ok(file) = File::open(path) {
                let reader = BufReader::new(file);
                if let Ok(source) = Decoder::new(reader) {
                    if let Some(ref sink) = self.sink {
                        sink.append(source);
                        sink.play();
                    }
                    self.state = AudioState::Playing;
                    self.play_start = Some(Instant::now());
                    self.seek_offset = 0;
                    self.paused_position = 0;
                }
            }
        }
    }

    pub fn pause(&mut self) {
        if self.state == AudioState::Playing {
            self.paused_position = self.position_ms();
            if let Some(ref sink) = self.sink {
                sink.pause();
            }
            self.state = AudioState::Paused;
        }
    }

    pub fn resume(&mut self) {
        if self.state == AudioState::Paused {
            if let Some(ref sink) = self.sink {
                sink.play();
            }
            self.state = AudioState::Playing;
            self.seek_offset = self.paused_position;
            self.play_start = Some(Instant::now());
        }
    }

    pub fn stop(&mut self) {
        self.sink_stop_and_clear();
        self.state = AudioState::Stopped;
        self.play_start = None;
        self.seek_offset = 0;
        self.paused_position = 0;
    }

    pub fn seek(&mut self, position_ms: u64) {
        let was_paused = self.state == AudioState::Paused;
        let pos = position_ms;

        self.sink_stop_and_clear();

        if let Some(ref path) = self.filepath.clone() {
            if let Ok(file) = File::open(path) {
                let reader = BufReader::new(file);
                if let Ok(source) = Decoder::new(reader) {
                    let skipped = source.skip_duration(std::time::Duration::from_millis(pos));
                    if let Some(ref sink) = self.sink {
                        sink.append(skipped);
                        sink.play();
                    }
                    self.play_start = Some(Instant::now());
                    self.seek_offset = pos;
                    self.paused_position = pos;
                    self.state = AudioState::Playing;

                    if was_paused {
                        if let Some(ref sink) = self.sink {
                            sink.pause();
                        }
                        self.state = AudioState::Paused;
                    }
                }
            }
        }
    }

    pub fn set_volume(&mut self, volume: f64) {
        self.volume = volume.clamp(0.0, 1.0);
        if let Some(ref sink) = self.sink {
            sink.set_volume(self.volume as f32);
        }
    }

    pub fn volume(&self) -> f64 {
        self.volume
    }

    pub fn position_ms(&self) -> u64 {
        match self.state {
            AudioState::Playing => {
                match self.play_start {
                    Some(start) => self.seek_offset + start.elapsed().as_millis() as u64,
                    None => self.seek_offset,
                }
            }
            AudioState::Paused => self.paused_position,
            AudioState::Stopped => 0,
        }
    }

    pub fn duration_ms(&self) -> u64 {
        self.duration_ms
    }

    pub fn is_finished(&self) -> bool {
        if self.state == AudioState::Playing {
            if let Some(ref sink) = self.sink {
                if sink.empty() {
                    return true;
                }
            }
        }
        false
    }

    pub fn is_playing(&self) -> bool {
        self.state == AudioState::Playing
    }

    pub fn is_paused(&self) -> bool {
        self.state == AudioState::Paused
    }

    pub fn filepath(&self) -> Option<&Path> {
        self.filepath.as_deref()
    }

    pub fn has_audio(&self) -> bool {
        self.filepath.is_some()
    }

    fn sink_stop_and_clear(&mut self) {
        if let Some(ref sink) = self.sink {
            sink.stop();
            sink.clear();
        }
    }
}

/// Find a companion audio file for a karaoke file.
/// For a .cdg file, looks for .mp3, .ogg, .wav with the same stem.
/// For .kar/.mid files, also looks for companion audio.
/// Returns the path to the first found companion, or None.
pub fn find_companion_audio(filepath: &Path) -> Option<PathBuf> {
    let stem = filepath.file_stem()?;
    let parent = filepath.parent().unwrap_or_else(|| Path::new(""));
    for ext in &["mp3", "ogg", "wav"] {
        let candidate = parent.join(format!("{}.{}", stem.to_str()?, ext));
        if candidate.exists() {
            return Some(candidate);
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    // ── find_companion_audio ──────────────────────────────────────────

    #[test]
    fn test_companion_none_when_no_audio_file() {
        let dir = std::env::temp_dir().join("pykaraoke_test_companion_none");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        let cdg = dir.join("song.cdg");
        fs::write(&cdg, b"").unwrap();
        assert!(find_companion_audio(&cdg).is_none());
    }

    #[test]
    fn test_companion_finds_mp3() {
        let dir = std::env::temp_dir().join("pykaraoke_test_companion_mp3");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        let cdg = dir.join("song.cdg");
        let mp3 = dir.join("song.mp3");
        fs::write(&cdg, b"").unwrap();
        fs::write(&mp3, b"").unwrap();
        let found = find_companion_audio(&cdg);
        assert!(found.is_some());
        assert_eq!(found.unwrap(), mp3);
    }

    #[test]
    fn test_companion_prefers_mp3_over_ogg() {
        let dir = std::env::temp_dir().join("pykaraoke_test_companion_order");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        let cdg = dir.join("song.cdg");
        fs::write(&cdg, b"").unwrap();
        fs::write(dir.join("song.ogg"), b"").unwrap();
        fs::write(dir.join("song.mp3"), b"").unwrap();
        // Should return mp3 (first match)
        let found = find_companion_audio(&cdg);
        assert!(found.is_some());
        assert_eq!(found.unwrap().extension().unwrap(), "mp3");
    }

    #[test]
    fn test_companion_finds_wav() {
        let dir = std::env::temp_dir().join("pykaraoke_test_companion_wav");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        let cdg = dir.join("song.cdg");
        let wav = dir.join("song.wav");
        fs::write(&cdg, b"").unwrap();
        fs::write(&wav, b"").unwrap();
        let found = find_companion_audio(&cdg);
        assert!(found.is_some());
        assert_eq!(found.unwrap(), wav);
    }

    #[test]
    fn test_companion_works_with_kar() {
        let dir = std::env::temp_dir().join("pykaraoke_test_companion_kar");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        let kar = dir.join("song.kar");
        let mp3 = dir.join("song.mp3");
        fs::write(&kar, b"").unwrap();
        fs::write(&mp3, b"").unwrap();
        let found = find_companion_audio(&kar);
        assert_eq!(found, Some(mp3));
    }

    #[test]
    fn test_companion_returns_none_for_nonexistent_stem() {
        let dir = std::env::temp_dir().join("pykaraoke_test_companion_nostem");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        // File with no stem (e.g. just ".cdg")
        let no_stem = dir.join(".cdg");
        fs::write(&no_stem, b"").unwrap();
        assert!(find_companion_audio(&no_stem).is_none());
    }

    // ── AudioPlayer state machine (no audio device needed) ─────────────

    /// Creates an AudioPlayer wrapped in an Option for tests where
    /// audio hardware may not be available.
    fn try_create_player() -> Option<AudioPlayer> {
        AudioPlayer::new().ok()
    }

    #[test]
    fn test_initial_state() {
        if let Some(player) = try_create_player() {
            assert!(!player.is_playing());
            assert!(!player.is_paused());
            assert!(!player.has_audio());
            assert_eq!(player.position_ms(), 0);
            assert_eq!(player.duration_ms(), 0);
            assert!((player.volume() - 0.8).abs() < 0.001);
        }
    }

    #[test]
    fn test_play_pause_resume_state_transitions() {
        if let Some(mut player) = try_create_player() {
            // Cannot test load/play with real files, but can verify
            // the no-op paths don't panic.
            player.pause();   // no-op when stopped
            assert!(!player.is_paused());
            player.resume();  // no-op when stopped
            assert!(!player.is_playing());
            player.stop();    // no-op when stopped
            assert!(!player.is_playing());

            // seek on unloaded player = no-op
            player.seek(5000);
            assert_eq!(player.position_ms(), 0);
        }
    }

    #[test]
    fn test_volume_clamping() {
        if let Some(mut player) = try_create_player() {
            player.set_volume(1.5);
            assert!((player.volume() - 1.0).abs() < 0.001);
            player.set_volume(-0.5);
            assert!((player.volume() - 0.0).abs() < 0.001);
            player.set_volume(0.5);
            assert!((player.volume() - 0.5).abs() < 0.001);
        }
    }

    #[test]
    fn test_load_nonexistent_file_returns_error() {
        if let Some(mut player) = try_create_player() {
            let result = player.load(&Path::new("/nonexistent/file.mp3"));
            assert!(result.is_err());
            match result.unwrap_err() {
                AudioError::LoadError(msg) => {
                    assert!(msg.contains("Cannot open"));
                }
                _ => panic!("Expected LoadError"),
            }
        }
    }

    #[test]
    fn test_is_finished_returns_false_when_stopped() {
        if let Some(player) = try_create_player() {
            assert!(!player.is_finished());
        }
    }
}
