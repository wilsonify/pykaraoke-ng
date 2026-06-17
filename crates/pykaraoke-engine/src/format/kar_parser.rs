//! KAR/MIDI file parser — pure Rust implementation.
//!
//! Port of `src/pykaraoke/players/kar.py` MIDI parsing, lyrics extraction
//! and timing conversion.
//!
//! # Pipeline
//! 1. `midi_parse_data(raw_bytes, encoding)` → `ParsedMidiFile`
//! 2. ParsedMidiFile contains: header, tracks, tempo map, lyrics, note bounds
//! 3. `Lyrics::to_lyrics_view()` → `LyricsView` for frontend consumption

use crate::format::kar::*;
use crate::views::{LyricLine, LyricsView};

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug)]
pub enum MidiParseError {
    NoHeader,
    InvalidHeader,
    Truncated,
    NoLyrics,
}

impl std::fmt::Display for MidiParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MidiParseError::NoHeader => write!(f, "No MIDI header chunk found"),
            MidiParseError::InvalidHeader => write!(f, "Invalid MIDI header"),
            MidiParseError::Truncated => write!(f, "Truncated MIDI file"),
            MidiParseError::NoLyrics => write!(f, "No lyrics found in MIDI file"),
        }
    }
}

impl std::error::Error for MidiParseError {}

// ---------------------------------------------------------------------------
// VLQ (Variable-Length Quantity)
// ---------------------------------------------------------------------------

/// Reads a MIDI variable-length quantity from `data` starting at `offset`.
/// Returns `(value, bytes_consumed)` or `None` if truncated.
pub fn read_var_length(data: &[u8], offset: usize) -> Option<(u64, usize)> {
    let mut value: u64 = 0;
    let mut pos = offset;
    let mut shift: u32 = 0;
    while shift <= 42 {
        let byte = *data.get(pos)?;
        pos += 1;
        value = (value << 7) | (byte & 0x7F) as u64;
        if byte & 0x80 == 0 {
            return Some((value, pos - offset));
        }
        shift += 7;
    }
    None
}

fn read_u16_be(data: &[u8], offset: usize) -> Option<u16> {
    Some(u16::from_be_bytes([*data.get(offset)?, *data.get(offset + 1)?]))
}

fn read_u32_be(data: &[u8], offset: usize) -> Option<u32> {
    Some(u32::from_be_bytes([
        *data.get(offset)?,
        *data.get(offset + 1)?,
        *data.get(offset + 2)?,
        *data.get(offset + 3)?,
    ]))
}

// ---------------------------------------------------------------------------
// Tempo change
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct TempoChange {
    pub click: u64,
    pub microseconds_per_quarter: u32,
}

// ---------------------------------------------------------------------------
// Track descriptor (parsing state per track)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct TrackDesc {
    pub track_num: usize,
    pub total_clicks: u64,
    pub first_note_click: Option<u64>,
    pub last_note_click: Option<u64>,
    pub lyrics_track: bool,
    pub text_events: Lyrics,
    pub lyric_events: Lyrics,
    pub name: String,
}

impl TrackDesc {
    fn new(track_num: usize) -> Self {
        Self {
            track_num,
            total_clicks: 0,
            first_note_click: None,
            last_note_click: None,
            lyrics_track: false,
            text_events: Lyrics::new(),
            lyric_events: Lyrics::new(),
            name: String::new(),
        }
    }
}

// ---------------------------------------------------------------------------
// LyricSyllable / Lyrics (mirror of Python Lyrics class)
// ---------------------------------------------------------------------------

/// A single lyric syllable with click timing, text, line number, and type.
#[derive(Debug, Clone)]
pub struct LyricSyllable {
    pub click: u64,
    pub ms: u64,
    pub text: String,
    pub line: usize,
    pub typ: LyricType,
}

/// A collection of lyric syllables.
#[derive(Debug, Clone)]
pub struct Lyrics {
    pub list: Vec<LyricSyllable>,
    pub line: usize,
}

impl Lyrics {
    pub fn new() -> Self {
        Self {
            list: Vec::new(),
            line: 0,
        }
    }

    pub fn has_any(&self) -> bool {
        !self.list.is_empty()
    }

    /// Record a MIDI 0x01 text event.
    pub fn record_text(&mut self, click: u64, text: &str) {
        let text = text.replace('\x00', "").replace('\r', "");
        if text.is_empty() {
            return;
        }

        let chars: Vec<char> = text.chars().collect();

        if chars[0] == '@' {
            if chars.len() < 2 {
                return;
            }
            let text_type = match chars[1] {
                'T' => LyricType::Title,
                'I' => LyricType::Info,
                _ => return,
            };
            for line in text[2..].split('\n') {
                let line = line.trim();
                if line.is_empty() {
                    continue;
                }
                self.line += 1;
                self.list.push(LyricSyllable {
                    click,
                    ms: 0,
                    text: line.to_string(),
                    line: self.line,
                    typ: text_type,
                });
            }
            return;
        }

        let mut remaining = text.as_str();
        if remaining.starts_with('\\') {
            self.line += 2;
            remaining = &remaining[1..];
        } else if remaining.starts_with('/') {
            self.line += 1;
            remaining = &remaining[1..];
        }

        if !remaining.is_empty() {
            let lines: Vec<&str> = remaining.split('\n').collect();
            for (i, line_text) in lines.iter().enumerate() {
                if i > 0 {
                    self.line += 1;
                }
                self.list.push(LyricSyllable {
                    click,
                    ms: 0,
                    text: line_text.to_string(),
                    line: self.line,
                    typ: LyricType::Normal,
                });
            }
        }
    }

