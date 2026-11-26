"""Tests for pykaraoke.lrc — the pure LRC lyrics parser."""

import pytest

from pykaraoke.lrc import parse_elrc, parse_elrc_lines, parse_lrc, parse_offset


class TestParseLrc:
    def test_basic_timed_line(self):
        parsed = parse_lrc("[00:12.34]Hello world\n")
        assert parsed is not None
        assert parsed["lyrics"] == [{"ms": 12340, "text": "Hello world", "type": 0, "line": 0}]

    def test_millisecond_fraction(self):
        parsed = parse_lrc("[01:02.345]three digits\n")
        assert parsed["lyrics"][0]["ms"] == 62_345

    def test_hundredth_fraction(self):
        parsed = parse_lrc("[00:05.50]fifty hundredths\n")
        assert parsed["lyrics"][0]["ms"] == 5_500

    def test_meta_tags(self):
        parsed = parse_lrc(
            "[ti:Inside Out]\n[ar:Tom and the Back Roads]\n[al:Album]\n[length:03:45]\n[00:10.00]go\n"
        )
        assert parsed["meta"] == {
            "ti": "Inside Out",
            "ar": "Tom and the Back Roads",
            "al": "Album",
            "length": "03:45",
        }
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

    # ------------------------------------------------------------------
    # Enhanced LRC: word-level <mm:ss.xx> tags
    # ------------------------------------------------------------------

    def test_word_level_timestamps(self):
        parsed = parse_lrc("[00:12.00]Word <00:12.50> by <00:12.80> word\n")
        assert parsed["lyrics"] == [
            {"ms": 12000, "text": "Word", "type": 0, "line": 0},
            {"ms": 12500, "text": "by", "type": 0, "line": 0},
            {"ms": 12800, "text": "word", "type": 0, "line": 0},
        ]

    def test_word_tags_use_millisecond_fraction(self):
        parsed = parse_lrc("[00:01.000]a <00:01.250> b\n")
        assert [s["ms"] for s in parsed["lyrics"]] == [1000, 1250]

    def test_consecutive_word_tags_skip_empty_text(self):
        parsed = parse_lrc("[00:01.00]<00:01.50><00:02.00>only here\n")
        assert parsed["lyrics"] == [{"ms": 2000, "text": "only here", "type": 0, "line": 0}]

    def test_repeated_line_timestamps_expand_words(self):
        # A repeated line is emitted once per line timestamp; word tags
        # keep their absolute times.
        parsed = parse_lrc("[00:01.00][00:10.00]a <00:01.50> b\n")
        assert [(s["ms"], s["text"]) for s in parsed["lyrics"]] == [
            (1000, "a"),
            (1500, "b"),
            (10000, "a"),
            (1500, "b"),
        ]

    def test_duration_includes_word_times(self):
        parsed = parse_lrc("[00:10.00]a <00:12.00> b <00:14.00> c\n")
        assert parsed["duration_ms"] == 14000

    def test_malformed_tag_stays_literal(self):
        # <foo> is not a valid word tag; the line falls back to line timing.
        parsed = parse_lrc("[00:01.00]hi <foo> there\n")
        assert parsed["lyrics"] == [{"ms": 1000, "text": "hi <foo> there", "type": 0, "line": 0}]


