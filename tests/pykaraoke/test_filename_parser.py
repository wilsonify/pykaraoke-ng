"""Parameterized unit tests for pykaraoke.filename_parser."""

import unicodedata

import pytest

from pykaraoke.filename_parser import FilenameParser, FileNameType, ParsedSong


def _parser(name_type: FileNameType = FileNameType.ARTIST_TITLE) -> FilenameParser:
    return FilenameParser(file_name_type=name_type)


# ===========================================================================
# Space-dash-space pattern tests
# ===========================================================================


class TestSpaceDashPattern:
    @pytest.mark.parametrize(
        "filepath, expected_artist, expected_title",
        [
            ("Artist - Title.mp3", "Artist", "Title"),
            ("John Doe - My Song.mp3", "John Doe", "My Song"),
            ("Artist - Title (Remix).cdg", "Artist", "Title (Remix)"),
            ("Artist - Title - Live.mp3", "Artist", "Title - Live"),
            ("The Beatles - Let It Be - Live.kar", "The Beatles", "Let It Be - Live"),
            ("Sinatra - My Way.kar", "Sinatra", "My Way"),
            ("Artist - Song 2024.cdg", "Artist", "Song 2024"),
            ("Artist - A-B-C Song.cdg", "Artist", "A-B-C Song"),
            ("  Artist   -   Title  .mp3", "Artist", "Title"),
        ],
    )
    def test_space_dash_extraction(self, filepath, expected_artist, expected_title):
        result = _parser().parse(filepath)
        assert result.artist == expected_artist
        assert result.title == expected_title

    def test_directory_dashes_ignored(self):
        result = _parser().parse("/music/rock-band/best-of/Artist - Title.mp3")
        assert result.artist == "Artist"
        assert result.title == "Title"

    def test_windows_path_dashes_ignored(self):
        result = _parser().parse(r"C:\my-music\rock-hits\Queen - Bohemian Rhapsody.cdg")
        assert result.artist == "Queen"
        assert result.title == "Bohemian Rhapsody"

    def test_disc_and_track_empty_for_space_dash(self):
        result = _parser().parse("Artist - Title.mp3")
        assert result.disc == ""
        assert result.track == ""


# ===========================================================================
# Legacy format tests
# ===========================================================================


class TestLegacyDiscTrackArtistTitle:
    parser = _parser(FileNameType.DISC_TRACK_ARTIST_TITLE)

    @pytest.mark.parametrize(
        "filepath, disc, track, artist, title",
        [
            ("SC1234-05-John Doe-My Song.cdg", "SC1234", "05", "John Doe", "My Song"),
            ("SC1234-05-The Rolling Stones-Paint It Black.cdg", "SC1234", "05", "The Rolling Stones", "Paint It Black"),
            ("SC1234-05-Artist-Title-With-Dashes.cdg", "SC1234", "05", "Artist", "Title-With-Dashes"),
        ],
    )
    def test_four_part_parsing(self, filepath, disc, track, artist, title):
        result = self.parser.parse(filepath)
        assert result.disc == disc
        assert result.track == track
        assert result.artist == artist
        assert result.title == title

    def test_fewer_than_four_parts_falls_back_to_title_only(self):
        result = self.parser.parse("OnePart.cdg")
        assert result.title == "OnePart"
        assert result.artist == ""


class TestLegacyDisctTrackArtistTitle:
    parser = _parser(FileNameType.DISCTRACK_ARTIST_TITLE)

    @pytest.mark.parametrize(
        "filepath, disc, artist, title",
        [
            ("SC123405-John Doe-My Song.cdg", "SC123405", "John Doe", "My Song"),
            ("AB9901-Queen-Bohemian Rhapsody.cdg", "AB9901", "Queen", "Bohemian Rhapsody"),
        ],
    )
    def test_three_part_parsing(self, filepath, disc, artist, title):
        result = self.parser.parse(filepath)
        assert result.disc == disc
        assert result.artist == artist
        assert result.title == title


class TestLegacyDiscArtistTitle:
    parser = _parser(FileNameType.DISC_ARTIST_TITLE)

    @pytest.mark.parametrize(
        "filepath, disc, artist, title",
        [
            ("SC1234-John Doe-My Song.cdg", "SC1234", "John Doe", "My Song"),
            ("DISC1-Adele-Hello.kar", "DISC1", "Adele", "Hello"),
        ],
    )
    def test_three_part_parsing(self, filepath, disc, artist, title):
        result = self.parser.parse(filepath)
        assert result.disc == disc
        assert result.artist == artist
        assert result.title == title