    /// Record a MIDI 0x05 lyric event.
    pub fn record_lyric(&mut self, click: u64, text: &str) {
        let text = text.replace('\x00', "");
        if text == "\n" {
            self.line += 2;
            return;
        }
        if text == "\r" || text == "\r\n" {
            self.line += 1;
            return;
        }
        if text.is_empty() {
            return;
        }

        let mut processed = text.replace('\r', "");
        let chars: Vec<char> = processed.chars().collect();

        if chars[0] == '\\' {
            self.line += 2;
            processed = chars[1..].iter().collect();
        } else if chars[0] == '/' {
            self.line += 1;
            processed = chars[1..].iter().collect();
        }

        let lines: Vec<&str> = processed.split('\n').collect();
        for (i, line_text) in lines.iter().enumerate() {
            if i > 0 {
                self.line += 1;
            }
            self.list.push(LyricSyllable {
                click,
                ms: 0,
                text: line_text.to_string(),
                line: self.line,
                typ: LyricType::Normal,
            });
        }
    }

    /// Convert click timing to milliseconds using the tempo map.
    pub fn compute_timing(&mut self, tempo: &[TempoChange], ticks_per_quarter: u16) {
        let mut ts = MidiTimestamp::new(tempo, ticks_per_quarter);
        for syllable in &mut self.list {
            ts.advance_to_click(syllable.click);
            syllable.ms = ts.ms as u64;
        }
    }

    /// Check for missing spaces between words and repair if needed.
    pub fn analyze_spaces(&mut self) {
        let groups = self.group_indices();
        let (total_syls, total_gaps) = Self::count_gaps_indices(&self.list, &groups);
        if total_syls > 0 && (total_gaps as f64) / (total_syls as f64) < 0.1 {
            for group in &groups {
                for i in group.iter().take(group.len().saturating_sub(1)) {
                    if !self.list[*i].text.ends_with('-') {
                        self.list[*i].text.push(' ');
                    } else {
                        self.list[*i].text.pop();
                    }
                }
            }
        }
    }

    /// Group syllable indices by line number.
    fn group_indices(&self) -> Vec<Vec<usize>> {
        let mut groups: Vec<Vec<usize>> = Vec::new();
        let mut current: Vec<usize> = Vec::new();
        let mut last_line = None;
        for (i, syl) in self.list.iter().enumerate() {
            if last_line.map_or(false, |l| l != syl.line) {
                if !current.is_empty() {
                    groups.push(std::mem::take(&mut current));
                }
            }
            last_line = Some(syl.line);
            current.push(i);
        }
        if !current.is_empty() {
            groups.push(current);
        }
        groups
    }

    fn count_gaps_indices(list: &[LyricSyllable], groups: &[Vec<usize>]) -> (usize, usize) {
        let mut total_syls = 0;
        let mut total_gaps = 0;
        for group in groups {
            let n = group.len().saturating_sub(1);
            for window in group.windows(2) {
                let i = window[0];
                let j = window[1];
                if list[i].text.trim_end() != list[i].text
                    || list[j].text.trim_start() != list[j].text
                {
                    total_gaps += 1;
                }
            }
            total_syls += n;
        }
        (total_syls, total_gaps)
    }

    /// Build a `LyricsView` from the computed lyrics at a given `current_ms`.
    pub fn to_lyrics_view(&self, current_ms: u64) -> LyricsView {
        let total = self.list.len();
        if total == 0 {
            return LyricsView {
                current_line: String::new(),
                next_line: String::new(),
                current_line_progress: 0.0,
                lines: Vec::new(),
            };
        }

        let mut current_idx = 0;
        for (i, syl) in self.list.iter().enumerate() {
            if syl.ms > current_ms {
                break;
            }
            current_idx = i;
        }

        let current_line_num = self.list[current_idx].line;
        let mut current_line_text = String::new();
        let mut next_line_text = String::new();
        let mut found_next = false;

        let mut current_line_start_ms = 0u64;
        let mut current_line_end_ms = current_ms + 1000;

        for syl in &self.list {
            if syl.line == current_line_num {
                if !current_line_text.is_empty()
                    && !syl.text.starts_with(' ')
                    && !current_line_text.ends_with(' ')
                {
                    current_line_text.push(' ');
                }
                current_line_text.push_str(&syl.text);
            }
        }

        // Find start/end times for the current line.
        for syl in &self.list {
            if syl.line == current_line_num {
                if syl.ms <= current_ms {
                    current_line_start_ms = syl.ms;
                }
                if syl.ms > current_ms && current_line_end_ms == current_ms + 1000 {
                    current_line_end_ms = syl.ms;
                }
            }
        }

        // Find next line text.
        for syl in &self.list {
            if syl.line > current_line_num && !found_next {
                next_line_text = syl.text.clone();
                found_next = true;
            }
        }

        let line_duration = current_line_end_ms.saturating_sub(current_line_start_ms).max(1);
        let progress = if current_ms >= current_line_start_ms {
            ((current_ms - current_line_start_ms) as f64 / line_duration as f64).clamp(0.0, 1.0)
        } else {
            0.0
        };

        let view_lines: Vec<LyricLine> = self
            .list
            .iter()
            .map(|s| LyricLine {
                text: s.text.clone(),
                start_ms: s.ms,
                duration_ms: 0,
            })
            .collect();

        LyricsView {
            current_line: current_line_text,
            next_line: next_line_text,
            current_line_progress: progress,
            lines: view_lines,
        }
    }
}

