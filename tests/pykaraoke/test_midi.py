"""Tests for pykaraoke.midi — the pure MIDI/KAR parser."""

import os
import struct

import pytest

from pykaraoke.midi import Lyrics, MidiFile, MidiTimestamp, parse_midi, var_length

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")
ELVIS_KAR = os.path.join(
    FIXTURES, "ultrastar-deluxe", "Creative Commons", "elvis_presley_-_cant_help_falling_in_love.kar"
)


# ---------------------------------------------------------------------------
# Synthetic MIDI builders
# ---------------------------------------------------------------------------


def _vlq(value: int) -> bytes:
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append(0x80 | (value & 0x7F))
        value >>= 7
    return bytes(reversed(out))


def _track(events: list[bytes]) -> bytes:
    data = b"".join(events)
    return b"MTrk" + struct.pack(">L", len(data)) + data


def _make_midi(tempo=500000, ticks_per_quarter=480) -> bytes:
    """A tiny 2-bar song: tempo, then notes + lyrics on one track."""
    header = b"MThd" + struct.pack(">LHHH", 6, 0, 1, ticks_per_quarter)
    events = [
        b"\x00\xff\x58\x04\x04\x02\x18\x08",  # time signature
        b"\x00\xff\x51\x03" + tempo.to_bytes(3, "big"),  # set tempo
        b"\x00\xff\x03\x05Words",
        b"\x00\x90\x3c\x64",  # note on C4 vel 100
        b"\x00\xff\x05\x03Hel",
        b"\x60\x80\x3c\x00",  # note off after 96 ticks
        b"\x00\x90\x48\x64",  # note on C5 (0x48 = 72)
        b"\x60\xff\x05\x03lo!",
        b"\x60\x80\x48\x00",
        b"\x00\xff\x2f\x00",
    ]
    return header + _track(events)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestParseMidi:
    def test_parses_real_kar_fixture(self):
        with open(ELVIS_KAR, "rb") as f:
            data = f.read()
        mf = parse_midi(data)
        assert mf is not None
        assert mf.lyrics is not None
        assert mf.lyrics.has_any()
        assert mf.click_units_per_quarter
        # Lyrics have absolute ms timing in increasing order.
        times = [s.ms for s in mf.lyrics.list]
        assert all(t is not None for t in times)
        assert times == sorted(times)

    def test_synthetic_song_notes_and_lyrics(self):
        mf = parse_midi(_make_midi())
        assert mf is not None
        assert mf.lyrics is not None
        texts = [s.text.strip() for s in mf.lyrics.list]
        assert "Hel" in texts
        assert "lo!" in texts
        assert mf.notes, "note events should be collected"
        starts = [n[0] for n in mf.notes]
        assert starts == sorted(starts)
        for _start, channel, note, velocity, duration in mf.notes:
            assert channel == 0
            assert note in (60, 72)
            assert velocity == 100
            assert duration > 0
        assert mf.last_note_ms > 0

    def test_tempo_timing(self):
        # 500000 us/quarter = 500 ms/quarter; 480 ticks/quarter ->
        # 96 ticks = 100 ms.
        mf = parse_midi(_make_midi(tempo=500000))
        assert mf is not None
        # First note at click 0, second at click 96+96? (see events:
        # second note-on is 96 ticks after the first note-off).
        assert mf.notes[0][0] == 0
        assert mf.notes[1][0] >= 100

    def test_malformed_header_returns_none(self):
        assert parse_midi(b"garbage") is None
        assert parse_midi(b"") is None
        assert parse_midi(b"MThd\x00\x00\x00\x06\x00\x00\x00\x01") is None  # truncated

    def test_no_lyrics_returns_none(self):
        # Header + a track with only a note, no lyric events.
        header = b"MThd" + struct.pack(">LHHH", 6, 0, 1, 480)
        track = _track([b"\x00\x90\x3c\x64", b"\x60\x80\x3c\x00", b"\x00\xff\x2f\x00"])
        assert parse_midi(header + track) is None

    def test_to_dict_serializable(self):
        mf = parse_midi(_make_midi())
        assert mf is not None
        d = mf.to_dict()
        assert "lyrics" in d
        assert "notes" in d
        assert "duration_ms" in d
        assert isinstance(d["notes"][0], list)
        # Lyrics carry timing, text, type and line number for the UI.
        assert all("ms" in s and "text" in s and "type" in s and "line" in s for s in d["lyrics"])

    def test_no_duet_parts_in_midi(self):
        # Singer/part tagging is an LRC feature; MIDI/KAR lyrics never
        # carry it, so the payload exposes no duet information.
        with open(ELVIS_KAR, "rb") as f:
            real_kar = f.read()
        for midi in (_make_midi(), real_kar):
            mf = parse_midi(midi)
            assert mf is not None
            d = mf.to_dict()
            assert "parts" not in d
            assert all("part" not in s for s in d["lyrics"])


