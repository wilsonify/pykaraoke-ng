"""Pure-Python MIDI/KAR parser (Pyodide-compatible).

Port of the classic PyKaraoke MIDI parser with no pygame dependency.
Parses Standard MIDI Files (SMF) plus karaoke lyric meta-events, and
produces:

* timed lyric syllables (``MidiFile.lyrics``)
* timed note events (``MidiFile.notes``) for a web synthesizer
* per-channel program (instrument) changes (``MidiFile.programs``)
"""

from __future__ import annotations

import io
import struct

# text types.
TEXT_LYRIC = 0
TEXT_INFO = 1
TEXT_TITLE = 2

_DEBUG = False


class MidiFile:
    def __init__(self):
        self.track_list: list[TrackDesc] = []

        # Chosen lyric list, converted from (clicks, text) to (ms, text).
        self.lyrics: Lyrics | None = None

        self.text_encoding = ""  # The encoding of text in midi file

        self.click_units_per_smpte = None
        self.smpte_frames_per_sec = None
        self.click_units_per_quarter = None

        # Tempo changes: (click, microseconds-per-quarter-note).
        self.tempo: list[tuple[int, int]] = [(0, 0)]

        self.numerator = None
        self.denominator = None
        self.clocks_per_metronome_tick = None
        self.notes_per_24_midi_clocks = None
        self.earliest_note_ms = 0  # Start of earliest note in song
        self.last_note_ms = 0  # End of latest note in song

        # Note events: [start_ms, channel, note, velocity, duration_ms].
        self.notes: list[list[int]] = []
        # Program changes: {channel: program}.
        self.programs: dict[int, int] = {}

    def to_dict(self) -> dict:
        """JSON-friendly view of the parsed song for the web UI."""
        lyrics = []
        if self.lyrics is not None:
            for syl in self.lyrics.list:
                lyrics.append({"ms": syl.ms, "text": syl.text, "type": syl.type, "line": syl.line})
        return {
            "lyrics": lyrics,
            "notes": [list(n) for n in self.notes],
            "programs": {str(k): v for k, v in sorted(self.programs.items())},
            "duration_ms": int(self.last_note_ms or 0),
            "tempo": [list(t) for t in self.tempo],
        }


class TrackDesc:
    def __init__(self, track_num):
        self.track_num = track_num
        self.total_clicks_from_start = 0
        self.bytes_read = 0
        self.first_note_click = None
        self.first_note_ms = None
        self.last_note_click = None
        self.last_note_ms = None
        self.lyrics_track = False
        self.running_status = 0

        self.text_events = Lyrics()
        self.lyric_events = Lyrics()

        # Note events collected while parsing (clicks, not ms).
        self.note_ons: list[tuple[int, int, int, int]] = []  # (click, ch, note, vel)
        self.note_offs: list[tuple[int, int, int]] = []  # (click, ch, note)
        self.programs: dict[int, int] = {}


class MidiTimestamp:
    """Applies tempo changes to click counts, computing elapsed ms."""

    def __init__(self, midifile):
        self.click_units_per_quarter = midifile.click_units_per_quarter
        self.tempo = midifile.tempo
        self.ms = 0
        self.click = 0
        self.i = 0

    def advance_to_click(self, click):
        clicks = click - self.click
        if clicks < 0:
            # Ignore jumps backward in time.
            return

        while clicks > 0 and self.i < len(self.tempo):
            clicks_remaining = max(self.tempo[self.i][0] - self.click, 0)
            clicks_used = min(clicks, clicks_remaining)
            if clicks_used != 0:
                self.ms += self.get_time_for_clicks(clicks_used, self.tempo[self.i - 1][1])
            self.click += clicks_used
            clicks -= clicks_used
            clicks_remaining -= clicks_used
            if clicks_remaining == 0:
                self.i += 1

        if clicks > 0:
            # The last tempo mark holds forever.
            self.ms += self.get_time_for_clicks(clicks, self.tempo[-1][1])
            self.click += clicks

    def get_time_for_clicks(self, clicks, tempo):
        microseconds = (float(clicks) / self.click_units_per_quarter) * tempo
        return microseconds / 1000