// ---------------------------------------------------------------------------
// MidiTimestamp (click → milliseconds converter)
// ---------------------------------------------------------------------------

pub struct MidiTimestamp {
    ticks_per_quarter: u16,
    tempo: Vec<TempoChange>,
    ms: f64,
    click: u64,
    i: usize,
}

impl MidiTimestamp {
    pub fn new(tempo: &[TempoChange], ticks_per_quarter: u16) -> Self {
        Self {
            ticks_per_quarter,
            tempo: tempo.to_vec(),
            ms: 0.0,
            click: 0,
            i: 0,
        }
    }

    pub fn advance_to_click(&mut self, click: u64) {
        if click <= self.click {
            return;
        }

        // Advance i to the entry that applies at self.click.
        while self.i + 1 < self.tempo.len() && self.tempo[self.i + 1].click <= self.click {
            self.i += 1;
        }

        let mut remaining = click - self.click;
        while remaining > 0 {
            let current_tempo = self.tempo[self.i].microseconds_per_quarter;

            let next_change = if self.i + 1 < self.tempo.len() {
                self.tempo[self.i + 1].click
            } else {
                u64::MAX
            };

            let segment_end = next_change.min(click);
            let segment_clicks = segment_end - self.click;

            if segment_clicks > 0 {
                self.ms += self.time_for_clicks(segment_clicks, current_tempo);
                self.click += segment_clicks;
                remaining -= segment_clicks;
            }

            if self.click >= next_change && self.i + 1 < self.tempo.len() {
                self.i += 1;
            } else {
                break;
            }
        }
    }

    fn time_for_clicks(&self, clicks: u64, tempo_micros: u32) -> f64 {
        let micros = (clicks as f64 / self.ticks_per_quarter as f64) * tempo_micros as f64;
        micros / 1000.0
    }
}

// ---------------------------------------------------------------------------
// ParsedMidiFile — the result of a full MIDI parse
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct ParsedMidiFile {
    pub format: u16,
    pub num_tracks: u16,
    pub ticks_per_quarter: u16,
    pub tracks: Vec<MidiTrack>,
    pub lyrics: Lyrics,
    pub tempo: Vec<TempoChange>,
    pub earliest_note_ms: f64,
    pub last_note_ms: f64,
}

// ---------------------------------------------------------------------------
// Top-level parse function
// ---------------------------------------------------------------------------

/// Parse a MIDI/KAR file from raw bytes.
///
/// `encoding` is the text encoding for lyric data (e.g. "cp1252", "latin-1").
/// If empty, defaults to "latin-1".
pub fn midi_parse_data(data: &[u8], encoding: &str) -> Result<ParsedMidiFile, MidiParseError> {
    // --- Parse header ---
    let chunk_type = data.get(0..4).ok_or(MidiParseError::NoHeader)?;
    if chunk_type != b"MThd" {
        return Err(MidiParseError::NoHeader);
    }
    let _header_len = read_u32_be(data, 4).ok_or(MidiParseError::Truncated)?;
    let format = read_u16_be(data, 8).ok_or(MidiParseError::Truncated)?;
    let num_tracks = read_u16_be(data, 10).ok_or(MidiParseError::Truncated)?;
    let division = read_u16_be(data, 12).ok_or(MidiParseError::Truncated)?;

    let ticks_per_quarter = if division & 0x8000 != 0 {
        division & 0x00FF
    } else {
        division & 0x7FFF
    };

    // --- Parse tracks ---
    let mut pos: usize = 14;
    let mut track_descs: Vec<TrackDesc> = Vec::new();
    let mut global_tempo: Vec<TempoChange> = vec![TempoChange {
        click: 0,
        microseconds_per_quarter: MIDI_DEFAULT_TEMPO,
    }];

    for _track_num in 0..num_tracks as usize {
        let chunk_id = data.get(pos..pos + 4).ok_or(MidiParseError::Truncated)?;
        if chunk_id != b"MTrk" {
            let chunk_len = read_u32_be(data, pos + 4).ok_or(MidiParseError::Truncated)? as usize;
            pos += 8 + chunk_len;
            continue;
        }
        let track_len = read_u32_be(data, pos + 4).ok_or(MidiParseError::Truncated)? as usize;
        pos += 8;

        let track_data = data
            .get(pos..pos + track_len)
            .ok_or(MidiParseError::Truncated)?;
        let track_desc = parse_track(track_data, _track_num, encoding, &mut global_tempo);
        track_descs.push(track_desc);
        pos += track_len;
    }

    // --- Select best lyrics ---
    let lyrics = select_best_lyrics(&track_descs);

    // --- Compute timing ---
    let mut final_lyrics = lyrics.clone();
    if final_lyrics.has_any() {
        final_lyrics.compute_timing(&global_tempo, ticks_per_quarter);
        final_lyrics.analyze_spaces();
    }

    // --- Compute note bounds ---
    let (earliest_note_ms, last_note_ms) =
        compute_note_bounds(&track_descs, &global_tempo, ticks_per_quarter);

    // --- Build tracks list for output ---
    let tracks: Vec<MidiTrack> = track_descs
        .iter()
        .map(|td| MidiTrack {
            events: Vec::new(),
            name: td.name.clone(),
        })
        .collect();

    Ok(ParsedMidiFile {
        format,
        num_tracks,
        ticks_per_quarter,
        tracks,
        lyrics: final_lyrics,
        tempo: global_tempo,
        earliest_note_ms,
        last_note_ms,
    })
}

