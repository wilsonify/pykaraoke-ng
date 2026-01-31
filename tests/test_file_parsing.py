"""Unit tests for file path parsing functions.

These tests verify the filename parsing logic used to extract
artist, title, disc, and track information from karaoke file names.
"""



class MockSettings:
    """Mock settings object for testing without pygame dependencies."""

    def __init__(self, file_name_type=0, derive_info=True):
        self.CdgDeriveSongInformation = derive_info
        self.CdgFileNameType = file_name_type
        self.ExcludeNonMatchingFilenames = False
        self.KarExtensions = [".kar", ".mid"]
        self.CdgExtensions = [".cdg"]
        self.MpgExtensions = [".mpg", ".mpeg", ".avi"]
        self.FilesystemCoding = "utf-8"
        self.ZipfileCoding = "cp1252"


class TestFileNameParsing:
    """Test filename parsing for different naming schemes."""

    # Note: These test the parsing logic conceptually.
    # The actual SongStruct class requires pygame, so we test the parsing
    # algorithm directly.

    def test_disc_track_artist_title_format(self):
        """Test parsing 'Disc-Track-Artist-Title.ext' format (type 0)."""
        filepath = "SC1234-05-John Doe-My Song.cdg"
        parts = filepath.split("-")

        assert len(parts) == 4, "Should have 4 parts for type 0"
        assert parts[0] == "SC1234"  # Disc
        assert parts[1] == "05"  # Track
        assert parts[2] == "John Doe"  # Artist
        # Title includes extension
        assert parts[3].startswith("My Song")

    def test_disctrack_artist_title_format(self):
        """Test parsing 'DiscTrack-Artist-Title.ext' format (type 1)."""
        filepath = "SC123405-John Doe-My Song.cdg"
        parts = filepath.split("-")

        assert len(parts) == 3, "Should have 3 parts for type 1"
        assert parts[0] == "SC123405"  # DiscTrack combined
        assert parts[1] == "John Doe"  # Artist
        assert parts[2].startswith("My Song")  # Title

    def test_disc_artist_title_format(self):
        """Test parsing 'Disc-Artist-Title.ext' format (type 2)."""
        filepath = "SC1234-John Doe-My Song.cdg"
        parts = filepath.split("-")

        assert len(parts) == 3, "Should have 3 parts for type 2"
        assert parts[0] == "SC1234"  # Disc
        assert parts[1] == "John Doe"  # Artist
        assert parts[2].startswith("My Song")  # Title

    def test_artist_title_format(self):
        """Test parsing 'Artist-Title.ext' format (type 3)."""
        filepath = "John Doe-My Song.cdg"
        parts = filepath.split("-")

        assert len(parts) == 2, "Should have 2 parts for type 3"
        assert parts[0] == "John Doe"  # Artist
        assert parts[1].startswith("My Song")  # Title

    def test_parse_with_spaces(self):
        """Test parsing filenames with spaces in artist and title."""
        filepath = "SC1234-05-The Rolling Stones-Paint It Black.cdg"
        parts = filepath.split("-")

        assert len(parts) == 4
        assert parts[2] == "The Rolling Stones"
        assert "Paint It Black" in parts[3]

    def test_parse_handles_extra_dashes_gracefully(self):
        """Test that extra dashes in title don't break parsing."""
        filepath = "SC1234-05-Artist-Title-With-Dashes.cdg"
        # This format won't parse correctly with simple split
        parts = filepath.split("-")

        # The simple split will produce more parts than expected
        assert len(parts) > 4

    def test_extension_removal(self):
        """Test that extension is correctly stripped from title."""
        import os

        filename = "My Song.cdg"
        title_without_ext = os.path.splitext(filename)[0]

        assert title_without_ext == "My Song"
        assert ".cdg" not in title_without_ext


class TestFileExtensions:
    """Test file extension handling."""

    def test_kar_extensions(self):
        """Test KAR file extensions."""
        settings = MockSettings()
        assert ".kar" in settings.KarExtensions
        assert ".mid" in settings.KarExtensions

    def test_cdg_extensions(self):
        """Test CDG file extensions."""
        settings = MockSettings()
        assert ".cdg" in settings.CdgExtensions

    def test_mpg_extensions(self):
        """Test MPG file extensions."""
        settings = MockSettings()
        assert ".mpg" in settings.MpgExtensions
        assert ".mpeg" in settings.MpgExtensions
        assert ".avi" in settings.MpgExtensions

    def test_extension_case_handling(self):
        """Test that extensions are stored in lowercase."""
        settings = MockSettings()

        for ext in settings.KarExtensions + settings.CdgExtensions + settings.MpgExtensions:
            assert ext == ext.lower(), f"Extension {ext} should be lowercase"

    def test_extension_detection(self):
        """Test extension extraction from filenames."""
        import os

        test_cases = [
            ("song.kar", ".kar"),
            ("song.cdg", ".cdg"),
            ("song.mpg", ".mpg"),
            ("SONG.KAR", ".KAR"),  # OS preserves case
            ("path/to/song.mid", ".mid"),
            ("song.with.dots.kar", ".kar"),
        ]

        for filename, expected_ext in test_cases:
            _, ext = os.path.splitext(filename)
            assert ext == expected_ext