class LyricSyllable:
    """A single lyric event (a syllable) displayed at a given time."""

    def __init__(self, click, text, line, type=TEXT_LYRIC):
        self.click = click
        self.ms = None
        self.text = text
        self.line = line
        self.type = type

    def __repr__(self):
        return f"<{self.ms} {self.text}>"


class Lyrics:
    """Complete lyrics of a song as a list of syllables in event order."""

    def __init__(self):
        self.list: list[LyricSyllable] = []
        self.line = 0

    def has_any(self):
        return bool(self.list)

    def record_text(self, click, text):
        """Record a MIDI 0x1 text event (a syllable)."""
        text = text.replace("\x00", "").replace("\r", "")
        if not text:
            return

        if text[0] == "@":
            if text[1] == "T":
                text_type = TEXT_TITLE
            elif text[1] == "I":
                text_type = TEXT_INFO
            else:
                return  # any other comment is ignored
            for line in text[2:].split("\n"):
                line = line.strip()
                self.line += 1
                self.list.append(LyricSyllable(click, line, self.line, text_type))
            return

        if text[0] == "\\":
            # Paragraph break (like a line break, with an extra blank line).
            self.line += 2
            text = text[1:]
        elif text[0] == "/":
            # Line break.
            self.line += 1
            text = text[1:]

        if text:
            lines = text.split("\n")
            self.list.append(LyricSyllable(click, lines[0], self.line))
            for line in lines[1:]:
                self.line += 1
                self.list.append(LyricSyllable(click, line, self.line))

    def record_lyric(self, click, text):
        """Record a MIDI 0x5 lyric event (a syllable)."""
        text = text.replace("\x00", "")

        if text == "\n":
            self.line += 2
        elif text == "\r" or text == "\r\n":
            self.line += 1
        elif text:
            text = text.replace("\r", "")
            if text[0] == "\\":
                self.line += 2
                text = text[1:]
            elif text[0] == "/":
                self.line += 1
                text = text[1:]
            lines = text.split("\n")
            self.list.append(LyricSyllable(click, lines[0], self.line))
            for line in lines[1:]:
                self.line += 1
                self.list.append(LyricSyllable(click, line, self.line))

    def compute_timing(self, midifile):
        ts = MidiTimestamp(midifile)
        for syllable in self.list:
            ts.advance_to_click(syllable.click)
            syllable.ms = int(ts.ms)

        for track_desc in midifile.track_list:
            ts = MidiTimestamp(midifile)
            if track_desc.first_note_click is not None:
                ts.advance_to_click(track_desc.first_note_click)
                track_desc.first_note_ms = ts.ms
            if track_desc.last_note_click is not None:
                ts.advance_to_click(track_desc.last_note_click)
                track_desc.last_note_ms = ts.ms

    def analyze_spaces(self):
        """Repair the degenerate no-spaces-between-words case."""
        lines = self._group_syllables_into_lines()
        total_num_syls, total_num_gaps = self._count_gaps(lines)
        if total_num_syls and float(total_num_gaps) / float(total_num_syls) < 0.1:
            self._insert_spaces(lines)

    def _group_syllables_into_lines(self):
        line_number = None
        lines = []
        current_line = []
        for syllable in self.list:
            if syllable.line != line_number:
                if current_line:
                    lines.append(current_line)
                current_line = []
                line_number = syllable.line
            current_line.append(syllable)
        if current_line:
            lines.append(current_line)
        return lines

    @staticmethod
    def _count_gaps(lines):
        total_num_syls = 0
        total_num_gaps = 0
        for line in lines:
            num_syls = len(line) - 1
            num_gaps = 0
            for i in range(num_syls):
                if (
                    line[i].text.rstrip() != line[i].text
                    or line[i + 1].text.lstrip() != line[i + 1].text
                ):
                    num_gaps += 1
            total_num_syls += num_syls
            total_num_gaps += num_gaps
        return total_num_syls, total_num_gaps

    @staticmethod
    def _insert_spaces(lines):
        for line in lines:
            for syllable in line[:-1]:
                if syllable.text.endswith("-"):
                    syllable.text = syllable.text[:-1]
                else:
                    syllable.text += " "


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_midi(midi_data: bytes, encoding: str = "") -> MidiFile | None:
    """Parse *midi_data* and return a :class:`MidiFile`, or None on failure."""
    midifile = MidiFile()
    midifile.text_encoding = encoding

    filehdl = io.BytesIO(midi_data)

    packet = filehdl.read(8)
    if len(packet) < 8:
        return None
    chunk_type, length = struct.unpack(">4sL", packet)
    if chunk_type != b"MThd":
        return None

    packet = filehdl.read(length)
    if len(packet) < 6:
        return None
    _, _, division = struct.unpack(">HHH", packet[:6])
    if division & 0x8000:
        midifile.click_units_per_smpte = division & 0x00FF
        midifile.smpte_frames_per_sec = division & 0x7F00
    else:
        midifile.click_units_per_quarter = division & 0x7FFF
    if not midifile.click_units_per_quarter:
        return None

    _parse_midi_tracks(filehdl, midifile)

    if not midifile.track_list:
        return None

    midifile.lyrics = _select_best_lyrics(midifile)
    if midifile.lyrics is None or not midifile.lyrics.has_any():
        return None

    midifile.lyrics.compute_timing(midifile)
    midifile.lyrics.analyze_spaces()

    midifile.earliest_note_ms, midifile.last_note_ms = _compute_note_bounds(midifile)
    _collect_notes(midifile)

    return midifile


