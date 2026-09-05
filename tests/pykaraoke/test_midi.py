"""Tests for pykaraoke.midi — the pure MIDI/KAR parser."""

import os
import struct

import pytest

from pykaraoke.midi import Lyrics, MidiFile, MidiTimestamp, parse_midi

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
        assert "Hel" in texts and "lo!" in texts
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
        assert "lyrics" in d and "notes" in d and "duration_ms" in d
        assert isinstance(d["notes"][0], list)
        # Lyrics carry timing, text, type and line number for the UI.
        assert all("ms" in s and "text" in s and "type" in s and "line" in s for s in d["lyrics"])


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
        lyr.record_text(20, "\\there")  # paragraph break
        assert [s.text for s in lyr.list] == ["Hel", "lo", "there"]
        assert [s.line for s in lyr.list] == [0, 1, 3]  # 0-based lines

    def test_record_text_title_and_info(self):
        lyr = Lyrics()
        lyr.record_text(0, "@TSong Title")
        lyr.record_text(0, "@ISome info")
        lyr.record_text(0, "@Xignored")
        assert [s.text for s in lyr.list] == ["Song Title", "Some info"]
        assert [s.type for s in lyr.list] == [2, 1]

    def test_record_lyric(self):
        lyr = Lyrics()
        lyr.record_lyric(0, "Hel")
        lyr.record_lyric(10, "\r")  # line break
        lyr.record_lyric(20, "lo")
        assert [s.text for s in lyr.list] == ["Hel", "lo"]
        assert [s.line for s in lyr.list] == [0, 1]  # 0-based lines

    def test_analyze_spaces_adds_gaps(self):
        lyr = Lyrics()
        lyr.record_text(0, "Hel")
        lyr.record_text(10, "lo")
        lyr.record_text(20, "there")
        lyr.analyze_spaces()
        joined = "".join(s.text for s in lyr.list)
        assert " " in joined