class TestParseElrc:
    """Word-level timing from a companion .elrc file."""

    @staticmethod
    def _words(lyrics):
        return [(s["ms"], s["text"]) for s in lyrics]

    def test_words_align_to_their_line(self):
        parsed = parse_lrc("[00:01.00]Hello brave new world\n[00:05.00]Second line here\n")
        elrc = (
            "[00:01.00]Hello brave new world\n"  # line header: whole line
            "[00:01.20]Hello\n[00:01.70]brave\n[00:02.20]new\n[00:02.90]world\n"
            "[00:05.00]Second line here\n"  # header for line 2
            "[00:05.30]Second\n[00:05.80]line\n[00:06.40]here\n"
        )
        merged = parse_elrc(elrc, parsed["lyrics"])
        assert [(s["line"], s["ms"], s["text"]) for s in merged] == [
            (0, 1200, "Hello"),
            (0, 1700, "brave"),
            (0, 2200, "new"),
            (0, 2900, "world"),
            (1, 5300, "Second"),
            (1, 5800, "line"),
            (1, 6400, "here"),
        ]

    def test_stray_entry_is_skipped(self):
        # "gamma" is not the next letters of the line: timing never shifts
        # onto the wrong word, and the rest still aligns.
        parsed = parse_lrc("[00:01.00]alpha beta\n")
        merged = parse_elrc("[00:01.10]gamma\n[00:01.20]alpha\n[00:01.60]beta\n", parsed["lyrics"])
        assert self._words(merged) == [(1200, "alpha"), (1600, "beta")]

    def test_untimed_line_keeps_its_own_syllables(self):
        parsed = parse_lrc("[00:01.00]one two\n[00:05.00]three four\n")
        merged = parse_elrc("[00:01.20]one\n[00:01.70]two\n", parsed["lyrics"])
        assert merged[2:] == [{"ms": 5000, "text": "three four", "type": 0, "line": 1}]

    def test_no_word_matches_returns_none(self):
        parsed = parse_lrc("[00:01.00]one two\n")
        assert parse_elrc("[00:01.10]zzz\n", parsed["lyrics"]) is None
        assert parse_elrc("[00:01.00]one two\n", parsed["lyrics"]) is None  # header only

    def test_empty_inputs_return_none(self):
        parsed = parse_lrc("[00:01.00]one two\n")
        assert parse_elrc("", parsed["lyrics"]) is None
        assert parse_elrc("no timestamps", parsed["lyrics"]) is None
        assert parse_elrc("[00:01.10]one\n", []) is None
        assert parse_elrc(None, parsed["lyrics"]) is None

    def test_offset_is_applied_to_word_times(self):
        # [offset:500] already shifted the line to 9500 ms; the .elrc is
        # shifted identically so both stay aligned.
        parsed = parse_lrc("[offset:500]\n[00:10.00]alpha beta\n")
        offset = parse_offset(parsed["meta"])
        merged = parse_elrc("[00:10.20]alpha\n[00:10.60]beta\n", parsed["lyrics"], offset_ms=offset)
        assert self._words(merged) == [(9700, "alpha"), (10100, "beta")]

    def test_unmatched_token_keeps_its_text_and_time_order(self):
        # A token the .elrc never mentions must not vanish from the line,
        # and times stay non-decreasing for the renderer's lit-walk.
        parsed = parse_lrc("[00:01.00]one two three\n")
        merged = parse_elrc("[00:01.10]one\n[00:01.80]three\n", parsed["lyrics"])
        assert [s["text"] for s in merged] == ["one", "two", "three"]
        times = [s["ms"] for s in merged]
        assert times == sorted(times)

    def test_word_before_line_start_is_clamped_to_it(self):
        parsed = parse_lrc("[00:01.00]one two\n")
        merged = parse_elrc("[00:00.50]one\n[00:01.50]two\n", parsed["lyrics"])
        assert self._words(merged) == [(1000, "one"), (1500, "two")]

    def test_non_latin_words_match(self):
        # Letter matching keeps unicode letters, not just [a-z0-9].
        parsed = parse_lrc("[00:01.00]Привет мир\n")
        merged = parse_elrc("[00:01.10]Привет\n[00:01.60]мир\n", parsed["lyrics"])
        assert self._words(merged) == [(1100, "Привет"), (1600, "мир")]

    def test_punctuation_and_case_are_ignored(self):
        parsed = parse_lrc("[00:01.00]Don't stop, me now\n")
        merged = parse_elrc("[00:01.20]don t\n[00:01.70]stop\n", parsed["lyrics"])
        assert [s["text"] for s in merged] == ["Don't", "stop,", "me", "now"]
        assert self._words(merged)[0] == (1200, "Don't")

    def test_repeated_line_collapses_to_one_copy(self):
        # The chorus is stamped twice; the word timing keeps the first pass.
        parsed = parse_lrc("[00:09.00][00:15.00]Repeat chorus line\n")
        merged = parse_elrc(
            "[00:09.00]Repeat chorus line\n[00:09.40]Repeat\n[00:10.10]chorus\n[00:10.60]line\n",
            parsed["lyrics"],
        )
        assert [(s["line"], s["ms"], s["text"]) for s in merged] == [
            (0, 9400, "Repeat"),
            (0, 10100, "chorus"),
            (0, 10600, "line"),
        ]