def _parse_midi_tracks(filehdl, midifile):
    track_num = 0
    while True:
        packet = filehdl.read(8)
        if packet == b"" or len(packet) < 8:
            break
        chunk_type, length = struct.unpack(">4sL", packet)
        if chunk_type != b"MTrk" and _DEBUG:
            print("Didn't find expected MIDI Track")
        track_desc = midi_parse_track(filehdl, midifile, track_num, length)
        if not track_desc:
            break
        midifile.track_list.append(track_desc)
        track_num += 1


def _select_best_lyrics(midifile):
    best_sort_key = (False, -1)
    best_lyrics = None
    for track_desc in midifile.track_list:
        lyrics = _choose_lyrics_from_track(track_desc)
        if not lyrics:
            continue
        sort_key = (track_desc.lyrics_track, len(lyrics.list))
        if sort_key > best_sort_key:
            best_sort_key = sort_key
            best_lyrics = lyrics
    return best_lyrics


def _choose_lyrics_from_track(track_desc):
    has_text = track_desc.text_events.has_any()
    has_lyric = track_desc.lyric_events.has_any()
    if has_text and has_lyric:
        if len(track_desc.lyric_events.list) > len(track_desc.text_events.list):
            return track_desc.lyric_events
        return track_desc.text_events
    if has_text:
        return track_desc.text_events
    if has_lyric:
        return track_desc.lyric_events
    return None


def _compute_note_bounds(midifile):
    earliest_note_ms = None
    last_note_ms = None
    for track in midifile.track_list:
        if track.first_note_ms is not None and (
            earliest_note_ms is None or track.first_note_ms < earliest_note_ms
        ):
            earliest_note_ms = track.first_note_ms
        if track.last_note_ms is not None and (
            last_note_ms is None or track.last_note_ms > last_note_ms
        ):
            last_note_ms = track.last_note_ms
    return earliest_note_ms or 0, last_note_ms or 0