class TestMidiTimestamp:
    def test_single_tempo(self):
        mf = MidiFile()
        mf.click_units_per_quarter = 480
        mf.tempo = [(0, 500000)]  # 500 ms per quarter
        ts = MidiTimestamp(mf)
        ts.advance_to_click(480)
        assert ts.ms == pytest.approx(500.0)

    def test_tempo_change(self):
        mf = MidiFile()
        mf.click_units_per_quarter = 480
        mf.tempo = [(0, 500000), (480, 250000)]
        ts = MidiTimestamp(mf)
        ts.advance_to_click(960)
        # 500 ms at 500 us/qn + 500 ms at 250 us/qn.
        assert ts.ms == pytest.approx(750.0)

    def test_no_backward_jumps(self):
        mf = MidiFile()
        mf.click_units_per_quarter = 480
        mf.tempo = [(0, 500000)]
        ts = MidiTimestamp(mf)
        ts.advance_to_click(960)
        before = ts.ms
        ts.advance_to_click(100)  # backward: ignored
        assert ts.ms == before


class TestLyrics:
    def test_record_text_breaks(self):
        lyr = Lyrics()
        lyr.record_text(0, "Hel")
        lyr.record_text(10, "/lo")  # line break
        lyr.record_text(20, "\\here")  # paragraph break
        assert [s.text for s in lyr.list] == ["Hel", "lo", "there"]
        assert [s.line for s in lyr.list] == [0, 1, 3]  # 0-based lines

    def test_record_text_title_and_info(self):
        lyr = Lyrics()
        lyr.record_text(0, "@TSong Title")
        lyr.record_text(0, "@ISome info")
        lyr.record_text(0, "@Xignored")
        assert [s.text for s in lyr.list] == ["Song Title", "Some info"]
        assert [s.type for s in lyr.list] == [2, 1]

    def test_record_text_multiline_title(self):
        lyr = Lyrics()
        lyr.record_text(0, "@TLine1\nLine2")
        assert [s.text for s in lyr.list] == ["Line1", "Line2"]
        assert [s.type for s in lyr.list] == [2, 2]

    def test_record_text_embedded_newlines(self):
        lyr = Lyrics()
        lyr.record_text(0, "Hel\nlo")
        assert [s.text for s in lyr.list] == ["Hel", "lo"]

    def test_record_text_strips_nul_and_cr(self):
        lyr = Lyrics()
        lyr.record_text(0, "He\x00l\r")
        lyr.record_text(0, "\r")  # becomes empty -> skipped
        assert [s.text for s in lyr.list] == ["Hel"]

    def test_record_lyric(self):
        lyr = Lyrics()
        lyr.record_lyric(0, "Hel")
        lyr.record_lyric(10, "\r")  # line break
        lyr.record_lyric(20, "lo")
        assert [s.text for s in lyr.list] == ["Hel", "lo"]
        assert [s.line for s in lyr.list] == [0, 1]  # 0-based lines

    def test_record_lyric_break_variants(self):
        lyr = Lyrics()
        lyr.record_lyric(0, "A")
        lyr.record_lyric(1, "\n")  # paragraph break
        lyr.record_lyric(2, "B")
        lyr.record_lyric(3, "\r\n")  # line break
        lyr.record_lyric(4, "\\C")  # paragraph break prefix
        lyr.record_lyric(5, "/D")  # line break prefix
        lyr.record_lyric(6, "E\nF")  # embedded newline
        assert [s.text for s in lyr.list] == ["A", "B", "C", "D", "E", "F"]
        assert [s.line for s in lyr.list] == [0, 2, 4, 5, 6, 7]

    def test_analyze_spaces_adds_gaps(self):
        lyr = Lyrics()
        lyr.record_text(0, "Hel")
        lyr.record_text(10, "lo")
        lyr.record_text(20, "there")
        lyr.analyze_spaces()
        joined = "".join(s.text for s in lyr.list)
        assert " " in joined

    def test_analyze_spaces_respects_existing_gaps(self):
        lyr = Lyrics()
        lyr.record_text(0, "Hel ")
        lyr.record_text(10, " lo ")
        lyr.record_text(20, "there")
        before = [s.text for s in lyr.list]
        lyr.analyze_spaces()
        assert [s.text for s in lyr.list] == before

    def test_analyze_spaces_strips_hyphen_continuation(self):
        lyr = Lyrics()
        lyr.record_text(0, "He-")
        lyr.record_text(10, "llo")
        lyr.record_text(20, "world")
        lyr.analyze_spaces()
        texts = [s.text for s in lyr.list]
        assert "He" in texts
        assert not any(t.endswith("-") for t in texts[:-1])

    def test_analyze_spaces_no_syllables(self):
        lyr = Lyrics()
        lyr.analyze_spaces()  # empty: no crash


