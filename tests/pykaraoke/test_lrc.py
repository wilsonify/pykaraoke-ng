"""Tests for pykaraoke.lrc — the pure LRC lyrics parser."""

from pykaraoke.lrc import parse_lrc


class TestParseLrc:
    def test_basic_timed_line(self):
        parsed = parse_lrc("[00:12.34]Hello world\n")
        assert parsed is not None
        assert parsed["lyrics"] == [
            {"ms": 12340, "text": "Hello world", "type": 0, "line": 0}
        ]

    def test_millisecond_fraction(self):
        parsed = parse_lrc("[01:02.345]three digits\n")
        assert parsed["lyrics"][0]["ms"] == 62_345

    def test_hundredth_fraction(self):
        parsed = parse_lrc("[00:05.50]fifty hundredths\n")
        assert parsed["lyrics"][0]["ms"] == 5_500

    def test_meta_tags(self):
        parsed = parse_lrc("[ti:Inside Out]\n[ar:Tom and the Back Roads]\n[al:Album]\n[length:03:45]\n[00:10.00]go\n")
        assert parsed["meta"] == {"ti": "Inside Out", "ar": "Tom and the Back Roads", "al": "Album", "length": "03:45"}
        assert parsed["duration_ms"] == 3 * 60_000 + 45_000

    def test_meta_tags_case_insensitive(self):
        parsed = parse_lrc("[Ti:Title]\n[00:10.00]go\n")
        assert parsed["meta"]["ti"] == "Title"

    def test_multiple_timestamps_share_a_line(self):
        parsed = parse_lrc("[00:01.00][00:02.00]la la\n")
        assert parsed["lyrics"] == [
            {"ms": 1000, "text": "la la", "type": 0, "line": 0},
            {"ms": 2000, "text": "la la", "type": 0, "line": 0},
        ]

    def test_sequential_line_numbers(self):
        parsed = parse_lrc("[00:01.00]one\n[00:02.00]two\n[00:03.00]three\n")
        assert [s["line"] for s in parsed["lyrics"]] == [0, 1, 2]

    def test_duration_falls_back_to_last_timestamp(self):
        parsed = parse_lrc("[00:01.00]one\n[02:30.00]two\n")
        assert parsed["duration_ms"] == 150_000

    def test_blank_lines_and_no_timestamps(self):
        assert parse_lrc("") is None
        assert parse_lrc("just some text\nno timestamps\n") is None
        assert parse_lrc("[00:10.00]   \n") is None  # timestamp with empty text

    def test_metadata_only(self):
        assert parse_lrc("[ti:Song]\n[ar:Artist]\n") is None

    def test_crlf_line_endings(self):
        parsed = parse_lrc("[00:01.00]one\r\n[00:02.00]two\r\n")
        assert [s["text"] for s in parsed["lyrics"]] == ["one", "two"]

    def test_extra_tags_before_text(self):
        # A second [mm:ss] tag before the text is stripped.
        parsed = parse_lrc("[00:01.00][00:02.00]  word  \n")
        assert parsed["lyrics"][0]["text"] == "word"
