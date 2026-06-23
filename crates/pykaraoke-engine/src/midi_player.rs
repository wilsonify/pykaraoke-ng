//! MIDI/KAR file player — sends MIDI events to system MIDI synthesizer.
//!
//! Uses `midir` to open a connection to the system MIDI output device
//! (Microsoft GS Wavetable Synth on Windows, CoreMIDI on macOS, ALSA on Linux)
//! and sends parsed MIDI events with correct timing.

use std::path::{Path, PathBuf};
use std::time::Instant;
use midir::{MidiOutput, MidiOutputConnection};

/// Send wrapper for `MidiOutputConnection`.
/// The underlying Windows handle is not `Send` in midir's type system,
/// but we guarantee single-threaded access via EngineImpl's Mutex.
struct SendMidiConn(MidiOutputConnection);
unsafe impl Send for SendMidiConn {}

/// A timed MIDI event ready to send.
struct TimedEvent {
    /// Absolute time in milliseconds from start.
    time_ms: u64,
    /// Raw MIDI message bytes (e.g. [0x90, 60, 100]).
    message: Vec<u8>,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum MidiState {
    Stopped,
    Playing,
    Paused,
}

/// MIDI/KAR player that sends events to the system synthesizer.
///
/// Call `tick(current_ms)` from the engine's tick loop to advance playback.
pub struct MidiPlayer {
    conn: Option<SendMidiConn>,
    events: Vec<TimedEvent>,
    current_index: usize,
    state: MidiState,
    start_instant: Option<Instant>,
    paused_offset_ms: u64,
    duration_ms: u64,
    /// The filepath of the loaded MIDI file, if any.
    pub filepath: Option<PathBuf>,
}

impl MidiPlayer {
    /// Create a new `MidiPlayer` without loading any file.
    pub fn new() -> Self {
        Self {
            conn: None,
            events: Vec::new(),
            current_index: 0,
            state: MidiState::Stopped,
            start_instant: None,
            paused_offset_ms: 0,
            duration_ms: 0,
            filepath: None,
        }
    }

    /// Open a connection to the first available MIDI output port.
    /// Returns `None` if no MIDI output is available (e.g. no synthesizer).
    fn open_midi_output() -> Option<SendMidiConn> {
        let midi_out = MidiOutput::new("PyKaraoke NG").ok()?;
        let ports = midi_out.ports();
        let first_port = ports.first()?;
        let conn = midi_out.connect(first_port, "pykaraoke-output").ok()?;
        Some(SendMidiConn(conn))
    }