class TestParseDuet:
    """Duet part tags ([00:01.00][a]…) and [pa:]/[pb:] singer names."""

    @pytest.mark.parametrize(
        ("tag", "expected"),
        [
            ("[a]", "a"),
            ("[A]", "a"),
            ("[b]", "b"),
            ("[ab]", "ab"),
            ("[ba]", "ab"),  # the mirror of a shared line
            ("[AB]", "ab"),
        ],
    )
    def test_part_tag_variants(self, tag, expected):
        parsed = parse_lrc(f"[00:01.00]{tag}line text\n")
        assert parsed["lyrics"][0]["part"] == expected
        assert parsed["lyrics"][0]["text"] == "line text"

    def test_part_per_line(self):
        parsed = parse_lrc(
            "[00:01.00][a]first\n[00:05.00][b]second\n[00:09.00][ab]shared\n[00:13.00]solo\n"
        )
        assert [(s["line"], s.get("part")) for s in parsed["lyrics"]] == [
            (0, "a"),
            (1, "b"),
            (2, "ab"),
            (3, None),
        ]

    def test_solo_song_payload_has_no_duet_keys(self):
        parsed = parse_lrc("[00:01.00]hello\n[00:05.00]world\n")
        assert parsed["lyrics"] == [
            {"ms": 1000, "text": "hello", "type": 0, "line": 0},
            {"ms": 5000, "text": "world", "type": 0, "line": 1},
        ]
        assert "parts" not in parsed

    def test_unknown_bracket_tag_is_not_a_part(self):
        # [abc] is not a duet id: stripped like any other bracket group.
        parsed = parse_lrc("[00:01.00][abc]hi\n")
        assert parsed["lyrics"][0]["text"] == "hi"
        assert "part" not in parsed["lyrics"][0]

    def test_part_tag_must_follow_the_timestamps(self):
        # A tag before the timestamps leaves no time to parse: unusable.
        assert parse_lrc("[a][00:01.00]hello\n") is None

    def test_part_applies_to_every_word_of_an_enhanced_line(self):
        parsed = parse_lrc("[00:01.00][b]one <00:01.50>two <00:02.00>three\n")
        assert [s["part"] for s in parsed["lyrics"]] == ["b", "b", "b"]

    def test_part_applies_to_every_repeated_timestamp(self):
        parsed = parse_lrc("[00:01.00][00:10.00][ab]chorus\n")
        assert [s["part"] for s in parsed["lyrics"]] == ["ab", "ab"]

    def test_offset_shifts_duet_lines_too(self):
        parsed = parse_lrc("[offset:+500]\n[00:10.00][a]line\n")
        assert parsed["lyrics"][0] == {
            "ms": 9500,
            "text": "line",
            "type": 0,
            "line": 0,
            "part": "a",
        }

    def test_singer_names_from_meta(self):
        parsed = parse_lrc("[pa:Alice]\n[pb:Bob]\n[00:01.00][a]hi\n")
        assert parsed["parts"] == {"a": "Alice", "b": "Bob"}
        assert parsed["meta"]["pa"] == "Alice"

    def test_only_one_singer_named(self):
        parsed = parse_lrc("[pb:Bob]\n[00:01.00]hi\n")
        assert parsed["parts"] == {"b": "Bob"}

    def test_empty_or_missing_names_are_not_exposed(self):
        assert "parts" not in parse_lrc("[pa:]\n[pb:]\n[00:01.00]hi\n")
        assert "parts" not in parse_lrc("[00:01.00][b]hi\n")

    def test_elrc_merge_keeps_part_tags(self):
        parsed = parse_lrc("[pa:Alice]\n[00:01.00][a]Hello world\n[00:05.00][b]Second line\n")
        merged = parse_elrc(
            "[00:01.00]Hello world\n[00:01.20]Hello\n[00:01.70]world\n"
            "[00:05.00]Second line\n[00:05.30]Second\n[00:05.80]line\n",
            parsed["lyrics"],
        )
        assert [(s["line"], s["text"], s.get("part")) for s in merged] == [
            (0, "Hello", "a"),
            (0, "world", "a"),
            (1, "Second", "b"),
            (1, "line", "b"),
        ]
        assert parsed["parts"] == {"a": "Alice"}


class TestTimestampVariants:
    """Timestamps people actually write: the fraction is optional, and either
    `.` or `:` may introduce it."""

    @pytest.mark.parametrize("tag", ["[00:12]", "[00:12.00]", "[00:12:00]"])
    def test_equivalent_forms(self, tag):
        parsed = parse_lrc(f"{tag}Hello\n")
        assert [(e["ms"], e["text"]) for e in parsed["lyrics"]] == [(12000, "Hello")]

    def test_fraction_digits_scale(self):
        assert parse_lrc("[00:01.5]a\n")["lyrics"][0]["ms"] == 1500
        assert parse_lrc("[00:01.50]a\n")["lyrics"][0]["ms"] == 1500
        assert parse_lrc("[00:01.500]a\n")["lyrics"][0]["ms"] == 1500

    def test_three_digit_minutes(self):
        parsed = parse_lrc("[123:45.67]a\n")
        assert parsed["lyrics"][0]["ms"] == (123 * 60 + 45) * 1000 + 670

    def test_word_tags_accept_the_same_forms(self):
        parsed = parse_lrc("[00:01]One <00:02>two <00:03:50>three\n")
        assert [e["ms"] for e in parsed["lyrics"]] == [1000, 2000, 3500]

    def test_elrc_accepts_the_same_forms(self):
        parsed = parse_lrc("[00:01.00]Hello world\n")
        merged = parse_elrc("[00:01]Hello\n[00:01.5] world\n", parsed["lyrics"])
        assert [e["text"] for e in merged] == ["Hello", "world"]

    def test_a_whole_second_file_no_longer_fails(self):
        parsed = parse_lrc("[00:01]One\n[00:05]Two\n")
        assert parsed is not None
        assert [e["text"] for e in parsed["lyrics"]] == ["One", "Two"]