def _merge_track_programs(midifile, track) -> None:
    """Fold one track's per-channel programs into the file-level map."""
    for ch, program in track.programs.items():
        midifile.programs.setdefault(ch, program)


def _pair_track_notes(track, ts, raw: list) -> None:
    """Pair one track's note-on/off events into (start, end, ch, note, vel)."""
    # FIFO queue of unmatched note-ons per (channel, note).
    pending: dict[tuple[int, int], list[tuple[int, int]]] = {}  # key -> [(click, vel)]
    for click_on, channel, note, velocity in track.note_ons:
        pending.setdefault((channel, note), []).append((click_on, velocity))
    for click_off, channel, note in track.note_offs:
        queue = pending.get((channel, note))
        if not queue:
            continue
        click_on, velocity = queue.pop(0)
        ts.advance_to_click(click_on)
        start_ms = int(ts.ms)
        ts.advance_to_click(click_off)
        end_ms = int(ts.ms)
        raw.append((start_ms, end_ms, channel, note, velocity))


def _append_unmatched_notes(midifile, ts, raw: list) -> None:
    """Notes left without a note-off get a short default duration."""
    for track in midifile.track_list:
        for click_on, channel, note, velocity in track.note_ons:
            ts.advance_to_click(click_on)
            start_ms = int(ts.ms)
            if not any(r[0] == start_ms and r[2] == channel and r[3] == note for r in raw):
                raw.append((start_ms, start_ms + 250, channel, note, velocity))


def _collect_notes(midifile):
    """Pair note-on/off events and convert them to absolute times in ms."""
    ts = MidiTimestamp(midifile)
    raw = []  # (start_ms, end_ms, channel, note, velocity)

    for track in midifile.track_list:
        _merge_track_programs(midifile, track)
        _pair_track_notes(track, ts, raw)

    _append_unmatched_notes(midifile, ts, raw)

    raw.sort(key=lambda n: n[0])
    midifile.notes = [[s, ch, note, vel, max(0, e - s)] for s, e, ch, note, vel in raw]


def midi_parse_track(filehdl, midifile, track_num, length):
    track = TrackDesc(track_num)
    while track.bytes_read < length:
        event_bytes = midi_process_event(filehdl, track, midifile)
        if event_bytes is None or event_bytes == 0:
            return None
        track.bytes_read = track.bytes_read + event_bytes
    return track


def midi_process_event(filehdl, track_desc, midifile):
    bytes_read = 0
    click, var_bytes = var_length(filehdl)
    if var_bytes == 0:
        return 0
    bytes_read = bytes_read + var_bytes
    track_desc.total_clicks_from_start += click
    byte_str = filehdl.read(1)
    bytes_read = bytes_read + 1
    status_byte = byte_str[0] if byte_str else 0

    # Handle the MIDI running status.
    if status_byte & 0x80:
        event_type = status_byte
        if (event_type & 0xF0) != 0xF0:
            track_desc.running_status = event_type
    else:
        event_type = track_desc.running_status
        filehdl.seek(-1, 1)
        bytes_read = bytes_read - 1

    if event_type == 0xFF:
        bytes_read += _process_meta_event(filehdl, track_desc, midifile)
    else:
        bytes_read += _process_channel_event(filehdl, track_desc, event_type)
    return bytes_read


def _process_meta_event(filehdl, track_desc, midifile):
    bytes_read = 0
    byte_str = filehdl.read(1)
    bytes_read += 1
    event = byte_str[0] if byte_str else 0

    handler = _META_EVENT_HANDLERS.get(event)
    if handler:
        bytes_read += handler(filehdl, track_desc, midifile)
    else:
        bytes_read += _meta_discard_var(filehdl, event)
    return bytes_read


def _meta_sequence_number(filehdl, track_desc, midifile):
    bytes_read = 0
    packet = filehdl.read(2)
    bytes_read += 2
    type_val = packet[1] if len(packet) > 1 else 0
    if type_val == 0x02:
        filehdl.read(2)
    return bytes_read


