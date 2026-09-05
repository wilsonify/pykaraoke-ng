"""QA tests for the LRC parser (standard + enhanced), fixture-based.

Covers the audit checklist: metadata tags, [offset:] ±, timestamp
variants, malformed input, unicode, ordering, and long files.
"""

import os
import time

import pytest

from pykaraoke.lrc import parse_lrc

FIXTURES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures", "lrc"
)


def _read(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Metadata tags
# ---------------------------------------------------------------------------


class TestMetadataTags:
    def test_standard_tags(self):
        parsed = parse_lrc(
            "[ti:Song]\n[ar:Artist]\n[al:Album]\n[au:Composer]\n[lr:Lyricist]\n"
            "[by:Creator]\n[re:Editor]\n[ve:1.0]\n[length:03:45]\n[00:01.00]go\n"
        )
        assert parsed["meta"] == {
            "ti": "Song",
            "ar": "Artist",
            "al": "Album",
            "au": "Composer",
            "lr": "Lyricist",
            "by": "Creator",
            "re": "Editor",
            "ve": "1.0",
            "length": "03:45",
        }

    def test_unknown_custom_tags_are_captured(self):
        parsed = parse_lrc("[custom-tag:some value]\n[00:01.00]go\n")
        assert parsed["meta"]["custom-tag"] == "some value"

    def test_empty_meta_value(self):
        parsed = parse_lrc("[ti:]\n[00:01.00]go\n")
        assert parsed["meta"]["ti"] == ""

    def test_timestamps_are_not_meta(self):
        # [00:12.34] must parse as a timestamp, not [key=00 value=12.34].
        parsed = parse_lrc("[00:12.34]go\n")
        assert "00" not in parsed["meta"]
        assert parsed["lyrics"][0]["ms"] == 12340


# ---------------------------------------------------------------------------
# [offset:] handling
# ---------------------------------------------------------------------------


class TestOffset:
    def test_positive_offset_shifts_earlier(self):
        # Per the LRC spec: a positive offset makes lyrics appear sooner.
        parsed = parse_lrc("[offset:+500]\n[00:10.00]a\n[00:12.00]b\n")
        assert [s["ms"] for s in parsed["lyrics"]] == [9500, 11500]

    def test_negative_offset_shifts_later(self):
        parsed = parse_lrc("[offset:-500]\n[00:10.00]a\n[00:12.00]b\n")
        assert [s["ms"] for s in parsed["lyrics"]] == [10500, 12500]

    def test_offset_clamps_at_zero(self):
        parsed = parse_lrc("[offset:+2000]\n[00:01.00]early\n[00:12.00]later\n")
        assert [s["ms"] for s in parsed["lyrics"]] == [0, 10000]

    def test_offset_applies_to_word_tags(self):
        parsed = parse_lrc("[offset:+500]\n[00:10.00]a <00:10.50> b\n")
        assert [s["ms"] for s in parsed["lyrics"]] == [9500, 10000]

    def test_malformed_offset_is_ignored(self):
        parsed = parse_lrc("[offset:abc]\n[00:10.00]a\n")
        assert parsed["lyrics"][0]["ms"] == 10000

    def test_offset_without_sign(self):
        parsed = parse_lrc("[offset:500]\n[00:10.00]a\n")
        assert parsed["lyrics"][0]["ms"] == 9500


# ---------------------------------------------------------------------------
# Timestamp variants and precision
# ---------------------------------------------------------------------------


class TestTimestampVariants:
    @pytest.mark.parametrize(
        ("line", "expected_ms"),
        [
            ("[00:12.34]", 12340),      # standard
            ("[00:12.345]", 12345),     # milliseconds
            ("[00:12.3]", 12300),       # tenths
            ("[0:12.34]", 12340),       # non-padded minutes
            ("[00:5.34]", 5340),        # non-padded seconds
            ("[00:00.999]", 999),       # precision
            ("[1:02.05]", 62050),       # mixed padding
        ],
    )
    def test_timestamp_forms(self, line, expected_ms):
        parsed = parse_lrc(f"{line}text\n")
        assert parsed["lyrics"][0]["ms"] == expected_ms

    def test_duplicate_timestamps_kept(self):
        parsed = parse_lrc("[00:10.00]a\n[00:10.00]b\n")
        assert [(s["ms"], s["text"]) for s in parsed["lyrics"]] == [
            (10000, "a"),
            (10000, "b"),
        ]

    def test_out_of_order_lines_keep_file_order(self):
        parsed = parse_lrc("[00:30.00]late\n[00:10.00]early\n")
        # Parser output is deterministic (file order); the UI sorts lines.
        assert [s["text"] for s in parsed["lyrics"]] == ["late", "early"]
        assert [s["ms"] for s in parsed["lyrics"]] == [30000, 10000]

    def test_out_of_order_words_keep_file_order(self):
        parsed = parse_lrc("[00:10.00]a <00:12.00> c <00:11.00> b\n")
        assert [(s["ms"], s["text"]) for s in parsed["lyrics"]] == [
            (10000, "a"),
            (12000, "c"),
            (11000, "b"),
        ]

    def test_length_with_fraction(self):
        parsed = parse_lrc("[length:03:45.50]\n[00:01.00]a\n")
        assert parsed["duration_ms"] == 225_500

    def test_length_with_space_and_single_digit_minutes(self):
        parsed = parse_lrc("[length: 2:23]\n[00:01.00]a\n")
        assert parsed["duration_ms"] == 143_000


# ---------------------------------------------------------------------------
# Malformed / unusual input
# ---------------------------------------------------------------------------


class TestMalformedInput:
    def test_untimed_lines_ignored(self):
        parsed = parse_lrc("plain lyric line without time\n[00:01.00]real\n")
        assert [s["text"] for s in parsed["lyrics"]] == ["real"]

    def test_blank_lines_and_comments_ignored(self):
        parsed = parse_lrc("\n\n# a comment\n[00:01.00]a\n\n[00:02.00]b\n")
        assert [s["text"] for s in parsed["lyrics"]] == ["a", "b"]

    def test_malformed_lines_skipped_but_valid_lines_kept(self):
        parsed = parse_lrc(_read("malformed.lrc"))
        texts = [s["text"] for s in parsed["lyrics"]]
        assert "Valid line after garbage" in texts
        assert "extra bracket group stripped" in texts
        assert all(s["ms"] >= 0 for s in parsed["lyrics"])

    def test_unicode_lyrics(self):
        parsed = parse_lrc("[00:01.00]Café — 日本語 🎤\n")
        assert parsed["lyrics"][0]["text"] == "Café — 日本語 🎤"

    def test_crlf_and_mixed_line_endings(self):
        parsed = parse_lrc("[00:01.00]a\r\n[00:02.00]b\n[00:03.00]c\r\n")
        assert [s["text"] for s in parsed["lyrics"]] == ["a", "b", "c"]

    def test_bom_prefix(self):
        parsed = parse_lrc("\ufeff[ti:T]\n[00:01.00]a\n")
        assert parsed["meta"]["ti"] == "T"


# ---------------------------------------------------------------------------
# Fixtures (realistic files)
# ---------------------------------------------------------------------------


class TestFixtures:
    def test_standard_fixture(self):
        parsed = parse_lrc(_read("standard.lrc"))
        assert parsed["meta"]["ti"] == "Let's Twist Again"
        assert parsed["meta"]["ar"] == "Chubby Checker"
        assert parsed["meta"]["by"] == "lrc-maker"
        assert parsed["duration_ms"] == 143_000  # [length: 2:23]

        by_ms = {s["text"]: s["ms"] for s in parsed["lyrics"]}
        assert by_ms["Naku Penda Piya-Naku Taka Piya-Mpenziwe"] == 12000
        assert by_ms["Some more lyrics ..."] == 15300
        assert by_ms["Non-padded fraction line"] == 18500
        assert by_ms["Non-padded minute"] == 20000
        assert by_ms["Café — 日本語 🎤"] == 90000
        assert by_ms["Out of order line (kept in file order)"] == 60000
        # Repeated chorus line appears at both timestamps.
        chorus = [s for s in parsed["lyrics"] if s["text"].startswith("Repeating")]
        assert [s["ms"] for s in chorus] == [21100, 45100]

    def test_enhanced_fixture(self):
        parsed = parse_lrc(_read("enhanced.lrc"))
        # First line: leading space segment dropped, words timed per tag.
        first = parsed["lyrics"][:8]
        assert [(s["ms"], s["text"]) for s in first] == [
            (40, "When"),
            (160, "the"),
            (820, "truth"),
            (1290, "is"),
            (1630, "found"),
            (3090, "to"),
            (3370, "be"),
            (5920, "lies"),
        ]
        assert len(parsed["lyrics"]) == 21  # 8 + 7 + 6 words
        assert parsed["meta"]["lr"] == "Lyricists of that song"
        assert parsed["duration_ms"] == 178_000  # [length: 2:58]

    def test_offset_fixtures(self):
        pos = parse_lrc(_read("offset-positive.lrc"))
        neg = parse_lrc(_read("offset-negative.lrc"))
        assert [s["ms"] for s in pos["lyrics"]] == [9500, 11500]
        assert [s["ms"] for s in neg["lyrics"]] == [10500, 12500]


# ---------------------------------------------------------------------------
# Scale
# ---------------------------------------------------------------------------


class TestScale:
    def test_long_file(self):
        lines = ["[ti:Long Song]", "[ar:Long Artist]"]
        for i in range(2000):
            minutes = i // 60
            seconds = i % 60
            lines.append(f"[{minutes:02d}:{seconds:02d}.00]Lyric line {i}")
        start = time.monotonic()
        parsed = parse_lrc("\n".join(lines))
        elapsed = time.monotonic() - start
        assert parsed is not None
        assert len(parsed["lyrics"]) == 2000
        assert elapsed < 1.0  # generous bound; typically < 20 ms
