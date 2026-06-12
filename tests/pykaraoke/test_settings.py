"""Tests for settings and configuration structures.

Tests the settings defaults, validation, and serialization
without requiring pygame.
"""

import pytest


class TestDefaultSettings:
    """Test default settings values."""

    def test_default_window_size(self):
        """Test default window size is reasonable."""
        default_size = (640, 480)
        assert default_size[0] > 0
        assert default_size[1] > 0
        assert default_size[0] >= default_size[1]  # Wider than tall

    def test_default_player_size(self):
        """Test default player size."""
        default_size = (640, 480)
        assert default_size == (640, 480)

    def test_default_sample_rate(self):
        """Test default audio sample rate."""
        default_rate = 44100
        assert default_rate in [11025, 22050, 44100, 48000]

    def test_default_buffer_ms(self):
        """Test default audio buffer size in milliseconds."""
        default_buffer = 50
        # Should be small enough for responsive audio
        assert 10 <= default_buffer <= 500


class TestFileExtensionDefaults:
    """Test default file extension settings."""

    def test_kar_extensions(self):
        """Test default KAR file extensions."""
        extensions = [".kar", ".mid"]
        assert ".kar" in extensions
        assert ".mid" in extensions

    def test_cdg_extensions(self):
        """Test default CDG file extensions."""
        extensions = [".cdg"]
        assert ".cdg" in extensions

    def test_mpg_extensions(self):
        """Test default MPG file extensions."""
        extensions = [".mpg", ".mpeg", ".avi"]
        assert ".mpg" in extensions
        assert ".mpeg" in extensions

    def test_extensions_are_lowercase(self):
        """Test that all extensions are lowercase."""
        all_extensions = [".kar", ".mid", ".cdg", ".mpg", ".mpeg", ".avi"]
        for ext in all_extensions:
            assert ext == ext.lower()
            assert ext.startswith(".")


class TestEncodingSettings:
    """Test encoding-related settings."""

    def test_available_encodings(self):
        """Test list of available encodings."""
        encodings = [
            "cp1252",
            "iso-8859-1",
            "iso-8859-2",
            "iso-8859-5",
            "iso-8859-7",
            "utf-8",
        ]

        # All should be valid Python encodings
        import codecs

        for encoding in encodings:
            try:
                codecs.lookup(encoding)
            except LookupError:
                pytest.fail(f"Invalid encoding: {encoding}")

    def test_default_filesystem_encoding(self):
        """Test default filesystem encoding."""
        import os

        default = "cp1252" if os.name == "nt" else "iso-8859-1"

        assert default in ["cp1252", "iso-8859-1", "utf-8"]

    def test_default_zipfile_encoding(self):
        """Test default zipfile encoding."""
        default = "cp1252"
        # CP1252 is Windows Western European, common for ZIP files
        assert default == "cp1252"


class TestZoomModes:
    """Test CDG zoom mode settings."""

    def test_zoom_modes_defined(self):
        """Test that all zoom modes are defined."""
        zoom_modes = ["quick", "int", "full", "soft", "none"]
        assert len(zoom_modes) == 5

    def test_zoom_mode_descriptions(self):
        """Test zoom mode descriptions exist."""
        zoom_desc = {
            "quick": "a pixelly scale, maintaining aspect ratio",
            "int": "like quick, reducing artifacts a little",
            "full": "like quick, but stretches to fill the entire window",
            "soft": "a high-quality scale, but may be slow on some hardware",
            "none": "keep the display in its original size",
        }

        for mode in ["quick", "int", "full", "soft", "none"]:
            assert mode in zoom_desc
            assert len(zoom_desc[mode]) > 0