def _meta_text_event(filehdl, track_desc, midifile):
    bytes_read = 0
    length, var_bytes = var_length(filehdl)
    bytes_read += var_bytes
    text = filehdl.read(length)
    bytes_read += length
    if length <= 1000:
        encoding = midifile.text_encoding if midifile.text_encoding != "" else "latin-1"
        text = text.decode(encoding, "replace")
        if _is_lyric_text(text):
            track_desc.text_events.record_text(track_desc.total_clicks_from_start, text)
    return bytes_read


def _meta_copyright(filehdl, track_desc, midifile):
    return _read_and_discard_var(filehdl)


def _meta_track_title(filehdl, track_desc, midifile):
    bytes_read = 0
    length, var_bytes = var_length(filehdl)
    bytes_read += var_bytes
    title = filehdl.read(length)
    bytes_read += length
    if isinstance(title, bytes):
        title = title.decode("latin-1", "replace")
    if title == "Words":
        track_desc.lyrics_track = True
    return bytes_read


def _meta_instrument(filehdl, track_desc, midifile):
    return _read_and_discard_var(filehdl)


def _meta_lyric_event(filehdl, track_desc, midifile):
    bytes_read = 0
    length, var_bytes = var_length(filehdl)
    bytes_read += var_bytes
    lyric = filehdl.read(length)
    bytes_read += length
    encoding = midifile.text_encoding if midifile.text_encoding != "" else "latin-1"
    lyric = lyric.decode(encoding, "replace")
    if _is_lyric_text(lyric):
        track_desc.lyric_events.record_lyric(track_desc.total_clicks_from_start, lyric)
    return bytes_read


def _meta_end_of_track(filehdl, track_desc, midifile):
    filehdl.read(1)
    return 1


def _meta_set_tempo(filehdl, track_desc, midifile):
    packet = filehdl.read(4)
    if len(packet) < 4:
        return len(packet)
    tempo = (packet[1] << 16) | (packet[2] << 8) | packet[3]
    midifile.tempo.append((track_desc.total_clicks_from_start, tempo))
    return 4


def _meta_smpte(filehdl, track_desc, midifile):
    filehdl.read(6)
    return 6


def _meta_time_signature(filehdl, track_desc, midifile):
    packet = filehdl.read(5)
    if len(packet) >= 5:
        midifile.numerator = packet[1]
        midifile.denominator = packet[2]
        midifile.clocks_per_metronome_tick = packet[3]
        midifile.notes_per_24_midi_clocks = packet[4]
    elif len(packet) >= 4:
        midifile.numerator = packet[1]
        midifile.denominator = packet[2]
        midifile.clocks_per_metronome_tick = packet[3]
    return len(packet)


def _meta_key_signature(filehdl, track_desc, midifile):
    filehdl.read(3)
    return 3


def _meta_sequencer_specific(filehdl, track_desc, midifile):
    bytes_read = 0
    length, var_bytes = var_length(filehdl)
    bytes_read += var_bytes
    byte_str = filehdl.read(1)
    bytes_read += 1
    ID = byte_str[0] if byte_str else 0
    if ID == 0:
        filehdl.read(2)
        bytes_read += 2
        length -= 3
    else:
        length -= 1
    filehdl.read(length)
    bytes_read += length
    return bytes_read


def _is_lyric_text(text):
    return " SYX" not in text and "Track-" not in text and "%-" not in text and "%+" not in text


def _read_and_discard_var(filehdl):
    bytes_read = 0
    length, var_bytes = var_length(filehdl)
    bytes_read += var_bytes
    filehdl.read(length)
    bytes_read += length
    return bytes_read


def _meta_discard_var(filehdl, event):
    if _DEBUG:
        print(f"Unknown meta-event: 0x{event:X}")
    return _read_and_discard_var(filehdl)