// ---------------------------------------------------------------------------
// Track parser
// ---------------------------------------------------------------------------

fn parse_track(
    data: &[u8],
    track_num: usize,
    encoding: &str,
    global_tempo: &mut Vec<TempoChange>,
) -> TrackDesc {
    let mut track = TrackDesc::new(track_num);
    let mut pos = 0;
    let mut running_status: u8 = 0;

    while pos < data.len() {
        if !process_event(data, &mut pos, &mut track, encoding, global_tempo, &mut running_status) {
            break;
        }
    }

    track
}

// ---------------------------------------------------------------------------
// Event processor
// ---------------------------------------------------------------------------

fn process_event(
    data: &[u8],
    pos: &mut usize,
    track: &mut TrackDesc,
    encoding: &str,
    global_tempo: &mut Vec<TempoChange>,
    running_status: &mut u8,
) -> bool {
    let (delta, consumed) = match read_var_length(data, *pos) {
        Some(v) => v,
        None => return false,
    };
    *pos += consumed;
    track.total_clicks += delta;

    let Some(&status) = data.get(*pos) else {
        return false;
    };
    *pos += 1;

    let event_type: u8;
    if status & 0x80 != 0 {
        event_type = status;
        if event_type & 0xF0 != 0xF0 {
            *running_status = event_type;
        }
    } else {
        event_type = *running_status;
        *pos -= 1;
    }

    match event_type {
        0xFF => {
            process_meta_event(data, pos, track, encoding, global_tempo);
        }
        0xF0 | 0xF7 => {
            if let Some((_len, consumed)) = read_var_length(data, *pos) {
                *pos += consumed + _len as usize;
            }
        }
        _ => {
            process_channel_event(data, pos, track, event_type);
        }
    }

    true
}

// ---------------------------------------------------------------------------
// Meta event handlers
// ---------------------------------------------------------------------------

fn process_meta_event(
    data: &[u8],
    pos: &mut usize,
    track: &mut TrackDesc,
    encoding: &str,
    global_tempo: &mut Vec<TempoChange>,
) {
    let Some(&meta_type) = data.get(*pos) else { return };
    *pos += 1;

    match meta_type {
        0x00 => *pos += 2,
        0x01 => handle_text_event(data, pos, track, encoding),
        0x02 => {
            read_and_discard_var(data, pos);
        }
        0x03 => handle_track_name(data, pos, track, encoding),
        0x04 => {
            read_and_discard_var(data, pos);
        }
        0x05 => handle_lyric_event(data, pos, track, encoding),
        0x06 | 0x07 | 0x08 | 0x09 => {
            read_and_discard_var(data, pos);
        }
        0x20 | 0x21 => *pos += 2,
        0x2F => {
            let _ = data.get(*pos);
            *pos += 1;
        }
        0x51 => handle_tempo(data, pos, track, global_tempo),
        0x54 => *pos += 6,
        0x58 => {
            read_and_discard_var(data, pos);
        }
        0x59 => {
            read_and_discard_var(data, pos);
        }
        0x7F => {
            read_and_discard_var(data, pos);
        }
        _ => {
            read_and_discard_var(data, pos);
        }
    }
}

fn handle_text_event(data: &[u8], pos: &mut usize, track: &mut TrackDesc, _encoding: &str) {
    let Some((len, consumed)) = read_var_length(data, *pos) else { return };
    *pos += consumed;
    if len > 1000 {
        *pos += len as usize;
        return;
    }
    let Some(text_bytes) = data.get(*pos..*pos + len as usize) else {
        *pos += len as usize;
        return;
    };
    *pos += len as usize;

    let text = decode_latin1_lossy(text_bytes);
    if is_lyric_text(&text) {
        track.text_events.record_text(track.total_clicks, &text);
    }
}