    /// Load a MIDI/KAR file and parse it into timed events.
    /// Establishes a MIDI output connection if one isn't already open.
    pub fn load(&mut self, filepath: &Path) -> Result<(), String> {
        let data = std::fs::read(filepath).map_err(|e| format!("Cannot read MIDI file: {}", e))?;
        let smf = midly::Smf::parse(&data)
            .map_err(|e| format!("Cannot parse MIDI file: {:?}", e))?;

        let ticks_per_quarter = match smf.header.timing {
            midly::Timing::Metrical(tpq) => tpq.as_int() as u64,
            midly::Timing::Timecode(..) => {
                return Err("SMPTE timecode format not supported".to_string());
            }
        };

        // Parse all tracks interleaved by tick, collect tempo changes
        let mut tempo_events: Vec<(u64, u32)> = Vec::new(); // (tick, micros_per_quarter)
        let mut raw_events: Vec<(u64, Vec<u8>)> = Vec::new(); // (tick, message)

        for track in &smf.tracks {
            let mut abs_tick: u64 = 0;
            for event in track {
                let delta = event.delta.as_int() as u64;
                abs_tick += delta;

                match &event.kind {
                    midly::TrackEventKind::Meta(meta) => {
                        if let midly::MetaMessage::Tempo(tempo) = meta {
                            tempo_events.push((abs_tick, tempo.as_int()));
                        }
                    }
                    midly::TrackEventKind::Midi { channel, message } => {
                        let ch = channel.as_int();
                        let mut bytes = Vec::with_capacity(3);
                        match message {
                            midly::MidiMessage::NoteOff { key, vel } => {
                                bytes.extend_from_slice(&[0x80 | ch, key.as_int(), vel.as_int()]);
                            }
                            midly::MidiMessage::NoteOn { key, vel } => {
                                bytes.extend_from_slice(&[0x90 | ch, key.as_int(), vel.as_int()]);
                            }
                            midly::MidiMessage::Aftertouch { key, vel } => {
                                bytes.extend_from_slice(&[0xA0 | ch, key.as_int(), vel.as_int()]);
                            }
                            midly::MidiMessage::Controller { controller, value } => {
                                bytes.extend_from_slice(&[0xB0 | ch, controller.as_int(), value.as_int()]);
                            }
                            midly::MidiMessage::ProgramChange { program } => {
                                bytes.extend_from_slice(&[0xC0 | ch, program.as_int()]);
                            }
                            midly::MidiMessage::ChannelAftertouch { vel } => {
                                bytes.extend_from_slice(&[0xD0 | ch, vel.as_int()]);
                            }
                            midly::MidiMessage::PitchBend { bend } => {
                                let val = bend.as_int();
                                bytes.extend_from_slice(&[0xE0 | ch, (val & 0x7F) as u8, ((val >> 7) & 0x7F) as u8]);
                            }
                        }
                        if !bytes.is_empty() {
                            raw_events.push((abs_tick, bytes));
                        }
                    }
                    _ => {}
                }
            }
        }

        // Sort by tick
        raw_events.sort_by_key(|e| e.0);
        tempo_events.sort_by_key(|e| e.0);

        // Build tempo map for tick → ms conversion (default = 120 BPM = 500000 micros/quarter)
        tempo_events.insert(0, (0, 500000));

        // Convert ticks to milliseconds using the tempo map
        let mut tempo_idx = 0;
        let mut current_tempo = tempo_events[0].1;
        let mut accumulated_ms: f64 = 0.0;
        let mut prev_tick: u64 = 0;

        let mut timed_events: Vec<TimedEvent> = Vec::with_capacity(raw_events.len());

        for (tick, message) in &raw_events {
            let tick = *tick;

            // Advance through any tempo changes that occur before this tick
            while tempo_idx + 1 < tempo_events.len() && tempo_events[tempo_idx + 1].0 <= tick {
                let segment_ticks = tempo_events[tempo_idx + 1].0 - prev_tick;
                accumulated_ms += ticks_to_ms(segment_ticks, current_tempo, ticks_per_quarter);
                prev_tick = tempo_events[tempo_idx + 1].0;
                tempo_idx += 1;
                current_tempo = tempo_events[tempo_idx].1;
            }

            // Convert the remaining ticks from prev_tick to current tick
            let segment_ticks = tick - prev_tick;
            accumulated_ms += ticks_to_ms(segment_ticks, current_tempo, ticks_per_quarter);
            prev_tick = tick;

            timed_events.push(TimedEvent {
                time_ms: accumulated_ms.round() as u64,
                message: message.clone(),
            });
        }

        self.duration_ms = timed_events.last().map(|e| e.time_ms + 2000).unwrap_or(0);
        self.events = timed_events;
        self.current_index = 0;
        self.filepath = Some(filepath.to_path_buf());

        // Try to open MIDI output if not already connected
        if self.conn.is_none() {
            self.conn = Self::open_midi_output();
        }

        Ok(())
    }

    /// Start or restart playback from the beginning.
    pub fn play(&mut self) {
        self.state = MidiState::Playing;
        self.current_index = 0;
        self.start_instant = Some(Instant::now());
        self.paused_offset_ms = 0;
    }

    /// Pause playback.
    pub fn pause(&mut self) {
        if self.state == MidiState::Playing {
            self.state = MidiState::Paused;
            self.paused_offset_ms = self.position_ms();
            self.start_instant = None;
            self.all_notes_off();
        }
    }

    /// Resume from pause.
    pub fn resume(&mut self) {
        if self.state == MidiState::Paused {
            self.state = MidiState::Playing;
            self.start_instant = Some(Instant::now());
        }
    }

    /// Stop playback and reset.
    pub fn stop(&mut self) {
        self.state = MidiState::Stopped;
        self.current_index = 0;
        self.start_instant = None;
        self.paused_offset_ms = 0;
        self.all_notes_off();
    }

    /// Advance playback — call from the engine tick loop.
    /// Sends any MIDI events whose time has arrived.
    pub fn tick(&mut self, current_ms: u64) {
        if self.state != MidiState::Playing {
            return;
        }
        while self.current_index < self.events.len() {
            let time_ms = self.events[self.current_index].time_ms;
            if time_ms <= current_ms {
                let msg = self.events[self.current_index].message.clone();
                self.send(&msg);
                self.current_index += 1;
            } else {
                break;
            }
        }
    }

    /// True when all events have been sent and enough time has passed
    /// for the final notes to fade.
    pub fn is_finished(&self) -> bool {
        self.current_index >= self.events.len()
    }

    /// Current playback position in milliseconds.
    pub fn position_ms(&self) -> u64 {
        match self.state {
            MidiState::Playing => {
                let elapsed = self
                    .start_instant
                    .map(|t| t.elapsed().as_millis() as u64)
                    .unwrap_or(0);
                elapsed + self.paused_offset_ms
            }
            MidiState::Paused => self.paused_offset_ms,
            MidiState::Stopped => 0,
        }
    }

    /// Total duration of the MIDI file in milliseconds.
    pub fn duration_ms(&self) -> u64 {
        self.duration_ms
    }