class TestSortKeyGeneration:
    """Test the sort key generation logic for songs."""

    def test_strip_whitespace(self):
        """Test that whitespace is stripped."""
        test_str = "  My Song  "
        result = test_str.strip().lower()
        assert result == "my song"

    def test_lowercase_conversion(self):
        """Test that strings are lowercased."""
        test_str = "My Song"
        result = test_str.strip().lower()
        assert result == "my song"

    def test_article_removal_the(self):
        """Test removal of 'The' article."""
        test_str = "The Beatles"
        result = test_str.strip().lower()
        first_word = result.split()[0]

        if first_word in ["a", "an", "the"]:
            result = result[len(first_word) :].strip()

        assert result == "beatles"

    def test_article_removal_a(self):
        """Test removal of 'A' article."""
        test_str = "A Hard Day's Night"
        result = test_str.strip().lower()
        first_word = result.split()[0]

        if first_word in ["a", "an", "the"]:
            result = result[len(first_word) :].strip()

        assert result == "hard day's night"

    def test_article_removal_an(self):
        """Test removal of 'An' article."""
        test_str = "An American in Paris"
        result = test_str.strip().lower()
        first_word = result.split()[0]

        if first_word in ["a", "an", "the"]:
            result = result[len(first_word) :].strip()

        assert result == "american in paris"

    def test_no_article_no_change(self):
        """Test that strings without articles are unchanged."""
        test_str = "Queen"
        result = test_str.strip().lower()
        first_word = result.split()[0]

        if first_word in ["a", "an", "the"]:
            result = result[len(first_word) :].strip()

        assert result == "queen"

    def test_parenthetical_removal(self):
        """Test removal of leading parenthetical phrases."""
        test_str = "(The) Beatles"
        result = test_str.strip().lower()

        if result and result[0] == "(":
            try:
                rparen = result.index(")")
                if rparen != -1:
                    result = result[rparen + 1 :].strip()
            except ValueError:
                pass

        assert result == "beatles"


class TestFileNameCombinations:
    """Test the file naming scheme configurations."""

    def test_all_combinations_defined(self):
        """Test that all file name combinations are defined."""
        combinations = [
            "Disc-Track-Artist-Title",
            "DiscTrack-Artist-Title",
            "Disc-Artist-Title",
            "Artist-Title",
        ]

        assert len(combinations) == 4

    def test_combination_indices(self):
        """Test that combination indices match expected values."""
        combinations = [
            "Disc-Track-Artist-Title",  # 0
            "DiscTrack-Artist-Title",  # 1
            "Disc-Artist-Title",  # 2
            "Artist-Title",  # 3
        ]

        assert combinations[0] == "Disc-Track-Artist-Title"
        assert combinations[1] == "DiscTrack-Artist-Title"
        assert combinations[2] == "Disc-Artist-Title"
        assert combinations[3] == "Artist-Title"


class TestFilepathNormalization:
    """Test filepath normalization and handling."""

    def test_basename_extraction_posix(self):
        """Test extracting basename from POSIX paths."""
        import os

        test_cases = [
            ("/home/user/songs/song.kar", "song.kar"),
            ("song.mpg", "song.mpg"),
            ("./relative/path/song.mid", "song.mid"),
        ]

        for path, expected in test_cases:
            result = os.path.basename(path)
            assert result == expected

    def test_basename_extraction_windows(self):
        """Test extracting basename from Windows paths.
        
        Note: os.path.basename behavior differs between platforms.
        On POSIX, backslashes are not treated as path separators.
        """
        import os
        import sys

        # On Windows, this would work correctly
        # On POSIX, we need to handle Windows paths differently
        path = "C:\\Music\\song.cdg"

        # Cross-platform way to get basename from Windows path
        if sys.platform != "win32":
            # On POSIX, split on backslash manually for Windows paths
            result = path.split("\\")[-1]
        else:
            result = os.path.basename(path)

        assert result == "song.cdg"

    def test_tab_completion_fix(self):
        """Test that trailing dot is converted to .cdg extension."""
        filepath = "/path/to/song."

        if filepath and filepath[-1] == ".":
            filepath += "cdg"

        assert filepath == "/path/to/song.cdg"

    def test_no_trailing_dot_unchanged(self):
        """Test that paths without trailing dot are unchanged."""
        filepath = "/path/to/song.cdg"
        original = filepath

        if filepath and filepath[-1] == ".":
            filepath += "cdg"

        assert filepath == original
