//! KAR/MIDI format constants and definitions.
//!
//! Mirrors `src/pykaraoke/players/kar.py`.

/// MIDI file header chunk ID ("MThd").
pub const MIDI_HEADER_ID: [u8; 4] = [0x4D, 0x54, 0x68, 0x64]; // "MThd"

/// MIDI track chunk ID ("MTrk").
pub const MIDI_TRACK_ID: [u8; 4] = [0x4D, 0x54, 0x72, 0x6B]; // "MTrk"

/// MIDI format 0 (single track).
pub const MIDI_FORMAT_0: u16 = 0;

/// MIDI format 1 (multiple tracks, synchronous).
pub const MIDI_FORMAT_1: u16 = 1;

/// MIDI format 2 (multiple tracks, asynchronous).
pub const MIDI_FORMAT_2: u16 = 2;

/// Meta event status byte.
pub const MIDI_META_EVENT: u8 = 0xFF;

/// End of track meta event type.
pub const MIDI_META_END_OF_TRACK: u8 = 0x2F;

/// Tempo meta event type (microseconds per quarter note).
pub const MIDI_META_TEMPO: u8 = 0x51;

/// Time signature meta event type.
pub const MIDI_META_TIME_SIGNATURE: u8 = 0x58;

/// Key signature meta event type.
pub const MIDI_META_KEY_SIGNATURE: u8 = 0x59;

/// Track name meta event type.
pub const MIDI_META_TRACK_NAME: u8 = 0x03;

/// Instrument name meta event type.
pub const MIDI_META_INSTRUMENT_NAME: u8 = 0x04;

/// Lyric meta event type (standard MIDI lyrics).
pub const MIDI_META_LYRIC: u8 = 0x05;

/// Marker meta event type.
pub const MIDI_META_MARKER: u8 = 0x06;

/// Copyright meta event type.
pub const MIDI_META_COPYRIGHT: u8 = 0x02;

/// Cue point meta event type.
pub const MIDI_META_CUE_POINT: u8 = 0x07;

/// Maximum value for a 14-bit MIDI value.
pub const MIDI_MAX_14BIT: u16 = 0x3FFF;

/// MIDI channel voice note off.
pub const MIDI_NOTE_OFF: u8 = 0x80;

/// MIDI channel voice note on.
pub const MIDI_NOTE_ON: u8 = 0x90;

/// MIDI channel voice polyphonic key pressure.
pub const MIDI_POLY_AFTERTOUCH: u8 = 0xA0;

/// MIDI channel voice control change.
pub const MIDI_CONTROL_CHANGE: u8 = 0xB0;

/// MIDI channel voice program change.
pub const MIDI_PROGRAM_CHANGE: u8 = 0xC0;

/// MIDI channel voice channel aftertouch.
pub const MIDI_CHANNEL_AFTERTOUCH: u8 = 0xD0;

/// MIDI channel voice pitch wheel.
pub const MIDI_PITCH_WHEEL: u8 = 0xE0;

/// Default tempo (500,000 microseconds per quarter = 120 BPM).
pub const MIDI_DEFAULT_TEMPO: u32 = 500_000;

/// Number of MIDI channels (16).
pub const MIDI_NUM_CHANNELS: usize = 16;

/// A parsed lyric syllable with timing.
#[derive(Debug, Clone)]
pub struct LyricSyllable {
    pub text: String,
    pub start_ms: u64,
    pub duration_ms: u64,
}

/// Karaoke lyric types.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LyricType {
    Normal = 0,
    Info = 1,
    Title = 2,
}

/// A parsed MIDI event.
#[derive(Debug, Clone)]
pub struct MidiEvent {
    pub delta_time: u64,
    pub event_type: u8,
    pub data: Vec<u8>,
}

/// A parsed MIDI track.
#[derive(Debug, Clone)]
pub struct MidiTrack {
    pub events: Vec<MidiEvent>,
    pub name: String,
}

/// A parsed MIDI file.
#[derive(Debug, Clone)]
pub struct MidiFile {
    pub format: u16,
    pub num_tracks: u16,
    pub ticks_per_quarter: u16,
    pub tracks: Vec<MidiTrack>,
    pub lyrics: Vec<LyricSyllable>,
}

/// Lyric display constants.
pub const VIEW_PERCENT: u8 = 33; // Keep cursor in top 33% of screen
pub const FONT_SIZE: u32 = 40; // Default font size at 480px
pub const PARAGRAPH_LEAD_TIME: u64 = 5000; // ms

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_midi_header_id() {
        assert_eq!(MIDI_HEADER_ID, [0x4D, 0x54, 0x68, 0x64]);
    }

    #[test]
    fn test_midi_track_id() {
        assert_eq!(MIDI_TRACK_ID, [0x4D, 0x54, 0x72, 0x6B]);
    }

    #[test]
    fn test_midi_formats() {
        assert_eq!(MIDI_FORMAT_0, 0);
        assert_eq!(MIDI_FORMAT_1, 1);
        assert_eq!(MIDI_FORMAT_2, 2);
    }

    #[test]
    fn test_midi_meta_event() {
        assert_eq!(MIDI_META_EVENT, 0xFF);
    }

    #[test]
    fn test_midi_meta_types() {
        assert_eq!(MIDI_META_END_OF_TRACK, 0x2F);
        assert_eq!(MIDI_META_TEMPO, 0x51);
        assert_eq!(MIDI_META_TIME_SIGNATURE, 0x58);
        assert_eq!(MIDI_META_KEY_SIGNATURE, 0x59);
        assert_eq!(MIDI_META_TRACK_NAME, 0x03);
        assert_eq!(MIDI_META_INSTRUMENT_NAME, 0x04);
        assert_eq!(MIDI_META_LYRIC, 0x05);
        assert_eq!(MIDI_META_MARKER, 0x06);
    }

    #[test]
    fn test_default_tempo() {
        assert_eq!(MIDI_DEFAULT_TEMPO, 500_000);
    }

    #[test]
    fn test_channel_voice_events() {
        assert_eq!(MIDI_NOTE_OFF & 0xF0, 0x80);
        assert_eq!(MIDI_NOTE_ON & 0xF0, 0x90);
        assert_eq!(MIDI_POLY_AFTERTOUCH & 0xF0, 0xA0);
        assert_eq!(MIDI_CONTROL_CHANGE & 0xF0, 0xB0);
        assert_eq!(MIDI_PROGRAM_CHANGE & 0xF0, 0xC0);
        assert_eq!(MIDI_CHANNEL_AFTERTOUCH & 0xF0, 0xD0);
        assert_eq!(MIDI_PITCH_WHEEL & 0xF0, 0xE0);
    }

    #[test]
    fn test_lyric_constants() {
        assert_eq!(VIEW_PERCENT, 33);
        assert_eq!(FONT_SIZE, 40);
        assert_eq!(PARAGRAPH_LEAD_TIME, 5000);
    }
}