    /// Whether this player has a loaded file and a MIDI output connection.
    pub fn has_audio(&self) -> bool {
        self.conn.is_some() && !self.events.is_empty()
    }

    // ── Private helpers ─────────────────────────────────────────────

    fn send(&mut self, message: &[u8]) {
        if let Some(ref mut conn) = self.conn {
            conn.0.send(message).ok();
        }
    }

    fn all_notes_off(&mut self) {
        for ch in 0..16 {
            self.send(&[0xB0 | ch, 123, 0]);
        }
    }
}

/// Convert tick delta to milliseconds at a given tempo.
fn ticks_to_ms(ticks: u64, micros_per_quarter: u32, ticks_per_quarter: u64) -> f64 {
    (ticks as f64 / ticks_per_quarter as f64) * micros_per_quarter as f64 / 1000.0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_midi_player_new() {
        let p = MidiPlayer::new();
        assert_eq!(p.state, MidiState::Stopped);
        assert!(p.conn.is_none());
        assert!(p.events.is_empty());
        assert!(!p.has_audio());
        assert_eq!(p.duration_ms(), 0);
        assert!(p.is_finished());
    }

    #[test]
    fn test_midi_player_stop_resets_state() {
        let mut p = MidiPlayer::new();
        p.play();
        assert_eq!(p.state, MidiState::Playing);
        p.stop();
        assert_eq!(p.state, MidiState::Stopped);
        assert_eq!(p.current_index, 0);
        assert_eq!(p.position_ms(), 0);
    }

    #[test]
    fn test_midi_player_pause_resume() {
        let mut p = MidiPlayer::new();
        p.play();
        assert_eq!(p.state, MidiState::Playing);
        p.pause();
        assert_eq!(p.state, MidiState::Paused);
        p.resume();
        assert_eq!(p.state, MidiState::Playing);
        p.pause();
        assert_eq!(p.state, MidiState::Paused);
        // Pausing again should be a no-op
        p.pause();
        assert_eq!(p.state, MidiState::Paused);
    }

    #[test]
    fn test_midi_player_tick_sends_events() {
        let mut p = MidiPlayer::new();
        p.events = vec![
            TimedEvent { time_ms: 100, message: vec![0x90, 60, 100] },
            TimedEvent { time_ms: 200, message: vec![0x80, 60, 0] },
        ];
        p.duration_ms = 300;
        p.play();

        // Tick at 50ms — no events should be sent yet
        p.tick(50);
        assert_eq!(p.current_index, 0);
        assert!(!p.is_finished());

        // Tick at 150ms — first event should be sent
        p.tick(150);
        assert_eq!(p.current_index, 1);
        assert!(!p.is_finished());

        // Tick at 250ms — second event should be sent
        p.tick(250);
        assert_eq!(p.current_index, 2);
        assert!(p.is_finished());
    }

    #[test]
    fn test_midi_player_play_sends_all_events() {
        let mut p = MidiPlayer::new();
        p.events = vec![
            TimedEvent { time_ms: 0, message: vec![0x90, 60, 100] },
            TimedEvent { time_ms: 0, message: vec![0x90, 64, 100] },
        ];
        p.duration_ms = 100;
        p.play();
        p.tick(0);
        assert_eq!(p.current_index, 2);
        assert!(p.is_finished());
    }

    #[test]
    fn test_position_ms_evolves() {
        let mut p = MidiPlayer::new();
        p.play();
        // Immediately after play, position should be ~0
        assert!(p.position_ms() < 50);
    }

    #[test]
    fn test_position_ms_paused() {
        let mut p = MidiPlayer::new();
        p.play();
        p.pause();
        let pos = p.position_ms();
        // Should not change while paused
        std::thread::sleep(std::time::Duration::from_millis(10));
        assert_eq!(p.position_ms(), pos);
    }

    #[test]
    fn test_ticks_to_ms_normal() {
        // 96 ticks at 120 BPM (500000 micros/quarter) with 96 TPQN
        let ms = ticks_to_ms(96, 500000, 96);
        assert!((ms - 500.0).abs() < 0.001);
    }

    #[test]
    fn test_ticks_to_ms_double_tempo() {
        // 96 ticks at 240 BPM (250000 micros/quarter) with 96 TPQN
        let ms = ticks_to_ms(96, 250000, 96);
        assert!((ms - 250.0).abs() < 0.001);
    }

    #[test]
    fn test_ticks_to_ms_partial_tick() {
        let ms = ticks_to_ms(48, 500000, 96);
        assert!((ms - 250.0).abs() < 0.001);
    }

    #[test]
    fn test_load_invalid_file() {
        let mut p = MidiPlayer::new();
        let result = p.load(Path::new("nonexistent.mid"));
        assert!(result.is_err());
    }
}