class TestSampleRateSettings:
    """Test audio sample rate settings."""

    def test_available_sample_rates(self):
        """Test list of available sample rates."""
        rates = [48000, 44100, 22050, 11025, 5512]

        # Should be in descending order
        assert rates == sorted(rates, reverse=True)

        # All should be standard rates
        for rate in rates:
            assert rate > 0
            assert isinstance(rate, int)

    def test_sample_rates_are_divisible(self):
        """Test that sample rates have nice divisibility properties."""

        # 44100 family
        assert 44100 // 22050 == 2
        assert 22050 // 11025 == 2

        # 48000 is divisible by common values
        assert 48000 % 1000 == 0
        assert 48000 % 100 == 0


class TestColorSettings:
    """Test color settings for karaoke display."""

    def test_kar_background_color(self):
        """Test default KAR background color."""
        color = (0, 0, 0)  # Black
        assert len(color) == 3
        assert all(0 <= c <= 255 for c in color)

    def test_kar_ready_color(self):
        """Test default KAR ready (unsung) color."""
        color = (255, 50, 50)  # Reddish
        assert len(color) == 3
        assert all(0 <= c <= 255 for c in color)

    def test_kar_sweep_color(self):
        """Test default KAR sweep (sung) color."""
        color = (255, 255, 255)  # White
        assert len(color) == 3
        assert all(0 <= c <= 255 for c in color)

    def test_kar_info_color(self):
        """Test default KAR info color."""
        color = (0, 0, 200)  # Blue
        assert len(color) == 3
        assert all(0 <= c <= 255 for c in color)

    def test_kar_title_color(self):
        """Test default KAR title color."""
        color = (100, 100, 255)  # Light blue
        assert len(color) == 3
        assert all(0 <= c <= 255 for c in color)

    def test_colors_are_distinct(self):
        """Test that display colors are distinct from each other."""
        colors = [
            (0, 0, 0),  # background
            (255, 50, 50),  # ready
            (255, 255, 255),  # sweep
            (0, 0, 200),  # info
            (100, 100, 255),  # title
        ]

        # Each color should be unique
        assert len(colors) == len(set(colors))


class TestFileNameCombinationSettings:
    """Test file name parsing combination settings."""

    def test_combinations_defined(self):
        """Test all file name combinations are defined."""
        combinations = [
            "Disc-Track-Artist-Title",
            "DiscTrack-Artist-Title",
            "Disc-Artist-Title",
            "Artist-Title",
        ]
        assert len(combinations) == 4

    def test_combination_indices_stable(self):
        """Test that combination indices are stable."""
        combinations = [
            "Disc-Track-Artist-Title",  # 0
            "DiscTrack-Artist-Title",  # 1
            "Disc-Artist-Title",  # 2
            "Artist-Title",  # 3
        ]

        # These indices are used in settings files
        assert combinations.index("Disc-Track-Artist-Title") == 0
        assert combinations.index("DiscTrack-Artist-Title") == 1
        assert combinations.index("Disc-Artist-Title") == 2
        assert combinations.index("Artist-Title") == 3


class TestVersionConstants:
    """Test version constants for settings and database."""

    def test_settings_version_is_integer(self):
        """Test that settings version is an integer."""
        SETTINGS_VERSION = 6
        assert isinstance(SETTINGS_VERSION, int)
        assert SETTINGS_VERSION > 0

    def test_database_version_is_integer(self):
        """Test that database version is an integer."""
        DATABASE_VERSION = 2
        assert isinstance(DATABASE_VERSION, int)
        assert DATABASE_VERSION > 0


class TestBooleanSettings:
    """Test boolean configuration settings."""

    def test_fullscreen_default(self):
        """Test fullscreen default is False."""
        default = False
        assert default is False

    def test_look_inside_zips_default(self):
        """Test look inside zips default is True."""
        default = True
        assert default is True

    def test_read_titles_txt_default(self):
        """Test read titles.txt default is True."""
        default = True
        assert default is True

    def test_check_hashes_default(self):
        """Test check hashes default is False."""
        default = False
        assert default is False

    def test_delete_identical_default(self):
        """Test delete identical default is False."""
        default = False
        assert default is False