class TestLegacyArtistTitle:
    parser = _parser(FileNameType.ARTIST_TITLE)

    @pytest.mark.parametrize(
        "filepath, expected_artist, expected_title",
        [
            ("John Doe-My Song.cdg", "John Doe", "My Song"),
            ("Queen-Bohemian Rhapsody.kar", "Queen", "Bohemian Rhapsody"),
            ("Artist-Title-Extra.cdg", "Artist", "Title-Extra"),
        ],
    )
    def test_two_part_parsing(self, filepath, expected_artist, expected_title):
        result = self.parser.parse(filepath)
        assert result.artist == expected_artist
        assert result.title == expected_title

    def test_single_part_falls_back_to_title_only(self):
        result = self.parser.parse("JustTitle.cdg")
        assert result.title == "JustTitle"
        assert result.artist == ""


# ===========================================================================
# Edge-case / robustness tests
# ===========================================================================


class TestEdgeCases:
    def test_extension_stripped(self):
        result = _parser().parse("Artist - Title.cdg")
        assert ".cdg" not in result.artist
        assert ".cdg" not in result.title

    def test_multiple_extensions_stripped(self):
        result = _parser().parse("Artist - Song.name.cdg")
        assert result.title == "Song.name"

    def test_deep_directory_path_ignored(self):
        result = _parser().parse("/a-b/c-d/e-f/Artist - Title.cdg")
        assert result.artist == "Artist"
        assert result.title == "Title"

    def test_empty_filepath_returns_empty(self):
        result = _parser().parse("")
        assert result.artist == ""
        assert result.title == ""

    def test_no_separator_returns_title_only(self):
        result = _parser().parse("JustATitle.mp3")
        assert result.title == "JustATitle"
        assert result.artist == ""

    def test_unicode_filenames(self):
        result = _parser().parse("Björk - Jóga.cdg")
        assert result.artist == "Björk"
        assert result.title == "Jóga"

    def test_parenthetical_title_preserved(self):
        result = _parser().parse("Artist - Title (feat. Someone).cdg")
        assert result.title == "Title (feat. Someone)"

    def test_numbers_only_title(self):
        result = _parser().parse("Artist - 99 Problems.cdg")
        assert result.artist == "Artist"
        assert result.title == "99 Problems"

    def test_artist_with_internal_dash(self):
        result = _parser().parse("AC-DC - Highway to Hell.cdg")
        assert result.artist == "AC-DC"
        assert result.title == "Highway to Hell"


class TestParseZipPath:
    def test_zip_member_artist_from_directory(self):
        result = _parser().parse_zip_path("Language/Artist/Title.kar")
        assert result.artist == "Artist"
        assert result.title == "Title"

    def test_zip_member_with_separator(self):
        result = _parser().parse_zip_path("Some Dir/Queen - Bohemian Rhapsody.kar")
        assert result.artist == "Queen"
        assert result.title == "Bohemian Rhapsody"


# ===========================================================================
# Disc-track spaced naming mode (file_name_type = 4, issue #14)
# ===========================================================================


