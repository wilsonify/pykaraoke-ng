use rodio::{Decoder, OutputStream, OutputStreamHandle, Sink, Source};
use std::fs::File;
use std::io::BufReader;
use std::path::{Path, PathBuf};
use std::time::Instant;

/// Safe wrapper: `OutputStream` is !Send on Windows (cpal marks it so platform-agnostically),
/// but in practice sending is safe because we only access it via `&mut self` (exclusive
/// access) and it's never moved while being used. `EngineImpl` holds this behind a `Mutex`
/// in Tauri, so single-threaded access is guaranteed.
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
    _stream_handle: Option<OutputStreamHandle>,
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
            _stream_handle: Some(stream_handle),
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
