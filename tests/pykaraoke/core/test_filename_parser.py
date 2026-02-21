"""Parameterized unit tests for the filename_parser module.

Tests verify that :class:`FilenameParser` correctly extracts artist and
title from karaoke filenames under a wide range of edge cases, including:

- Multiple dashes in the title
- Dashes in the directory path (must be ignored)
- Space-dash-space separator patterns
- Legacy dash-only formats (all four ``FileNameType`` variants)
- Parenthetical modifiers, e.g. "(Remix)"
- Files without a recognisable separator (graceful fallback)
"""

import pytest

from pykaraoke.core.filename_parser import FileNameType, FilenameParser, ParsedSong


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parser(name_type: FileNameType = FileNameType.ARTIST_TITLE) -> FilenameParser:
    return FilenameParser(file_name_type=name_type)


# ===========================================================================
# Space-dash-space pattern tests
# ===========================================================================


class TestSpaceDashPattern:
    """Tests for the modern ``Artist - Title`` family of patterns."""

    @pytest.mark.parametrize(
        "filepath, expected_artist, expected_title",
        [
            # Basic case
            ("Artist - Title.mp3", "Artist", "Title"),
            # Title with spaces
            ("John Doe - My Song.mp3", "John Doe", "My Song"),
            # Title with parenthetical modifier
            ("Artist - Title (Remix).cdg", "Artist", "Title (Remix)"),
            # Multiple " - " segments: extra segments become part of the title
            ("Artist - Title - Live.mp3", "Artist", "Title - Live"),
            # Artist with spaces, title with extra segment
            ("The Beatles - Let It Be - Live.kar", "The Beatles", "Let It Be - Live"),
            # Extension .kar
            ("Sinatra - My Way.kar", "Sinatra", "My Way"),
            # Numbers in title
            ("Artist - Song 2024.cdg", "Artist", "Song 2024"),
            # Dashes inside title after the first " - "
            ("Artist - A-B-C Song.cdg", "Artist", "A-B-C Song"),
            # Leading / trailing spaces around artist and title
            ("  Artist   -   Title  .mp3", "Artist", "Title"),
        ],
    )
    def test_space_dash_extraction(
        self, filepath: str, expected_artist: str, expected_title: str
    ) -> None:
        result = _parser().parse(filepath)
        assert result.artist == expected_artist
        assert result.title == expected_title

    def test_directory_dashes_ignored(self) -> None:
        """Dashes in directory path components must not affect parsing."""
        result = _parser().parse("/music/rock-band/best-of/Artist - Title.mp3")
        assert result.artist == "Artist"
        assert result.title == "Title"

    def test_windows_path_dashes_ignored(self) -> None:
        """Windows-style paths with dashes in directory names are handled."""
        result = _parser().parse(r"C:\my-music\rock-hits\Queen - Bohemian Rhapsody.cdg")
        assert result.artist == "Queen"
        assert result.title == "Bohemian Rhapsody"

    def test_disc_and_track_empty_for_space_dash(self) -> None:
        """Space-dash format does not populate disc/track fields."""
        result = _parser().parse("Artist - Title.mp3")
        assert result.disc == ""
        assert result.track == ""


# ===========================================================================
# Legacy format tests
# ===========================================================================


class TestLegacyDiscTrackArtistTitle:
    """FileNameType.DISC_TRACK_ARTIST_TITLE — four-part format."""

    parser = _parser(FileNameType.DISC_TRACK_ARTIST_TITLE)

    @pytest.mark.parametrize(
        "filepath, disc, track, artist, title",
        [
            ("SC1234-05-John Doe-My Song.cdg", "SC1234", "05", "John Doe", "My Song"),
            ("SC1234-05-The Rolling Stones-Paint It Black.cdg", "SC1234", "05", "The Rolling Stones", "Paint It Black"),
            # Extra dashes in title must be preserved
            ("SC1234-05-Artist-Title-With-Dashes.cdg", "SC1234", "05", "Artist", "Title-With-Dashes"),
        ],
    )
    def test_four_part_parsing(
        self, filepath: str, disc: str, track: str, artist: str, title: str
    ) -> None:
        result = self.parser.parse(filepath)
        assert result.disc == disc
        assert result.track == track
        assert result.artist == artist
        assert result.title == title

    def test_fewer_than_four_parts_falls_back_to_title_only(self) -> None:
        """With <4 parts the parser returns the whole stem as the title."""
        result = self.parser.parse("OnePart.cdg")
        assert result.title == "OnePart"
        assert result.artist == ""