class TestDiscTrackSpaced:
    parser = _parser(FileNameType.DISC_TRACK_SPACED)

    @pytest.mark.parametrize(
        "filepath, disc, track, artist, title",
        [
            (
                "CB30055-15 - Switchfoot - Stars.cdg",
                "CB30055",
                "15",
                "Switchfoot",
                "Stars",
            ),
            (
                "CB5056-03-06 - Al Green - Let's Stay Together.cdg",
                "CB5056-03",
                "06",
                "Al Green",
                "Let's Stay Together",
            ),
            (
                "SC3448-03 - All-American Rejects - Dirty Little Secret.cdg",
                "SC3448",
                "03",
                "All-American Rejects",
                "Dirty Little Secret",
            ),
            (
                "SC1-01 - Artist - Title - Radio Edit.cdg",
                "SC1",
                "01",
                "Artist",
                "Title - Radio Edit",
            ),
            ("PHM0512-08 - Switchfoot - Stars.kar", "PHM0512", "08", "Switchfoot", "Stars"),
        ],
    )
    def test_issue_14_examples(self, filepath, disc, track, artist, title):
        result = self.parser.parse(filepath)
        assert result.disc == disc
        assert result.track == track
        assert result.artist == artist
        assert result.title == title

    def test_plain_space_dash_name_falls_back(self):
        result = self.parser.parse("Artist - Title.cdg")
        assert result.artist == "Artist"
        assert result.title == "Title"
        assert result.disc == ""
        assert result.track == ""

    def test_unspaced_stem_degrades_to_title_only(self):
        result = self.parser.parse("CB30055-15-Switchfoot-Stars.cdg")
        assert result.artist == ""
        assert result.disc == ""
        assert result.track == ""

    def test_prefix_without_hyphen_falls_back(self):
        result = self.parser.parse("Something - Artist - Title.cdg")
        assert result.artist == "Something"
        assert result.title == "Artist - Title"
        assert result.disc == ""
        assert result.track == ""

    def test_zip_member_uses_spaced_mode(self):
        result = self.parser.parse_zip_path(
            "PHM - Pop/PHM0512/PHM0512-08 - Switchfoot - Stars.kar"
        )
        assert result.disc == "PHM0512"
        assert result.track == "08"
        assert result.artist == "Switchfoot"
        assert result.title == "Stars"

    def test_spaced_mode_is_integer_four(self):
        assert int(FileNameType.DISC_TRACK_SPACED) == 4

    def test_other_modes_unchanged(self):
        default = _parser().parse("CB30055-15 - Switchfoot - Stars.cdg")
        assert default.artist == "CB30055-15"
        assert default.title == "Switchfoot - Stars"


# ===========================================================================
# ParsedSong dataclass tests
# ===========================================================================


class TestParsedSong:
    def test_default_values(self):
        song = ParsedSong()
        assert song.artist == ""
        assert song.title == ""
        assert song.disc == ""
        assert song.track == ""

    def test_explicit_values(self):
        song = ParsedSong(artist="Queen", title="Bohemian Rhapsody", disc="Q01", track="01")
        assert song.artist == "Queen"
        assert song.title == "Bohemian Rhapsody"
        assert song.disc == "Q01"
        assert song.track == "01"


# ===========================================================================
# Input validation (spec: "A null value fails fast")
# ===========================================================================


class TestInputValidation:
    @pytest.mark.parametrize("bad", [None, 42, b"bytes.cdg", ["list.cdg"]])
    def test_non_string_raises_type_error(self, bad):
        with pytest.raises(TypeError):
            _parser().parse(bad)


# ===========================================================================
# Unicode normalisation and field hygiene (filename-parser-edge-cases)
# ===========================================================================


class TestUnicodeNormalisation:
    def test_nfd_and_nfc_forms_agree(self):
        nfc = "Björk - Jóga.cdg"
        nfd = unicodedata.normalize("NFD", nfc)
        assert nfd != nfc
        assert _parser().parse(nfd) == _parser().parse(nfc)

    def test_cjk_characters_preserved(self):
        result = _parser().parse("初音ミク - 千本桜.mp3")
        assert result.artist == "初音ミク"
        assert result.title == "千本桜"

    @pytest.mark.parametrize(
        "dash",
        ["\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015", "\u2212", "\uFF0D", "\uFE58"],
    )
    def test_unicode_dash_variants_fold_to_separator(self, dash):
        # Unspaced dashes fold to the ASCII hyphen, so the legacy
        # Artist-Title split recognises them.
        result = _parser().parse(f"Artist{dash}Title.cdg")
        assert result.artist == "Artist"
        assert result.title == "Title"

    def test_unicode_dash_with_spaces_separates_fields(self):
        result = _parser().parse("Artist \u2014 Title.cdg")
        assert result.artist == "Artist"
        assert result.title == "Title"

    def test_full_width_parentheses_folded(self):
        result = _parser().parse("Artist - Title\uff08Live\uff09.mp3")
        assert result.artist == "Artist"
        assert result.title == "Title(Live)"

    def test_legacy_unicode_dash_parses(self):
        result = _parser(FileNameType.ARTIST_TITLE).parse("Queen\u2013Bohemian Rhapsody.kar")
        assert result.artist == "Queen"
        assert result.title == "Bohemian Rhapsody"


