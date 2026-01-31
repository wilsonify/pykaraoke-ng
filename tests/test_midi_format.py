"""Tests for MIDI/KAR file format handling.

Tests MIDI timing, byte parsing, and karaoke event structures
without requiring pygame.
"""

import pytest
import struct


class TestMIDIConstants:
    """Test MIDI file format constants."""

    def test_midi_header_id(self):
        """Test MIDI file header identifier."""
        MIDI_HEADER_ID = b"MThd"
        assert len(MIDI_HEADER_ID) == 4
        assert MIDI_HEADER_ID == b"MThd"

    def test_midi_track_id(self):
        """Test MIDI track chunk identifier."""
        MIDI_TRACK_ID = b"MTrk"
        assert len(MIDI_TRACK_ID) == 4
        assert MIDI_TRACK_ID == b"MTrk"

    def test_midi_header_length(self):
        """Test MIDI header data length."""
        # Standard MIDI header is always 6 bytes
        MIDI_HEADER_LENGTH = 6
        assert MIDI_HEADER_LENGTH == 6

    def test_midi_status_bytes(self):
        """Test MIDI status byte ranges."""
        # MIDI status bytes are 0x80-0xFF (high bit set)
        # Channel messages: 0x80-0xEF
        # System messages: 0xF0-0xFF

        NOTE_OFF = 0x80
        NOTE_ON = 0x90
        POLY_PRESSURE = 0xA0
        CONTROL_CHANGE = 0xB0
        PROGRAM_CHANGE = 0xC0
        CHANNEL_PRESSURE = 0xD0
        PITCH_BEND = 0xE0
        SYSTEM_EXCLUSIVE = 0xF0
        META_EVENT = 0xFF

        # All should have high bit set
        for status in [
            NOTE_OFF,
            NOTE_ON,
            POLY_PRESSURE,
            CONTROL_CHANGE,
            PROGRAM_CHANGE,
            CHANNEL_PRESSURE,
            PITCH_BEND,
            SYSTEM_EXCLUSIVE,
            META_EVENT,
        ]:
            assert status & 0x80 == 0x80, f"{hex(status)} should have high bit set"


class TestMIDIVariableLengthQuantity:
    """Test MIDI variable-length quantity encoding/decoding."""

    def encode_vlq(self, value):
        """Encode a value as MIDI variable-length quantity."""
        result = []
        result.append(value & 0x7F)
        value >>= 7

        while value:
            result.append((value & 0x7F) | 0x80)
            value >>= 7

        return bytes(reversed(result))

    def decode_vlq(self, data):
        """Decode a MIDI variable-length quantity."""
        value = 0
        for i, byte in enumerate(data):
            value = (value << 7) | (byte & 0x7F)
            if not (byte & 0x80):
                return value, i + 1
        raise ValueError("Incomplete VLQ")

    def test_vlq_single_byte(self):
        """Test VLQ encoding for values 0-127 (single byte)."""
        for value in [0, 1, 64, 127]:
            encoded = self.encode_vlq(value)
            assert len(encoded) == 1
            assert encoded[0] == value
            decoded, length = self.decode_vlq(encoded)
            assert decoded == value
            assert length == 1

    def test_vlq_two_bytes(self):
        """Test VLQ encoding for values 128-16383 (two bytes)."""
        test_values = [128, 255, 1000, 16383]
        for value in test_values:
            encoded = self.encode_vlq(value)
            assert len(encoded) == 2
            assert encoded[0] & 0x80 == 0x80  # Continuation bit set
            assert encoded[1] & 0x80 == 0x00  # Last byte, no continuation

            decoded, length = self.decode_vlq(encoded)
            assert decoded == value
            assert length == 2

    def test_vlq_three_bytes(self):
        """Test VLQ encoding for larger values."""
        value = 100000
        encoded = self.encode_vlq(value)
        assert len(encoded) == 3

        decoded, _ = self.decode_vlq(encoded)
        assert decoded == value

    def test_vlq_known_values(self):
        """Test VLQ against known encodings from MIDI spec."""
        # From MIDI spec examples
        test_cases = [
            (0x00, bytes([0x00])),
            (0x7F, bytes([0x7F])),
            (0x80, bytes([0x81, 0x00])),
            (0x2000, bytes([0xC0, 0x00])),
            (0x3FFF, bytes([0xFF, 0x7F])),
            (0x4000, bytes([0x81, 0x80, 0x00])),
        ]

        for value, expected in test_cases:
            encoded = self.encode_vlq(value)
            assert encoded == expected, f"VLQ({value}) = {encoded.hex()}, expected {expected.hex()}"