class TestParseWarnings:
    """A line that looks timed but cannot be read is reported, not swallowed."""

    def test_malformed_line_is_skipped_and_reported(self):
        parsed = parse_lrc("[00:01.00]Good\n[00:6x.00]Bad\n[00:03.00]Also good\n")
        assert [e["text"] for e in parsed["lyrics"]] == ["Good", "Also good"]
        assert len(parsed["warnings"]) == 1
        assert parsed["warnings"][0] == {
            "kind": "skipped-line",
            "line": 2,
            "text": "[00:6x.00]Bad",
        }

    def test_clean_file_has_no_warnings_key(self):
        assert "warnings" not in parse_lrc("[00:01.00]Good\n")

    def test_clear_line_markers_are_not_warnings(self):
        assert "warnings" not in parse_lrc("[00:05.00]\n[00:12.00]Good\n")

    def test_unmatched_elrc_entry_is_counted(self):
        parsed = parse_lrc("[00:01.00]Hello brave world\n")
        warnings = []
        merged = parse_elrc(
            "[00:01.00]Hello brave world\n[00:01.10]Hello\n[00:01.90]zebra\n",
            parsed["lyrics"],
            warnings=warnings,
        )
        assert [e["text"] for e in merged] == ["Hello", "brave", "world"]
        assert warnings == [{"kind": "unmatched-elrc", "line": 0, "count": 1}]

    def test_a_header_is_not_a_warning(self):
        parsed = parse_lrc("[00:01.00]Hello world\n")
        warnings = []
        parse_elrc(
            "[00:01.00]Hello world\n[00:01.10]Hello\n[00:01.90]world\n",
            parsed["lyrics"],
            warnings=warnings,
        )
        assert warnings == []


class TestElrcLineInference:
    """The chord-vault dialect: a header entry, then its words."""

    TEXT = (
        "[ar:Olivia Rodrigo]\n"
        "[length:0:20]\n"
        "[00:11.560]I got my license last week\n"
        "[00:11.560] I\n"
        "[00:12.440] got\n"
        "[00:13.320] my\n"
        "[00:14.720] license\n"
        "[00:15.320] last\n"
        "[00:15.740] week\n"
    )

    def test_lines_come_from_headers(self):
        parsed = parse_elrc_lines(self.TEXT)
        assert parsed["inferred"] is True
        assert [(e["text"], e["line"]) for e in parsed["lyrics"]] == [
            ("I", 0),
            ("got", 0),
            ("my", 0),
            ("license", 0),
            ("last", 0),
            ("week", 0),
        ]
        assert parsed["lyrics"][0]["ms"] == 11560
        assert parsed["meta"]["ar"] == "Olivia Rodrigo"
        assert parsed["duration_ms"] == 20000

    def test_a_line_without_words_stays_one_line(self):
        parsed = parse_elrc_lines("[00:01.00]Solo line here\n[00:05.00]Next line\n")
        assert [(e["text"], e["line"]) for e in parsed["lyrics"]] == [
            ("Solo line here", 0),
            ("Next line", 1),
        ]

    def test_a_header_needs_its_words_to_match(self):
        # "Hello there" is not spelled by "Goodbye" + "now", so no header.
        parsed = parse_elrc_lines("[00:01.00]Hello there\n[00:01.20]Goodbye\n[00:01.40]now\n")
        assert [(e["text"], e["line"]) for e in parsed["lyrics"]] == [
            ("Hello there", 0),
            ("Goodbye", 1),
            ("now", 2),
        ]

    def test_offset_is_applied(self):
        parsed = parse_elrc_lines("[offset:+500]\n[00:01.00]Solo line\n")
        assert parsed["lyrics"][0]["ms"] == 500

    def test_text_without_lines_is_none(self):
        assert parse_elrc_lines("") is None
        assert parse_elrc_lines("[ar:Only metadata]\n") is None