fn handle_track_name(data: &[u8], pos: &mut usize, track: &mut TrackDesc, _encoding: &str) {
    let Some((len, consumed)) = read_var_length(data, *pos) else { return };
    *pos += consumed;
    let Some(text_bytes) = data.get(*pos..*pos + len as usize) else {
        *pos += len as usize;
        return;
    };
    *pos += len as usize;
    let title = decode_latin1_lossy(text_bytes);
    track.name = title.clone();
    if title.trim() == "Words" {
        track.lyrics_track = true;
    }
}

fn handle_lyric_event(data: &[u8], pos: &mut usize, track: &mut TrackDesc, _encoding: &str) {
    let Some((len, consumed)) = read_var_length(data, *pos) else { return };
    *pos += consumed;
    let Some(text_bytes) = data.get(*pos..*pos + len as usize) else {
        *pos += len as usize;
        return;
    };
    *pos += len as usize;

    let text = decode_latin1_lossy(text_bytes);
    if is_lyric_text(&text) {
        track.lyric_events.record_lyric(track.total_clicks, &text);
    }
}

fn handle_tempo(data: &[u8], pos: &mut usize, track: &mut TrackDesc, global_tempo: &mut Vec<TempoChange>) {
    let Some(&len_byte) = data.get(*pos) else { return };
    *pos += 1;
    if len_byte != 3 {
        *pos += len_byte as usize;
        return;
    }
    let a = *data.get(*pos).unwrap_or(&0) as u32;
    let b = *data.get(*pos + 1).unwrap_or(&0) as u32;
    let c = *data.get(*pos + 2).unwrap_or(&0) as u32;
    *pos += 3;
    let tempo = (a << 16) | (b << 8) | c;
    global_tempo.push(TempoChange {
        click: track.total_clicks,
        microseconds_per_quarter: tempo,
    });
}

// ---------------------------------------------------------------------------
// Channel event handler
// ---------------------------------------------------------------------------

fn process_channel_event(data: &[u8], pos: &mut usize, track: &mut TrackDesc, event_type: u8) {
    let high_nibble = event_type & 0xF0;

    match high_nibble {
        0x80 => {
            *pos += 2;
            track.last_note_click = Some(track.total_clicks);
        }
        0x90 => {
            *pos += 2;
            if track.first_note_click.is_none() {
                track.first_note_click = Some(track.total_clicks);
            }
            track.last_note_click = Some(track.total_clicks);
        }
        0xA0 | 0xB0 | 0xE0 => *pos += 2,
        0xC0 | 0xD0 => *pos += 1,
        _ => {
            read_and_discard_var(data, pos);
        }
    }
}

// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

fn read_and_discard_var(data: &[u8], pos: &mut usize) {
    if let Some((len, consumed)) = read_var_length(data, *pos) {
        *pos += consumed + len as usize;
    }
}

/// Decode bytes as Latin-1 (ISO 8859-1), replacing invalid bytes.
fn decode_latin1_lossy(bytes: &[u8]) -> String {
    bytes.iter().map(|&b| b as char).collect()
}

fn is_lyric_text(text: &str) -> bool {
    !text.contains(" SYX")
        && !text.contains("Track-")
        && !text.contains("%-")
        && !text.contains("%+")
}

fn select_best_lyrics(tracks: &[TrackDesc]) -> Lyrics {
    let mut best_sort_key = (false, 0usize);
    let mut best_lyrics: Option<Lyrics> = None;

    for track in tracks {
        if let Some(lyrics) = choose_lyrics_from_track(track) {
            let sort_key = (track.lyrics_track, lyrics.list.len());
            if sort_key > best_sort_key {
                best_sort_key = sort_key;
                best_lyrics = Some(lyrics);
            }
        }
    }

    best_lyrics.unwrap_or_else(Lyrics::new)
}

fn choose_lyrics_from_track(track: &TrackDesc) -> Option<Lyrics> {
    let has_text = track.text_events.has_any();
    let has_lyric = track.lyric_events.has_any();

    if has_text && has_lyric {
        if track.lyric_events.list.len() > track.text_events.list.len() {
            return Some(track.lyric_events.clone());
        }
        return Some(track.text_events.clone());
    }
    if has_text {
        return Some(track.text_events.clone());
    }
    if has_lyric {
        return Some(track.lyric_events.clone());
    }
    None
}