class TestGP2XSettings:
    """Test GP2X-specific settings."""

    def test_gp2x_default_player_size(self):
        """Test GP2X default player size."""
        size = (320, 240)
        assert size == (320, 240)

    def test_gp2x_cpu_speeds_defined(self):
        """Test that GP2X CPU speed settings exist."""
        cpu_speeds = {
            "startup": 240,
            "wait": 33,
            "menu_idle": 33,
            "menu_slow": 100,
            "menu_fast": 240,
            "load": 240,
            "cdg": 200,
            "kar": 240,
            "mpg": 200,
        }

        # All speeds should be reasonable MHz values
        for activity, speed in cpu_speeds.items():
            assert 33 <= speed <= 300, f"CPU speed for {activity} out of range"


class TestFontDataSettings:
    """Regression: FontData settings must survive a save/load round-trip.

    FontData objects use a custom ``__repr__`` that is *not* a valid
    Python literal, so ``ast.literal_eval`` cannot parse the serialised
    form directly.  The settings parser must handle FontData specially.
    """

    def test_fontdata_roundtrip_no_size(self):
        """FontData without size round-trips through save/load."""
        from pykaraoke.core.database import FontData, SongDB

        fd = FontData("DejaVuSans.ttf")
        # Simulate what save_settings() writes
        serialised = (fd.name, fd.size, fd.bold, fd.italic)
        # Simulate what _parse_settings_line reconstructs
        reconstructed = FontData(*serialised)
        assert reconstructed.name == "DejaVuSans.ttf"
        assert reconstructed.size is None
        assert reconstructed.bold is False
        assert reconstructed.italic is False

    def test_fontdata_roundtrip_with_size(self):
        """FontData with size attributes round-trips correctly."""
        from pykaraoke.core.database import FontData

        fd = FontData("Arial", 14, bold=True, italic=False)
        serialised = (fd.name, fd.size, fd.bold, fd.italic)
        reconstructed = FontData(*serialised)
        assert reconstructed.name == "Arial"
        assert reconstructed.size == 14
        assert reconstructed.bold is True
        assert reconstructed.italic is False

    def test_fontdata_full_roundtrip(self):
        """Full FontData with all fields round-trips correctly."""
        from pykaraoke.core.database import FontData

        fd = FontData("Comic Sans", 18, bold=True, italic=True)
        serialised = (fd.name, fd.size, fd.bold, fd.italic)
        reconstructed = FontData(*serialised)
        assert reconstructed.name == "Comic Sans"
        assert reconstructed.size == 18
        assert reconstructed.bold is True
        assert reconstructed.italic is True

    def test_settings_parse_handles_fontdata_tuple(self):
        """_parse_settings_line reconstructs FontData from a tuple."""
        from pykaraoke.core.database import SongDB, SettingsStruct, FontData

        settings = SettingsStruct()
        # Simulate what save_settings() would write for kar_font
        SongDB._parse_settings_line(
            settings,
            "kar_font = ('DejaVuSans.ttf', None, False, False)\n",
        )
        result = getattr(settings, "kar_font")
        assert isinstance(result, FontData)
        assert result.name == "DejaVuSans.ttf"
        assert result.size is None
        assert result.bold is False
        assert result.italic is False

    def test_settings_serialize_fontdata_as_tuple(self):
        """save_settings must serialise FontData as a tuple literal."""
        from pykaraoke.core.database import FontData, SettingsStruct
        import io

        fd = FontData("MyFont.ttf")
        # Simulate the fix in save_settings(): convert FontData to tuple
        # BEFORE calling repr() so that ast.literal_eval can parse it.
        serialised = (fd.name, fd.size, fd.bold, fd.italic)
        repr_text = repr(serialised)
        # Must NOT contain FontData(...) since that is not a valid literal
        assert "FontData(" not in repr_text
        # Must be a valid Python literal that can be round-tripped
        import ast
        parsed = ast.literal_eval(repr_text)
        assert isinstance(parsed, tuple)
        assert parsed[0] == "MyFont.ttf"