class TestMIDIMetaEvents:
    """Test MIDI meta event types."""

    def test_meta_event_types(self):
        """Test common meta event type codes."""
        META_SEQUENCE_NUMBER = 0x00
        META_TEXT = 0x01
        META_COPYRIGHT = 0x02
        META_TRACK_NAME = 0x03
        META_INSTRUMENT = 0x04
        META_LYRIC = 0x05
        META_MARKER = 0x06
        META_CUE_POINT = 0x07
        META_CHANNEL_PREFIX = 0x20
        META_END_OF_TRACK = 0x2F
        META_SET_TEMPO = 0x51
        META_SMPTE_OFFSET = 0x54
        META_TIME_SIGNATURE = 0x58
        META_KEY_SIGNATURE = 0x59
        META_SEQUENCER_SPECIFIC = 0x7F

        # Text events are 0x01-0x0F
        text_events = [
            META_TEXT,
            META_COPYRIGHT,
            META_TRACK_NAME,
            META_INSTRUMENT,
            META_LYRIC,
            META_MARKER,
            META_CUE_POINT,
        ]
        for event in text_events:
            assert 0x01 <= event <= 0x0F

    def test_karaoke_text_event(self):
        """Test that lyrics use the LYRIC meta event type."""
        META_LYRIC = 0x05
        assert META_LYRIC == 5

        # Karaoke files may also use TEXT events
        META_TEXT = 0x01
        assert META_TEXT == 1


class TestMIDITiming:
    """Test MIDI timing calculations."""

    def test_ticks_to_ms_conversion(self):
        """Test converting MIDI ticks to milliseconds."""
        # Standard tempo: 120 BPM = 500000 microseconds per beat
        tempo_us = 500000
        ticks_per_beat = 480  # Common PPQN value

        def ticks_to_ms(ticks, tempo_us, ppqn):
            """Convert MIDI ticks to milliseconds."""
            us_per_tick = tempo_us / ppqn
            return (ticks * us_per_tick) / 1000

        # One beat at 480 PPQN, 120 BPM should be 500ms
        ms = ticks_to_ms(480, tempo_us, ticks_per_beat)
        assert abs(ms - 500.0) < 0.01

        # Half beat should be 250ms
        ms = ticks_to_ms(240, tempo_us, ticks_per_beat)
        assert abs(ms - 250.0) < 0.01

    def test_tempo_to_bpm(self):
        """Test converting MIDI tempo to BPM."""

        def tempo_to_bpm(tempo_us):
            """Convert microseconds per beat to BPM."""
            return 60000000.0 / tempo_us

        # Standard tempos
        assert abs(tempo_to_bpm(500000) - 120.0) < 0.01
        assert abs(tempo_to_bpm(600000) - 100.0) < 0.01
        assert abs(tempo_to_bpm(400000) - 150.0) < 0.01

    def test_bpm_to_tempo(self):
        """Test converting BPM to MIDI tempo."""

        def bpm_to_tempo(bpm):
            """Convert BPM to microseconds per beat."""
            return int(60000000.0 / bpm)

        assert bpm_to_tempo(120) == 500000
        assert bpm_to_tempo(100) == 600000
        assert bpm_to_tempo(60) == 1000000


class TestKARFileStructure:
    """Test KAR (Karaoke) file specific structures."""

    def test_kar_is_midi_type_1(self):
        """KAR files are typically MIDI Type 1 (multi-track)."""
        # MIDI Type 1 allows multiple tracks with lyrics in separate track
        MIDI_TYPE_1 = 1
        assert MIDI_TYPE_1 == 1

    def test_kar_lyric_markers(self):
        """Test common KAR lyric marker characters."""
        # Common conventions in KAR files:
        # '/' = line break
        # '\\' = paragraph break
        # '@' prefix = karaoke info (@K = karaoke type, @V = version)

        line_break = "/"
        paragraph_break = "\\"
        info_prefix = "@"

        test_lyric = "Hello /World\\New verse"
        assert line_break in test_lyric
        assert paragraph_break in test_lyric

    def test_kar_text_encoding(self):
        """Test KAR text encoding handling."""
        # KAR files often use various encodings
        encodings_to_test = ["cp1252", "iso-8859-1", "utf-8"]

        test_text = "Héllo Wörld"

        for encoding in encodings_to_test:
            try:
                encoded = test_text.encode(encoding)
                decoded = encoded.decode(encoding)
                assert decoded == test_text
            except UnicodeEncodeError:
                # Some characters may not be encodable in all encodings
                pass


class TestMIDIByteParsing:
    """Test MIDI byte parsing utilities."""

    def test_parse_big_endian_16(self):
        """Test parsing big-endian 16-bit values."""
        data = bytes([0x01, 0xE0])  # 480 in big-endian

        value = struct.unpack(">H", data)[0]
        assert value == 480

    def test_parse_big_endian_32(self):
        """Test parsing big-endian 32-bit values."""
        data = bytes([0x00, 0x07, 0xA1, 0x20])  # 500000 in big-endian

        value = struct.unpack(">I", data)[0]
        assert value == 500000

    def test_parse_midi_header(self):
        """Test parsing a MIDI file header."""
        # Construct a valid MIDI header
        header = b"MThd"  # Chunk ID
        header += struct.pack(">I", 6)  # Chunk length
        header += struct.pack(">H", 1)  # Format type (1 = multi-track)
        header += struct.pack(">H", 2)  # Number of tracks
        header += struct.pack(">H", 480)  # Ticks per beat

        # Parse it
        assert header[:4] == b"MThd"
        length = struct.unpack(">I", header[4:8])[0]
        assert length == 6

        format_type = struct.unpack(">H", header[8:10])[0]
        num_tracks = struct.unpack(">H", header[10:12])[0]
        division = struct.unpack(">H", header[12:14])[0]

        assert format_type == 1
        assert num_tracks == 2
        assert division == 480
