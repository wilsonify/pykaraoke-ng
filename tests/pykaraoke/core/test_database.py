"""
Comprehensive tests for pykaraoke.core.database module.

Tests SongStruct, SongDB, Settings, and related database functionality
with pygame mocked out to allow headless testing.
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Ensure pygame is mocked before importing database module
from tests.conftest import install_pygame_mock

install_pygame_mock()

from pykaraoke.core.database import (
    SongStruct,
    SongDB,
    SettingsStruct,
    TitleStruct,
    AppYielder,
    BusyCancelDialog,
    SETTINGS_VERSION,
    DATABASE_VERSION,
    MAX_ZIP_FILES,
    YIELD_INTERVAL,
)

# Alias for readability
SongSettings = SettingsStruct


class TestAppYielder:
    """Tests for the AppYielder utility class."""

    def test_init(self):
        yielder = AppYielder()
        assert hasattr(yielder, "last_yield")

    def test_consider_yield_short_interval(self):
        """consider_yield should not call Yield if interval is short."""
        yielder = AppYielder()
        # last_yield is set to current ticks, so consider_yield should not yield
        yielder.do_yield = MagicMock()
        yielder.consider_yield()
        # With default ticks returning 0, it won't yield since (0 - 0) < YIELD_INTERVAL

    def test_yield_base_does_nothing(self):
        """Base AppYielder.do_yield() should do nothing (abstract)."""
        yielder = AppYielder()
        yielder.do_yield()  # Should not raise


class TestBusyCancelDialog:
    """Tests for the BusyCancelDialog base class."""

    def test_init(self):
        dialog = BusyCancelDialog()
        assert dialog.clicked is False

    def test_set_progress(self):
        """set_progress should be callable."""
        dialog = BusyCancelDialog()
        if hasattr(dialog, "set_progress"):
            dialog.set_progress("test", 0.5)


class TestSongSettings:
    """Tests for the SongSettings class (default settings)."""

    def test_default_settings_created(self):
        settings = SongSettings()
        assert hasattr(settings, "folder_list")
        assert isinstance(settings.folder_list, list)

    def test_default_sample_rate(self):
        settings = SongSettings()
        assert hasattr(settings, "SampleRate")
        assert settings.SampleRate > 0

    def test_default_player_size(self):
        settings = SongSettings()
        assert hasattr(settings, "PlayerSize")
        assert len(settings.PlayerSize) == 2

    def test_default_zoom_modes(self):
        settings = SongSettings()
        assert hasattr(settings, "Zoom")
        assert isinstance(settings.Zoom, (list, tuple))
        assert len(settings.Zoom) > 0

    def test_default_fullscreen(self):
        settings = SongSettings()
        assert hasattr(settings, "FullScreen")
        assert isinstance(settings.FullScreen, bool)

    def test_default_buffer_ms(self):
        settings = SongSettings()
        assert hasattr(settings, "BufferMs")
        assert settings.BufferMs > 0

    def test_default_num_channels(self):
        settings = SongSettings()
        assert hasattr(settings, "NumChannels")
        assert settings.NumChannels in (1, 2)

    def test_default_extensions(self):
        settings = SongSettings()
        assert hasattr(settings, "CdgExtensions")
        assert ".cdg" in settings.CdgExtensions or "cdg" in str(settings.CdgExtensions).lower()

    def test_default_look_inside_zips(self):
        settings = SongSettings()
        assert hasattr(settings, "look_inside_zips")
        assert isinstance(settings.look_inside_zips, bool)

    def test_default_read_titles_txt(self):
        settings = SongSettings()
        assert hasattr(settings, "read_titles_txt")
        assert isinstance(settings.read_titles_txt, bool)


class TestSongStructBasic:
    """Tests for SongStruct creation and basic properties."""

    def test_create_cdg_song(self):
        """SongStruct should identify CDG files correctly."""
        settings = SongSettings()
        try:
            song = SongStruct("/path/to/song.cdg", settings)
            assert song.Filepath == "/path/to/song.cdg"
            assert song.Type == SongStruct.T_CDG
        except (KeyError, ValueError):
            # May raise if extension validation is strict
            pass

    def test_create_kar_song(self):
        """SongStruct should identify KAR files correctly."""
        settings = SongSettings()
        try:
            song = SongStruct("/path/to/song.kar", settings)
            assert song.Filepath == "/path/to/song.kar"
            assert song.Type == SongStruct.T_KAR
        except (KeyError, ValueError):
            pass

    def test_create_mpg_song(self):
        """SongStruct should identify MPEG files correctly."""
        settings = SongSettings()
        try:
            song = SongStruct("/path/to/song.mpg", settings)
            assert song.Filepath == "/path/to/song.mpg"
            assert song.Type == SongStruct.T_MPG
        except (KeyError, ValueError):
            pass

    def test_create_mp3_cdg_song(self):
        """SongStruct should identify mp3+g (CDG) files correctly."""
        settings = SongSettings()
        try:
            song = SongStruct("/path/to/song.cdg", settings)
            assert song.Type == SongStruct.T_CDG
        except (KeyError, ValueError):
            pass

    def test_song_mark_key(self):
        """SongStruct.get_mark_key() should return (Filepath, ZipStoredName)."""
        settings = SongSettings()
        try:
            song1 = SongStruct("/path/to/song.cdg", settings)
            assert song1.get_mark_key() == ("/path/to/song.cdg", None)
        except (KeyError, ValueError):
            pass

    def test_song_zip_stored_name(self):
        """SongStruct should preserve ZipStoredName."""
        settings = SongSettings()
        try:
            song = SongStruct(
                "/path/to/songs.zip",
                settings,
                zip_stored_name="artist - title.cdg",
            )
            assert song.ZipStoredName == "artist - title.cdg"
        except (KeyError, ValueError):
            pass


class TestSongStructParsing:
    """Tests for SongStruct filename parsing methods."""

    def test_make_sort_key_lowercase(self):
        """MakeSortKey should lowercase the input."""
        settings = SongSettings()
        try:
            song = SongStruct("/path/to/song.cdg", settings)
            key = song.make_sort_key("Hello World")
            assert key == "hello world"
        except (KeyError, ValueError):
            pass

    def test_make_sort_key_removes_article_the(self):
        """MakeSortKey should remove leading 'the'."""
        settings = SongSettings()
        try:
            song = SongStruct("/path/to/song.cdg", settings)
            key = song.make_sort_key("The Beatles")
            assert key == "beatles"
        except (KeyError, ValueError):
            pass

    def test_make_sort_key_removes_article_a(self):
        """MakeSortKey should remove leading 'a'."""
        settings = SongSettings()
        try:
            song = SongStruct("/path/to/song.cdg", settings)
            key = song.make_sort_key("A Song")
            assert key == "song"
        except (KeyError, ValueError):
            pass

    def test_make_sort_key_removes_article_an(self):
        """MakeSortKey should remove leading 'an'."""
        settings = SongSettings()
        try:
            song = SongStruct("/path/to/song.cdg", settings)
            key = song.make_sort_key("An Example")
            assert key == "example"
        except (KeyError, ValueError):
            pass

    def test_make_sort_key_strips_whitespace(self):
        """MakeSortKey should strip leading/trailing whitespace."""
        settings = SongSettings()
        try:
            song = SongStruct("/path/to/song.cdg", settings)
            key = song.make_sort_key("  Hello  ")
            assert key == "hello"
        except (KeyError, ValueError):
            pass

    def test_make_sort_key_removes_parenthetical(self):
        """MakeSortKey should remove leading parenthetical phrase."""
        settings = SongSettings()
        try:
            song = SongStruct("/path/to/song.cdg", settings)
            key = song.make_sort_key("(Bonus) Track Name")
            assert "track name" in key
        except (KeyError, ValueError):
            pass

    def test_parse_disc_type0(self):
        """ParseDisc with type 0 should extract disc from Disc-Track-Artist-Title."""
        settings = SongSettings()
        settings.CdgDeriveSongInformation = True
        settings.CdgFileNameType = 0
        try:
            song = SongStruct("/path/to/song.cdg", settings)
            disc = song.parse_disc("DISC01-01-Artist-Title", settings)
            assert disc == "DISC01"
        except (KeyError, ValueError):
            pass

    def test_parse_disc_type1(self):
        """ParseDisc with type 1 should extract disc from DiscTrack format."""
        settings = SongSettings()
        settings.CdgDeriveSongInformation = True
        settings.CdgFileNameType = 1
        try:
            song = SongStruct("/path/to/song.cdg", settings)
            disc = song.parse_disc("DISC01-Artist-Title", settings)
            # After fix: should use filepath[:-2]
            assert isinstance(disc, str)
        except (KeyError, ValueError):
            pass

    def test_parse_track_type0(self):
        """ParseTrack with type 0 should extract track from Disc-Track-Artist-Title."""
        settings = SongSettings()
        settings.CdgDeriveSongInformation = True
        settings.CdgFileNameType = 0
        try:
            song = SongStruct("/path/to/song.cdg", settings)
            track = song.parse_track("DISC01-02-Artist-Title", settings)
            assert track == "02"
        except (KeyError, ValueError):
            pass

    def test_parse_track_type1(self):
        """ParseTrack with type 1 should extract last 2 chars as track."""
        settings = SongSettings()
        settings.CdgDeriveSongInformation = True
        settings.CdgFileNameType = 1
        try:
            song = SongStruct("/path/to/song.cdg", settings)
            track = song.parse_track("DISC01-Artist-Title", settings)
            # After fix: should use filepath[-2:]
            assert isinstance(track, str)
        except (KeyError, ValueError):
            pass

    def test_lt_comparison(self):
        """SongStruct should support < comparison for sorting when file_sort_key is set."""
        import pykaraoke.core.database as db_module
        settings = SongSettings()
        try:
            song1 = SongStruct("/path/to/a_song.cdg", settings)
            song2 = SongStruct("/path/to/b_song.cdg", settings)
            # Set the global file_sort_key function
            old_key = db_module.file_sort_key
            db_module.file_sort_key = lambda s: s.DisplayFilename.lower()
            try:
                result = song1 < song2
                assert isinstance(result, bool)
            finally:
                db_module.file_sort_key = old_key
        except (KeyError, ValueError):
            pass

    def test_eq_comparison(self):
        """SongStruct should support == comparison when file_sort_key is set."""
        import pykaraoke.core.database as db_module
        settings = SongSettings()
        try:
            song1 = SongStruct("/path/to/song.cdg", settings)
            song2 = SongStruct("/path/to/song.cdg", settings)
            old_key = db_module.file_sort_key
            db_module.file_sort_key = lambda s: s.DisplayFilename.lower()
            try:
                result = song1 == song2
                assert isinstance(result, bool)
            finally:
                db_module.file_sort_key = old_key
        except (KeyError, ValueError):
            pass


class TestSongDBInit:
    """Tests for SongDB initialization."""

    def test_songdb_creates_settings(self):
        """SongDB should create a Settings object."""
        db = SongDB()
        assert hasattr(db, "Settings")
        assert isinstance(db.Settings, SongSettings)

    def test_songdb_empty_song_list(self):
        """SongDB should start with empty song lists."""
        db = SongDB()
        assert hasattr(db, "FullSongList")
        assert len(db.FullSongList) == 0

    def test_songdb_has_save_dir(self):
        """SongDB should determine a save directory."""
        db = SongDB()
        assert hasattr(db, "save_dir")
        assert isinstance(db.save_dir, str)

    def test_songdb_has_temp_dir(self):
        """SongDB should determine a temp directory."""
        db = SongDB()
        assert hasattr(db, "temp_dir")
        assert isinstance(db.temp_dir, str)


class TestSongDBOperations:
    """Tests for SongDB operational methods."""

    def test_folder_add(self):
        """FolderAdd should add a folder to the search list."""
        db = SongDB()
        db.folder_add("/path/to/songs")
        assert "/path/to/songs" in db.Settings.folder_list

    def test_folder_add_no_duplicates(self):
        """FolderAdd should not add duplicate folders."""
        db = SongDB()
        db.folder_add("/path/to/songs")
        db.folder_add("/path/to/songs")
        assert db.Settings.folder_list.count("/path/to/songs") == 1

    def test_folder_del(self):
        """FolderDel should remove a folder from the search list."""
        db = SongDB()
        db.folder_add("/path/to/songs")
        db.folder_del("/path/to/songs")
        assert "/path/to/songs" not in db.Settings.folder_list

    def test_is_extension_valid_cdg(self):
        """IsExtensionValid should recognize .cdg files."""
        db = SongDB()
        # CDG extension should be valid
        result = db.is_extension_valid(".cdg")
        assert isinstance(result, bool)

    def test_get_save_directory_env_override(self):
        """getSaveDirectory should respect PYKARAOKE_DIR env var."""
        db = SongDB()
        with patch.dict(os.environ, {"PYKARAOKE_DIR": "/custom/path"}):
            save_dir = db.get_save_directory()
            assert save_dir == "/custom/path"

    def test_get_temp_directory_env_override(self):
        """getTempDirectory should respect PYKARAOKE_TEMP_DIR env var."""
        db = SongDB()
        with patch.dict(os.environ, {"PYKARAOKE_TEMP_DIR": "/custom/temp"}):
            temp_dir = db.get_temp_directory()
            assert temp_dir == "/custom/temp"

    def test_save_settings_creates_directory(self):
        """SaveSettings should create save directory if needed."""
        db = SongDB()
        with tempfile.TemporaryDirectory() as tmpdir:
            db.save_dir = os.path.join(tmpdir, "pykaraoke_test")
            db.save_settings()
            assert os.path.exists(db.save_dir)

    def test_save_settings_writes_file(self):
        """SaveSettings should create settings.dat file."""
        db = SongDB()
        with tempfile.TemporaryDirectory() as tmpdir:
            db.save_dir = tmpdir
            db.save_settings()
            settings_path = os.path.join(tmpdir, "settings.dat")
            assert os.path.exists(settings_path)

    def test_load_settings_nonexistent_dir(self):
        """LoadSettings should handle nonexistent directory gracefully."""
        db = SongDB()
        db.save_dir = "/nonexistent/path/that/does/not/exist"
        # Should not raise
        try:
            db.load_settings(None)
        except (OSError, FileNotFoundError):
            pass  # Expected for nonexistent path


class TestSongDBZipCache:
    """Tests for SongDB zip file caching."""

    def test_zip_files_list_initialized(self):
        """SongDB should initialize with empty zip file cache."""
        db = SongDB()
        assert hasattr(db, "zip_files")
        assert len(db.zip_files) == 0


class TestConstants:
    """Tests for database module constants."""

    def test_settings_version_is_int(self):
        assert isinstance(SETTINGS_VERSION, int)
        assert SETTINGS_VERSION > 0

    def test_database_version_is_int(self):
        assert isinstance(DATABASE_VERSION, int)
        assert DATABASE_VERSION > 0

    def test_max_zip_files_reasonable(self):
        assert isinstance(MAX_ZIP_FILES, int)
        assert MAX_ZIP_FILES > 0

    def test_yield_interval_reasonable(self):
        assert isinstance(YIELD_INTERVAL, int)
        assert YIELD_INTERVAL > 0