# ---------------------------------------------------------------------------
# Edge-case coverage: meta events, channel events, running status
# ---------------------------------------------------------------------------


def _header(ticks: int = 480, tracks: int = 1, fmt: int = 0) -> bytes:
    return b"MThd" + struct.pack(">LHHH", 6, fmt, tracks, ticks)


def _end() -> bytes:
    return b"\x00\xff\x2f\x00"


class TestParseMidiEdgeCases:
    def test_smpte_division_returns_none(self):
        # SMPTE division sets frames but no click_units_per_quarter -> None.
        smpte_div = 0xE728  # 0xE7 frames code, 40 subframes
        header = b"MThd" + struct.pack(">LHHH", 6, 0, 1, smpte_div)
        assert parse_midi(header + _track([_end()])) is None

    def test_zero_division_returns_none(self):
        assert parse_midi(_header(ticks=0) + _track([_end()])) is None

    def test_header_only_returns_none(self):
        assert parse_midi(_header()) is None

    def test_non_midi_header_returns_none(self):
        header = b"XXXX" + struct.pack(">LHHH", 6, 0, 1, 480)
        assert parse_midi(header + _track([_end()])) is None

    def test_truncated_track_returns_none(self):
        # Track header claims more bytes than are present: the track parse
        # stops mid-event and the file has no complete tracks.
        bad = b"MTrk" + struct.pack(">L", 100) + b"\x00\x90"
        assert parse_midi(_header() + bad) is None

    def test_meta_copyright_instrument_and_names(self, caplog):
        events = [
            b"\x00\xff\x02\x05(c) X",  # copyright
            b"\x00\xff\x04\x03pno",  # instrument name
            b"\x00\xff\x06\x03mkr",  # marker
            b"\x00\xff\x07\x03cue",  # cue point
            b"\x00\xff\x08\x03pnm",  # program name
            b"\x00\xff\x09\x03dev",  # device name
            b"\x00\xff\x00\x06\x02\x01\x02\x00\x01",  # sequence number
            b"\x00\xff\x14\x02\x00\x00",  # MIDI channel (fixed 2)
            b"\x00\xff\x15\x02\x00\x00",  # MIDI port (fixed 2)
            b"\x00\xff\x0a\x03xyz",  # unknown meta -> discarded
            b"\x00\xff\x54\x05\x01\x02\x03\x04\x05",  # SMPTE offset
            b"\x00\xff\x59\x02\x00\x02",  # key signature
            b"\x00\xff\x7f\x03\x00\x01\x02",  # sequencer specific, ID 0
            b"\x00\xff\x7f\x03\x41\x01\x02",  # sequencer specific, ID != 0
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        with caplog.at_level("DEBUG", logger="pykaraoke.midi"):
            mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert [s.text for s in mf.lyrics.list] == ["Hel"]
        assert "Unknown meta-event: 0xA" in caplog.text

    def test_meta_time_signature_short_packet(self):
        events = [
            b"\x00\xff\x58\x04\x04\x02\x18",  # 4-byte: no notes_per_24
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert mf.numerator == 4
        assert mf.denominator == 2
        assert mf.clocks_per_metronome_tick == 0x18
        assert mf.notes_per_24_midi_clocks is None

    def test_meta_set_tempo_truncated(self):
        # A truncated tempo event is skipped; the file still parses via the
        # default tempo.
        events = [
            b"\x00\xff\x51\x03",  # claims 3 bytes but none follow
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert mf.tempo == [(0, 0)]  # default, no tempo events appended

    def test_long_text_event_is_ignored(self):
        payload = b"A" * 1200
        events = [
            b"\x00\xff\x01" + _vlq(len(payload)) + payload,
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert [s.text for s in mf.lyrics.list] == ["Hel"]

    def test_lyric_text_filter(self):
        # _is_lyric_text rejects tool noise; filtered events don't count.
        events = [
            b"\x00\xff\x05\x08 SYX track",
            b"\x00\xff\x05\x09Track-0001",
            b"\x00\xff\x05\x08%-00:00.0",
            b"\x00\xff\x05\x08%+00:00.0",
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is notidi if False else mf is not None
        assert [s.text for s in mf.lyrics.list] == ["Hel"]

    def test_text_event_filter(self):
        events = [
            b"\x00\xff\x01\x08 SYX track",
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert [s.text for s in mf.lyrics.list] == ["Hel"]

    def test_track_title_words_marks_lyrics_track(self):
        events = [
            b"\x00\xff\x03\x05Words",
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert mf.track_list[0].lyrics_track

    def test_track_title_other_text(self):
        events = [
            b"\x00\xff\x03\x05Verse",
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert not mf.track_list[0].lyrics_track

    def test_running_status_note_events(self):
        # A data byte without a status byte reuses the running status.
        events = [
            b"\x00\x90\x3c\x64",  # note on C4
            b"\x30\x64",  # running status: note on D4
            b"\x00\x90\x48\x00",  # velocity 0 == note off
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        notes = {(n[2], n[3]) for n in mf.notes}
        assert notes == {(60, 100), (62, 100)}

    def test_note_on_zero_velocity_is_note_off(self):
        events = [
            b"\x00\x90\x3c\x64",
            b"\x60\x90\x3c\x00",  # note off via velocity 0
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert len(mf.notes) == 1
        assert mf.notes[0][4] > 0  # duration from paired off

    def test_unmatched_note_gets_default_duration(self):
        events = [
            b"\x00\x90\x3c\x64",  # no note-off
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert len(mf.notes) == 1
        assert mf.notes[0][4] == 250  # default duration

    def test_channel_events_skipped(self):
        events = [
            b"\x00\xa0\x3c\x40",  # after-touch
            b"\x00\xb0\x07\x64",  # control change
            b"\x00\xe0\x00\x40",  # pitch wheel
            b"\x00\xc0\x19",  # program change
            b"\x00\xd0\x40",  # channel pressure
            b"\x00\x90\x3c\x64",
            b"\x60\x80\x3c\x00",
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert mf.programs == {0: 0x19}
        assert len(mf.notes) == 1

    def test_sysex_event_skipped(self):
        events = [
            b"\x00\xf0\x03\x01\x02\x03",
            b"\x00\x90\x3c\x64",
            b"\x60\x80\x3c\x00",
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert len(mf.notes) == 1

    def test_multiple_tracks_best_lyrics_wins(self):
        # Track 0: one lyric. Track 1 (marked "Words"): two lyrics.
        track0 = _track([b"\x00\xff\x05\x02Aa", _end()])
        track1 = _track(
            [b"\x00\xff\x03\x05Words", b"\x00\xff\x05\x02Bb", b"\x00\xff\x05\x02Cc", _end()]
        )
        mf = parse_midi(_header(tracks=2) + track0 + track1)
        assert mf is not None
        assert [s.text for s in mf.lyrics.list] == ["Bb", "Cc"]

    def test_text_track_wins_when_no_lyric_events(self):
        # A track with only text events still provides lyrics.
        events = [
            b"\x00\xff\x01\x03Hel",
            b"\x00\xff\x01\x03/lo",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert [s.text for s in mf.lyrics.list] == ["Hel", "lo"]

    def test_same_track_text_vs_lyric_prefers_longer(self):
        # Both text and lyric events in one track: the longer list wins.
        events = [
            b"\x00\xff\x01\x02T1",
            b"\x00\xff\x05\x02L1",
            b"\x00\xff\x05\x02L2",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert [s.text for s in mf.lyrics.list] == ["L1", "L2"]

    def test_same_track_text_wins_tie(self):
        # Equal counts: text events are preferred.
        events = [
            b"\x00\xff\x01\x02T1",
            b"\x00\xff\x01\x02T2",
            b"\x00\xff\x05\x02L1",
            b"\x00\xff\x05\x02L2",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert [s.text for s in mf.lyrics.list] == ["T1", "T2"]

    def test_truncated_event_stops_track(self):
        # A mid-event EOF ends the track; a second intact track keeps the
        # file parseable.
        bad = b"MTrk" + struct.pack(">L", 4) + b"\x00\x90"
        track1 = _track([b"\x00\xff\x05\x03Hel", _end()])
        mf = parse_midi(_header(tracks=2) + bad + track1)
        assert mf is not None
        assert [s.text for s in mf.lyrics.list] == ["Hel"]

    def test_multiple_note_ons_same_pitch_fifo(self):
        # Two overlapping note-ons for the same pitch pair FIFO with the
        # two note-offs.
        events = [
            b"\x00\x90\x3c\x64",
            b"\x30\x90\x3c\x50",
            b"\x30\x80\x3c\x00",
            b"\x30\x80\x3c\x00",
            b"\x00\xff\x05\x03Hel",
            _end(),
        ]
        mf = parse_midi(_header() + _track(events))
        assert mf is not None
        assert len(mf.notes) == 2
        velocities = sorted(n[3] for n in mf.notes)
        assert velocities == [50, 100]


class TestMidiTimestampPartials:
    def test_tempo_entry_with_gap_is_skipped(self):
        # A tempo mark in the future: earlier clicks use the initial tempo
        # until the mark is reached.
        mf = MidiFile()
        mf.click_units_per_quarter = 480
        mf.tempo = [(0, 500000), (960, 250000)]
        ts = MidiTimestamp(mf)
        ts.advance_to_click(480)
        assert ts.ms == pytest.approx(500.0)


class TestVarLength:
    def test_empty_stream(self):
        import io

        assert var_length(io.BytesIO(b"")) == (0, 0)

    def test_long_varint_stops_after_seven_bytes(self):
        import io

        data = b"\xff" * 8  # 8 continuation bytes: shift exceeds limit
        value, read = var_length(io.BytesIO(data))
        assert read == 7
        assert value > 0