class TestLegacyDisctTrackArtistTitle:
    """FileNameType.DISCTRACK_ARTIST_TITLE — three-part combined disc+track."""

    parser = _parser(FileNameType.DISCTRACK_ARTIST_TITLE)

    @pytest.mark.parametrize(
        "filepath, disc, artist, title",
        [
            ("SC123405-John Doe-My Song.cdg", "SC123405", "John Doe", "My Song"),
            ("AB9901-Queen-Bohemian Rhapsody.cdg", "AB9901", "Queen", "Bohemian Rhapsody"),
        ],
    )
    def test_three_part_parsing(
        self, filepath: str, disc: str, artist: str, title: str
    ) -> None:
        result = self.parser.parse(filepath)
        assert result.disc == disc
        assert result.artist == artist
        assert result.title == title


class TestLegacyDiscArtistTitle:
    """FileNameType.DISC_ARTIST_TITLE — three-part with separate disc."""

    parser = _parser(FileNameType.DISC_ARTIST_TITLE)

    @pytest.mark.parametrize(
        "filepath, disc, artist, title",
        [
            ("SC1234-John Doe-My Song.cdg", "SC1234", "John Doe", "My Song"),
            ("DISC1-Adele-Hello.kar", "DISC1", "Adele", "Hello"),
        ],
    )
    def test_three_part_parsing(
        self, filepath: str, disc: str, artist: str, title: str
    ) -> None:
        result = self.parser.parse(filepath)
        assert result.disc == disc
        assert result.artist == artist
        assert result.title == title


class TestLegacyArtistTitle:
    """FileNameType.ARTIST_TITLE — two-part simple format."""

    parser = _parser(FileNameType.ARTIST_TITLE)

    @pytest.mark.parametrize(
        "filepath, expected_artist, expected_title",
        [
            ("John Doe-My Song.cdg", "John Doe", "My Song"),
            ("Queen-Bohemian Rhapsody.kar", "Queen", "Bohemian Rhapsody"),
            # Extra dashes in title are preserved
            ("Artist-Title-Extra.cdg", "Artist", "Title-Extra"),
        ],
    )
    def test_two_part_parsing(
        self, filepath: str, expected_artist: str, expected_title: str
    ) -> None:
        result = self.parser.parse(filepath)
        assert result.artist == expected_artist
        assert result.title == expected_title

    def test_single_part_falls_back_to_title_only(self) -> None:
        result = self.parser.parse("JustTitle.cdg")
        assert result.title == "JustTitle"
        assert result.artist == ""


# ===========================================================================
# Edge-case / robustness tests
# ===========================================================================


class TestEdgeCases:
    """Boundary and robustness tests shared across parser instances."""

    def test_extension_stripped(self) -> None:
        """File extension must not appear in artist or title."""
        result = _parser().parse("Artist - Title.cdg")
        assert ".cdg" not in result.artist
        assert ".cdg" not in result.title

    def test_multiple_extensions_stripped(self) -> None:
        """Only the final extension is stripped."""
        result = _parser().parse("Artist - Song.name.cdg")
        assert result.title == "Song.name"

    def test_deep_directory_path_ignored(self) -> None:
        """Deep directory structures with dashes do not bleed into fields."""
        result = _parser().parse("/a-b/c-d/e-f/Artist - Title.cdg")
        assert result.artist == "Artist"
        assert result.title == "Title"

    def test_empty_filepath_returns_empty(self) -> None:
        result = _parser().parse("")
        assert result.artist == ""
        assert result.title == ""

    def test_only_extension_returns_empty(self) -> None:
        # os.path.splitext treats ".cdg" as a dotfile with no extension,
        # so the stem is ".cdg" itself.  There is no separator, so the
        # parser returns the stem as the title.
        result = _parser().parse(".cdg")
        assert result.artist == ""
        assert result.title == ".cdg"

    def test_no_separator_returns_title_only(self) -> None:
        """Filenames with no recognisable separator use the whole stem as title."""
        result = _parser().parse("JustATitle.mp3")
        assert result.title == "JustATitle"
        assert result.artist == ""

    def test_unicode_filenames(self) -> None:
        """Unicode characters in artist and title are preserved."""
        result = _parser().parse("Björk - Jóga.cdg")
        assert result.artist == "Björk"
        assert result.title == "Jóga"

    def test_parenthetical_title_preserved(self) -> None:
        result = _parser().parse("Artist - Title (feat. Someone).cdg")
        assert result.title == "Title (feat. Someone)"

    def test_numbers_only_title(self) -> None:
        result = _parser().parse("Artist - 99 Problems.cdg")
        assert result.artist == "Artist"
        assert result.title == "99 Problems"


# ===========================================================================
# ParsedSong dataclass tests
# ===========================================================================


class TestParsedSong:
    """Tests for the ParsedSong dataclass defaults and fields."""

    def test_default_values(self) -> None:
        song = ParsedSong()
        assert song.artist == ""
        assert song.title == ""
        assert song.disc == ""
        assert song.track == ""

    def test_explicit_values(self) -> None:
        song = ParsedSong(artist="Queen", title="Bohemian Rhapsody", disc="Q01", track="01")
        assert song.artist == "Queen"
        assert song.title == "Bohemian Rhapsody"
        assert song.disc == "Q01"
        assert song.track == "01"
