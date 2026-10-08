"""Tests for pykaraoke.lrc — the pure LRC lyrics parser."""

from pykaraoke.lrc import parse_elrc, parse_lrc, parse_offset


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
        assert parsed["lyrics"] == [
            {"ms": 2000, "text": "only here", "type": 0, "line": 0}
        ]

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
        assert parsed["lyrics"] == [
            {"ms": 1000, "text": "hi <foo> there", "type": 0, "line": 0}
        ]


class TestParseElrc:
    """Word-level timing from a companion .elrc file."""

    @staticmethod
    def _words(lyrics):
        return [(s["ms"], s["text"]) for s in lyrics]

    def test_words_align_to_their_line(self):
        parsed = parse_lrc(
            "[00:01.00]Hello brave new world\n[00:05.00]Second line here\n"
        )
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
        merged = parse_elrc(
            "[00:01.10]gamma\n[00:01.20]alpha\n[00:01.60]beta\n", parsed["lyrics"]
        )
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
        merged = parse_elrc(
            "[00:10.20]alpha\n[00:10.60]beta\n", parsed["lyrics"], offset_ms=offset
        )
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
            "[00:09.00]Repeat chorus line\n"
            "[00:09.40]Repeat\n[00:10.10]chorus\n[00:10.60]line\n",
            parsed["lyrics"],
        )
        assert [(s["line"], s["ms"], s["text"]) for s in merged] == [
            (0, 9400, "Repeat"),
            (0, 10100, "chorus"),
            (0, 10600, "line"),
        ]