def _meta_fixed_discard_2(filehdl, track_desc, midifile):
    filehdl.read(2)
    return 2


_META_EVENT_HANDLERS = {
    0x00: _meta_sequence_number,
    0x01: _meta_text_event,
    0x02: _meta_copyright,
    0x03: _meta_track_title,
    0x04: _meta_instrument,
    0x05: _meta_lyric_event,
    0x06: _read_and_discard_var,  # Marker
    0x07: _read_and_discard_var,  # Cue point
    0x08: _read_and_discard_var,  # Program name
    0x09: _read_and_discard_var,  # Device name
    0x20: _meta_fixed_discard_2,  # MIDI Channel
    0x21: _meta_fixed_discard_2,  # MIDI Port
    0x2F: _meta_end_of_track,
    0x51: _meta_set_tempo,
    0x54: _meta_smpte,
    0x58: _meta_time_signature,
    0x59: _meta_key_signature,
    0x7F: _meta_sequencer_specific,
}


def _channel_note_off(filehdl, track_desc, channel):
    """Record a note-off event; returns the consumed data length."""
    packet = filehdl.read(2)
    if len(packet) == 2:
        note = packet[0] & 0x7F
        track_desc.note_offs.append((track_desc.total_clicks_from_start, channel, note))
    track_desc.last_note_click = track_desc.total_clicks_from_start
    return 2


def _channel_note_on(filehdl, track_desc, channel):
    """Record a note-on event (velocity 0 means note off)."""
    packet = filehdl.read(2)
    if len(packet) == 2:
        note = packet[0] & 0x7F
        velocity = packet[1] & 0x7F
        if velocity == 0:
            track_desc.note_offs.append((track_desc.total_clicks_from_start, channel, note))
        else:
            track_desc.note_ons.append(
                (track_desc.total_clicks_from_start, channel, note, velocity)
            )
    if track_desc.first_note_click is None:
        track_desc.first_note_click = track_desc.total_clicks_from_start
    track_desc.last_note_click = track_desc.total_clicks_from_start
    return 2


def _channel_two_byte_data(filehdl):
    """Skip key after-touch / control change / pitch wheel (2-byte data)."""
    filehdl.read(2)
    return 2


def _channel_program_data(filehdl, track_desc, channel, high_nibble):
    """Record a program change / channel after-touch (1-byte data)."""
    packet = filehdl.read(1)
    if high_nibble == 0xC0 and packet:
        track_desc.programs[channel] = packet[0] & 0x7F
    return 1


def _process_channel_event(filehdl, track_desc, event_type):
    high_nibble = event_type & 0xF0
    channel = event_type & 0x0F

    if high_nibble == 0x80:
        return _channel_note_off(filehdl, track_desc, channel)
    if high_nibble == 0x90:
        return _channel_note_on(filehdl, track_desc, channel)
    if high_nibble in (0xA0, 0xB0, 0xE0):
        return _channel_two_byte_data(filehdl)
    if high_nibble in (0xC0, 0xD0):
        return _channel_program_data(filehdl, track_desc, channel, high_nibble)
    if event_type == 0xF0:
        return _process_sysex_f0(filehdl)
    return _read_and_discard_var(filehdl)


def _process_sysex_f0(filehdl):
    bytes_read = 0
    length, var_bytes = var_length(filehdl)
    bytes_read += var_bytes
    filehdl.read(length)
    bytes_read += length
    return bytes_read


def var_length(filehdl):
    converted_int = 0
    bit_shift = 0
    bytes_read = 0
    while bit_shift <= 42:
        byte_str = filehdl.read(1)
        bytes_read = bytes_read + 1
        if byte_str:
            byte_val = byte_str[0]
            converted_int = (converted_int << 7) | (byte_val & 0x7F)
            if byte_val & 0x80:
                bit_shift = bit_shift + 7
            else:
                break
        else:
            return (0, 0)
    return (converted_int, bytes_read)