fn compute_note_bounds(
    tracks: &[TrackDesc],
    tempo: &[TempoChange],
    ticks_per_quarter: u16,
) -> (f64, f64) {
    let mut earliest: Option<f64> = None;
    let mut latest: Option<f64> = None;

    for track in tracks {
        if let Some(click) = track.first_note_click {
            let mut ts = MidiTimestamp::new(tempo, ticks_per_quarter);
            ts.advance_to_click(click);
            if earliest.map_or(true, |e| ts.ms < e) {
                earliest = Some(ts.ms);
            }
        }
        if let Some(click) = track.last_note_click {
            let mut ts = MidiTimestamp::new(tempo, ticks_per_quarter);
            ts.advance_to_click(click);
            if latest.map_or(true, |l| ts.ms > l) {
                latest = Some(ts.ms);
            }
        }
    }

    (earliest.unwrap_or(0.0), latest.unwrap_or(0.0))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_simple_midi(tracks_data: &[&[u8]]) -> Vec<u8> {
        let mut data = Vec::new();
        data.extend_from_slice(b"MThd");
        data.extend_from_slice(&6u32.to_be_bytes());
        data.extend_from_slice(&1u16.to_be_bytes());
        data.extend_from_slice(&(tracks_data.len() as u16).to_be_bytes());
        data.extend_from_slice(&96u16.to_be_bytes());

        for track_bytes in tracks_data {
            data.extend_from_slice(b"MTrk");
            data.extend_from_slice(&(track_bytes.len() as u32).to_be_bytes());
            data.extend_from_slice(track_bytes);
        }
        data
    }

    fn build_track(events: &[(u64, u8, Vec<u8>)]) -> Vec<u8> {
        let mut track = Vec::new();
        for (delta, status, event_data) in events {
            write_var_length(&mut track, *delta);
            track.push(*status);
            track.extend_from_slice(event_data);
        }
        track
    }

    fn write_var_length(out: &mut Vec<u8>, mut value: u64) {
        let mut bytes = Vec::new();
        bytes.push((value & 0x7F) as u8);
        value >>= 7;
        while value > 0 {
            bytes.push((value & 0x7F) as u8 | 0x80);
            value >>= 7;
        }
        bytes.reverse();
        out.extend_from_slice(&bytes);
    }

    fn meta_event(delta: u64, meta_type: u8, data: &[u8]) -> (u64, u8, Vec<u8>) {
        let mut ed = Vec::new();
        write_var_length(&mut ed, data.len() as u64);
        ed.extend_from_slice(data);
        (delta, 0xFF, {
            let mut v = vec![meta_type];
            v.extend_from_slice(&ed);
            v
        })
    }

    fn note_on(delta: u64, channel: u8, note: u8, velocity: u8) -> (u64, u8, Vec<u8>) {
        (delta, 0x90 | channel, vec![note, velocity])
    }

    fn note_off(delta: u64, channel: u8, note: u8, velocity: u8) -> (u64, u8, Vec<u8>) {
        (delta, 0x80 | channel, vec![note, velocity])
    }

    fn end_track() -> (u64, u8, Vec<u8>) {
        meta_event(0, 0x2F, &[])
    }

    fn make_text_event(text: &[u8]) -> (u64, u8, Vec<u8>) {
        meta_event(0, 0x01, text)
    }

    // ------------------------------------------------------------------
    // Tests
    // ------------------------------------------------------------------

    #[test]
    fn test_var_length_simple() {
        let (val, consumed) = read_var_length(&[0x7F], 0).unwrap();
        assert_eq!(val, 0x7F);
        assert_eq!(consumed, 1);
    }

    #[test]
    fn test_var_length_two_bytes() {
        let (val, consumed) = read_var_length(&[0x81, 0x7F], 0).unwrap();
        assert_eq!(val, 255);
        assert_eq!(consumed, 2);
    }

    #[test]
    fn test_var_length_zero() {
        let (val, consumed) = read_var_length(&[0x00], 0).unwrap();
        assert_eq!(val, 0);
        assert_eq!(consumed, 1);
    }

    #[test]
    fn test_var_length_truncated() {
        assert!(read_var_length(&[], 0).is_none());
    }

    #[test]
    fn test_parse_midi_header() {
        let data = make_simple_midi(&[]);
        let mf = midi_parse_data(&data, "").unwrap();
        assert_eq!(mf.format, 1);
        assert_eq!(mf.ticks_per_quarter, 96);
    }

    #[test]
    fn test_parse_empty_file() {
        assert!(midi_parse_data(b"MThd", "").is_err());
    }

    #[test]
    fn test_parse_no_header() {
        assert!(matches!(midi_parse_data(b"RIFF....", ""), Err(MidiParseError::NoHeader)));
    }

    #[test]
    fn test_parse_track_with_tempo() {
        let tempo_data = [0x07, 0xA1, 0x20];
        let events = vec![
            meta_event(0, 0x51, &tempo_data),
            end_track(),
        ];
        let track = build_track(&events);
        let data = make_simple_midi(&[&track]);
        let mf = midi_parse_data(&data, "").unwrap();
        assert!(mf.tempo.len() >= 2);
        assert_eq!(mf.tempo.last().unwrap().microseconds_per_quarter, 500000);
    }

    #[test]
    fn test_parse_track_with_text_event() {
        let text = b"HELLO";
        let events = vec![make_text_event(text), end_track()];
        let track = build_track(&events);
        let data = make_simple_midi(&[&track]);
        let mf = midi_parse_data(&data, "").unwrap();
        assert!(mf.lyrics.has_any());
        assert_eq!(mf.lyrics.list[0].text, "HELLO");
    }

    #[test]
    fn test_parse_track_with_lyric_event() {
        let text = b"SING";
        let events = vec![meta_event(0, 0x05, text), end_track()];
        let track = build_track(&events);
        let data = make_simple_midi(&[&track]);
        let mf = midi_parse_data(&data, "").unwrap();
        assert_eq!(mf.lyrics.list[0].text, "SING");
    }

    #[test]
    fn test_parse_track_with_notes() {
        let events = vec![
            note_on(10, 0, 60, 100),
            note_off(96, 0, 60, 0),
            end_track(),
        ];
        let track = build_track(&events);
        let data = make_simple_midi(&[&track]);
        let mf = midi_parse_data(&data, "").unwrap();
        assert!(mf.last_note_ms > 0.0);
    }

    #[test]
    fn test_select_best_lyrics_prefers_words_track() {
        let make_track_data = |label: &str, lyrics: &[&str]| -> Vec<u8> {
            let mut events = Vec::new();
            if !label.is_empty() {
                events.push(meta_event(0, 0x03, label.as_bytes()));
            }
            for (i, l) in lyrics.iter().enumerate() {
                events.push(meta_event((i * 96) as u64, 0x01, l.as_bytes()));
            }
            events.push(end_track());
            build_track(&events)
        };

        let t1 = make_track_data("Words", &["SYL1", "SYL2"]);
        let t2 = make_track_data("", &["A", "B", "C"]);
        let data = make_simple_midi(&[&t1, &t2]);
        let mf = midi_parse_data(&data, "").unwrap();
        // Words track wins despite fewer syllables
        assert_eq!(mf.lyrics.list.len(), 2);
    }

    #[test]
    fn test_select_best_lyrics_most_syllables() {
        let make_track_data = |lyrics: &[&str]| -> Vec<u8> {
            let mut events = Vec::new();
            for (i, l) in lyrics.iter().enumerate() {
                events.push(meta_event((i * 96) as u64, 0x01, l.as_bytes()));
            }
            events.push(end_track());
            build_track(&events)
        };

        let t1 = make_track_data(&["ONE", "TWO"]);
        let t2 = make_track_data(&["A", "B", "C", "D"]);
        let data = make_simple_midi(&[&t1, &t2]);
        let mf = midi_parse_data(&data, "").unwrap();
        assert_eq!(mf.lyrics.list.len(), 4);
    }

    #[test]
    fn test_lyrics_compute_timing() {
        let mut lyrics = Lyrics::new();
        lyrics.record_text(96, "ONE");
        lyrics.record_text(192, "TWO");

        let tempo = vec![TempoChange { click: 0, microseconds_per_quarter: 500000 }];
        lyrics.compute_timing(&tempo, 96);
        assert_eq!(lyrics.list[0].ms, 500);
        assert_eq!(lyrics.list[1].ms, 1000);
    }

    #[test]
    fn test_midi_timestamp() {
        let tempo = vec![
            TempoChange { click: 0, microseconds_per_quarter: 500000 },
            TempoChange { click: 96, microseconds_per_quarter: 250000 },
        ];
        let mut ts = MidiTimestamp::new(&tempo, 96);
        ts.advance_to_click(192);
        // 96/96 * 500000/1000 = 500ms, + 96/96 * 250000/1000 = 250ms = 750ms
        assert!((ts.ms - 750.0).abs() < 0.001);
    }

    #[test]
    fn test_lyrics_record_text_basic() {
        let mut lyrics = Lyrics::new();
        lyrics.record_text(100, "Hello");
        assert_eq!(lyrics.list.len(), 1);
        assert_eq!(lyrics.list[0].text, "Hello");
        assert_eq!(lyrics.list[0].click, 100);
    }

    #[test]
    fn test_lyrics_record_text_line_break() {
        let mut lyrics = Lyrics::new();
        lyrics.record_text(100, "/World");
        assert_eq!(lyrics.list[0].text, "World");
    }

    #[test]
    fn test_lyrics_record_text_paragraph() {
        let mut lyrics = Lyrics::new();
        lyrics.record_text(100, "\\Hello");
        assert_eq!(lyrics.list[0].text, "Hello");
    }

    #[test]
    fn test_lyrics_record_text_title() {
        let mut lyrics = Lyrics::new();
        lyrics.record_text(0, "@TSong Title");
        assert_eq!(lyrics.list.len(), 1);
        assert_eq!(lyrics.list[0].typ, LyricType::Title);
        assert_eq!(lyrics.list[0].text, "Song Title");
    }

    #[test]
    fn test_lyrics_record_text_info() {
        let mut lyrics = Lyrics::new();
        lyrics.record_text(0, "@IArtist Name");
        assert_eq!(lyrics.list[0].typ, LyricType::Info);
        assert_eq!(lyrics.list[0].text, "Artist Name");
    }

    #[test]
    fn test_lyrics_record_text_ignores_other_at() {
        let mut lyrics = Lyrics::new();
        lyrics.record_text(0, "@KSomething else");
        assert!(!lyrics.has_any());
    }

    #[test]
    fn test_lyrics_record_lyric_basic() {
        let mut lyrics = Lyrics::new();
        lyrics.record_lyric(200, "Syllable");
        assert_eq!(lyrics.list.len(), 1);
        assert_eq!(lyrics.list[0].text, "Syllable");
    }

    #[test]
    fn test_is_lyric_text_filters() {
        assert!(!is_lyric_text(" SYX x"));
        assert!(!is_lyric_text("Track-1"));
        assert!(!is_lyric_text("%- x"));
        assert!(!is_lyric_text("%+ x"));
        assert!(is_lyric_text("Hello"));
    }

    #[test]
    fn test_lyrics_view_empty() {
        let lyrics = Lyrics::new();
        let view = lyrics.to_lyrics_view(0);
        assert!(view.current_line.is_empty());
    }

    #[test]
    fn test_lyrics_view_with_data() {
        let mut lyrics = Lyrics::new();
        lyrics.record_text(0, "Hel");
        lyrics.record_text(96, "lo");
        lyrics.record_text(192, "/World");
        let tempo = vec![TempoChange { click: 0, microseconds_per_quarter: 500000 }];
        lyrics.compute_timing(&tempo, 96);
        let view = lyrics.to_lyrics_view(50);
        assert_eq!(view.current_line, "Hel lo");
    }

    #[test]
    fn test_empty_midi_no_lyrics() {
        let data = make_simple_midi(&[]);
        let mf = midi_parse_data(&data, "").unwrap();
        assert!(!mf.lyrics.has_any());
    }

    #[test]
    fn test_running_status() {
        let mut track_bytes = Vec::new();
        write_var_length(&mut track_bytes, 0);
        track_bytes.push(0x90); track_bytes.push(0x3C); track_bytes.push(0x7F);
        write_var_length(&mut track_bytes, 96);
        track_bytes.push(0x3E); track_bytes.push(0x7F);
        write_var_length(&mut track_bytes, 0);
        track_bytes.push(0xFF);
        track_bytes.push(0x2F);
        track_bytes.push(0x00);
        let data = make_simple_midi(&[&track_bytes]);
        let mf = midi_parse_data(&data, "").unwrap();
        assert!(mf.tracks.len() >= 1);
    }

    #[test]
    fn test_latin1_encoding() {
        let text = b"OLE\xE9";
        let events = vec![meta_event(0, 0x01, text), end_track()];
        let track = build_track(&events);
        let data = make_simple_midi(&[&track]);
        let mf = midi_parse_data(&data, "").unwrap();
        assert_eq!(mf.lyrics.list[0].text, "OLE\u{00E9}");
    }

    #[test]
    fn test_compute_note_bounds_empty() {
        let (e, l) = compute_note_bounds(&[], &[], 96);
        assert_eq!(e, 0.0);
        assert_eq!(l, 0.0);
    }

    #[test]
    fn test_to_lyrics_view_progress() {
        let mut lyrics = Lyrics::new();
        lyrics.record_text(0, "Hi");
        lyrics.record_text(96, "/There");
        let tempo = vec![TempoChange { click: 0, microseconds_per_quarter: 500000 }];
        lyrics.compute_timing(&tempo, 96);
        let view = lyrics.to_lyrics_view(500);
        assert!(view.current_line_progress >= 0.0);
    }

    #[test]
    fn test_full_kar_file_parse() {
        let t1_events = vec![
            meta_event(0, 0x03, b"Words"),
            meta_event(0, 0x51, &[0x07, 0xA1, 0x20]),
            meta_event(0, 0x01, b"@TSong Title"),
            note_on(0, 0, 60, 100),
            meta_event(96, 0x01, b"Hel"),
            note_off(0, 0, 60, 0),
            note_on(96, 0, 64, 100),
            meta_event(96, 0x01, b"lo"),
            note_off(0, 0, 64, 0),
            note_on(96, 0, 67, 100),
            meta_event(96, 0x05, b"World"),
            note_off(0, 0, 67, 0),
            end_track(),
        ];
        let t2_events = vec![
            note_on(0, 1, 36, 80),
            note_off(384, 1, 36, 0),
            end_track(),
        ];

        let t1 = build_track(&t1_events);
        let t2 = build_track(&t2_events);
        let data = make_simple_midi(&[&t1, &t2]);
        let mf = midi_parse_data(&data, "latin-1").unwrap();
        assert!(mf.lyrics.has_any());
        assert!(mf.lyrics.list.len() >= 3);
        assert!(mf.last_note_ms > 0.0);
    }

    #[test]
    fn test_track_desc_defaults() {
        let td = TrackDesc::new(0);
        assert_eq!(td.track_num, 0);
        assert_eq!(td.total_clicks, 0);
        assert!(td.first_note_click.is_none());
        assert!(!td.lyrics_track);
    }

    #[test]
    fn test_select_best_lyrics_no_tracks() {
        assert!(!select_best_lyrics(&[]).has_any());
    }
}