class TestFieldHygiene:
    def test_trailing_dot_stem_is_trimmed(self):
        result = _parser().parse("Artist - Title. .cdg")
        assert result.artist == "Artist"
        assert result.title == "Title"

    def test_embedded_null_byte_truncates(self):
        result = _parser().parse("Artist - Title\x00evil.cdg")
        assert result.artist == "Artist"
        assert result.title == "Title"

    def test_zero_width_characters_stripped(self):
        result = _parser().parse("Art\u200bist - Ti\u200dtle.cdg")
        assert result.artist == "Artist"
        assert result.title == "Title"


# ===========================================================================
# Defensive fallback branches (coverage of degraded inputs)
# ===========================================================================


class TestDegradedInputs:
    def test_zip_member_blank_directory_falls_through(self):
        result = _parser().parse_zip_path(" /Title.kar")
        assert result.artist == ""
        assert result.title == "Title"

    def test_space_dash_helper_without_separator_returns_title(self):
        # Defensive fallback in _parse_space_dash when no separator survives.
        assert _parser()._parse_space_dash("JustTitle").title == "JustTitle"

    def test_spaced_mode_helper_without_separator_falls_back(self):
        # Defensive fallback in _parse_disc_track_spaced when the stem has
        # no space-dash-space separator at all.
        result = _parser(FileNameType.DISC_TRACK_SPACED)._parse_disc_track_spaced("JustTitle")
        assert result.artist == ""
        assert result.title == "JustTitle"

    def test_spaced_mode_empty_track_falls_back(self):
        result = _parser(FileNameType.DISC_TRACK_SPACED).parse("CB1- - Artist - Title.cdg")
        assert result.disc == ""
        assert result.track == ""
        assert result.artist == "CB1-"
        assert result.title == "Artist - Title"

    def test_spaced_mode_single_remainder_falls_back(self):
        result = _parser(FileNameType.DISC_TRACK_SPACED).parse("CB1-15 - OnlyOne.cdg")
        assert result.artist == "CB1-15"
        assert result.title == "OnlyOne"
        assert result.disc == ""

    def test_legacy_disc_artist_mode_with_too_few_parts(self):
        result = _parser(FileNameType.DISC_ARTIST_TITLE).parse("Two-Parts.cdg")
        assert result.artist == ""
        assert result.title == "Two-Parts"

    def test_multi_abbreviation_artist_grouping(self):
        result = _parser(FileNameType.ARTIST_TITLE).parse("AC-DC-Rock & Roll.cdg")
        assert result.artist == "AC-DC"
        assert result.title == "Rock & Roll"

    def test_single_abbreviation_prefix_stops_grouping(self):
        result = _parser(FileNameType.ARTIST_TITLE).parse("MC-Hammer-Time.cdg")
        assert result.artist == "MC"
        assert result.title == "Hammer-Time"

    def test_path_traversal_is_reduced_to_basename(self):
        result = _parser().parse("../../etc/passwd")
        assert result.artist == ""
        assert result.title == "passwd"

    def test_zip_member_without_directory_falls_through(self):
        result = _parser().parse_zip_path("JustTitle.kar")
        assert result.artist == ""
        assert result.title == "JustTitle"

    def test_mixed_separators_resolve_to_basename(self):
        result = _parser().parse(r"C:\music/karaoke\Artist - Title.cdg")
        assert result.artist == "Artist"
        assert result.title == "Title"

    def test_zip_member_unicode_directory_fallback(self):
        result = _parser().parse_zip_path("语言/Åsa Burt/Title.kar")
        assert result.artist == "Åsa Burt"
        assert result.title == "Title"

    def test_spaced_mode_empty_title_falls_back(self):
        # Direct helper call: an empty title after the second separator is
        # a defensive fallback in _parse_disc_track_spaced.
        result = _parser(FileNameType.DISC_TRACK_SPACED)._parse_disc_track_spaced("CB1-15 - Artist - ")
        assert result.artist == "CB1-15"
        assert result.title == "Artist -"


class TestBulkPerformance:
    @pytest.mark.slow
    def test_ten_thousand_filenames_parse_quickly(self):
        import time

        names = [
            f"Artist{i} - Title {i}.cdg" for i in range(5000)
        ] + [f"SC{i:04d}-{i % 100:02d}-Some Artist-Song {i}.kar" for i in range(5000)]
        parser = _parser(FileNameType.DISC_TRACK_ARTIST_TITLE)
        start = time.perf_counter()
        for name in names:
            parser.parse(name)
        elapsed = time.perf_counter() - start
        assert len(names) == 10_000
        assert elapsed < 1.0, f"parsing 10,000 filenames took {elapsed:.2f}s"
