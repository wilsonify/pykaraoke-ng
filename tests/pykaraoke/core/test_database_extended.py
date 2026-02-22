"""
Additional coverage tests for pykaraoke.core.database module.

Focus on SongData class, SettingsStruct defaults, SongDB helper methods,
and file extension validation.
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()

from pykaraoke.core.database import (
    SongStruct,
    SongDB,
    SongData,
    SettingsStruct,
    AppYielder,
    BusyCancelDialog,
    TitleStruct,
    DBStruct,
    SETTINGS_VERSION,
    DATABASE_VERSION,
    MAX_ZIP_FILES,
    YIELD_INTERVAL,
)


class TestSongData:
    """Tests for SongData class."""

    def test_songdata_from_file(self):
        """SongData with data=None means a true file on disk."""
        sd = SongData("/path/to/song.cdg", None)
        assert sd.filename == "/path/to/song.cdg"
        assert sd.trueFile is True
        assert sd.data is None
        assert sd.Ext == ".cdg"

    def test_songdata_from_data(self):
        """SongData with data means it came from a zip."""
        data = b"fake cdg data"
        sd = SongData("song.cdg", data)
        assert sd.filename == "song.cdg"
        assert sd.trueFile is False
        assert sd.data == data
        assert sd.Ext == ".cdg"

    def test_songdata_get_data_from_memory(self):
        """GetData should return data if already in memory."""
        data = b"fake cdg data"
        sd = SongData("song.cdg", data)
        assert sd.GetData() == data

    def test_songdata_get_data_from_file(self):
        """GetData should read file from disk if trueFile."""
        with tempfile.NamedTemporaryFile(suffix=".cdg", delete=False) as f:
            f.write(b"test cdg content")
            fname = f.name
        try:
            sd = SongData(fname, None)
            result = sd.GetData()
            assert result == b"test cdg content"
        finally:
            os.unlink(fname)

    def test_songdata_get_filepath_true_file(self):
        """GetFilepath should return filename directly for true files."""
        sd = SongData("/path/to/song.cdg", None)
        assert sd.GetFilepath() == "/path/to/song.cdg"

    def test_songdata_extension_kar(self):
        """SongData should correctly extract .kar extension."""
        sd = SongData("song.KAR", None)
        assert sd.Ext == ".kar"

    def test_songdata_extension_mpg(self):
        """SongData should correctly extract .mpg extension."""
        sd = SongData("song.MPG", None)
        assert sd.Ext == ".mpg"

    def test_songdata_temp_filename_initially_none(self):
        """tempFilename should initially be None."""
        sd = SongData("song.cdg", b"data")
        assert sd.tempFilename is None


class TestSettingsStructDefaults:
    """Tests for SettingsStruct default values."""

    def test_version(self):
        s = SettingsStruct()
        assert s.Version == SETTINGS_VERSION

    def test_folder_list_empty(self):
        s = SettingsStruct()
        assert s.FolderList == []

    def test_cdg_extensions(self):
        s = SettingsStruct()
        assert ".cdg" in s.CdgExtensions

    def test_kar_extensions(self):
        s = SettingsStruct()
        assert ".kar" in s.KarExtensions
        assert ".mid" in s.KarExtensions

    def test_mpg_extensions(self):
        s = SettingsStruct()
        assert ".mpg" in s.MpgExtensions

    def test_look_inside_zips(self):
        s = SettingsStruct()
        assert s.LookInsideZips is True

    def test_read_titles_txt(self):
        s = SettingsStruct()
        assert s.ReadTitlesTxt is True

    def test_sample_rate(self):
        s = SettingsStruct()
        assert s.SampleRate == 44100

    def test_num_channels(self):
        s = SettingsStruct()
        assert s.NumChannels == 2

    def test_buffer_ms(self):
        s = SettingsStruct()
        assert s.BufferMs == 50

    def test_fullscreen_default(self):
        s = SettingsStruct()
        assert s.FullScreen is False

    def test_player_size_default(self):
        s = SettingsStruct()
        assert s.PlayerSize == (640, 480)

    def test_window_size_default(self):
        s = SettingsStruct()
        assert s.WindowSize == (640, 480)

    def test_cdg_zoom_default(self):
        s = SettingsStruct()
        assert s.CdgZoom == "int"

    def test_double_buf(self):
        s = SettingsStruct()
        assert s.DoubleBuf is True

    def test_hardware_surface(self):
        s = SettingsStruct()
        assert s.HardwareSurface is True

    def test_sync_delay(self):
        s = SettingsStruct()
        assert s.SyncDelayMs == 0

    def test_kar_encoding(self):
        s = SettingsStruct()
        assert s.KarEncoding == "cp1252"

    def test_kar_background_colour(self):
        s = SettingsStruct()
        assert s.KarBackgroundColour == (0, 0, 0)

    def test_kar_ready_colour(self):
        s = SettingsStruct()
        assert s.KarReadyColour == (255, 50, 50)

    def test_kar_sweep_colour(self):
        s = SettingsStruct()
        assert s.KarSweepColour == (255, 255, 255)

    def test_use_mp3_settings(self):
        s = SettingsStruct()
        assert s.UseMp3Settings is True

    def test_cdg_use_c(self):
        s = SettingsStruct()
        assert s.CdgUseC is True

    def test_mpg_native(self):
        s = SettingsStruct()
        assert s.MpgNative is True

    def test_split_vertically(self):
        s = SettingsStruct()
        assert s.SplitVertically is True

    def test_auto_play_list(self):
        s = SettingsStruct()
        assert s.AutoPlayList is True

    def test_kamikaze_default(self):
        s = SettingsStruct()
        assert s.Kamikaze is False

    def test_use_performer_name(self):
        s = SettingsStruct()
        assert s.UsePerformerName is False

    def test_encodings_class_var(self):
        """SettingsStruct should have Encodings class variable."""
        assert len(SettingsStruct.Encodings) > 0
        assert "utf-8" in SettingsStruct.Encodings

    def test_zoom_class_var(self):
        """SettingsStruct should have Zoom class variable."""
        assert len(SettingsStruct.Zoom) > 0
        assert "int" in SettingsStruct.Zoom

    def test_sample_rates_class_var(self):
        """SettingsStruct should have SampleRates class variable."""
        assert 44100 in SettingsStruct.SampleRates

    def test_filename_combinations(self):
        """SettingsStruct should have FileNameCombinations."""
        assert len(SettingsStruct.FileNameCombinations) > 0


class TestDBStruct:
    """Tests for DBStruct class."""

    def test_dbstruct_version(self):
        db = DBStruct()
        assert db.Version == DATABASE_VERSION


class TestBusyCancelDialogMethods:
    """Tests for BusyCancelDialog abstract methods."""

    def test_show(self):
        d = BusyCancelDialog()
        d.Show()  # Should not raise

    def test_set_progress(self):
        d = BusyCancelDialog()
        d.SetProgress("Scanning...", 0.5)  # Should not raise

    def test_destroy(self):
        d = BusyCancelDialog()
        d.Destroy()  # Should not raise

    def test_clicked_default(self):
        d = BusyCancelDialog()
        assert d.Clicked is False


class TestSongDBMethodsExtended:
    """Extended tests for SongDB methods."""

    def test_songdb_is_extension_valid_cdg(self):
        db = SongDB()
        # .cdg should always be valid
        assert db.IsExtensionValid(".cdg") is True

    def test_songdb_is_extension_valid_kar(self):
        db = SongDB()
        assert db.IsExtensionValid(".kar") is True

    def test_songdb_is_extension_valid_mid(self):
        db = SongDB()
        assert db.IsExtensionValid(".mid") is True

    def test_songdb_is_extension_valid_mpg(self):
        db = SongDB()
        assert db.IsExtensionValid(".mpg") is True

    def test_songdb_is_extension_invalid(self):
        db = SongDB()
        assert db.IsExtensionValid(".xyz") is False

    def test_songdb_is_extension_ignored(self):
        db = SongDB()
        db.Settings.IgnoredExtensions = [".mp3"]
        assert db.IsExtensionValid(".mp3") is False

    def test_songdb_get_save_directory_env(self):
        db = SongDB()
        with patch.dict(os.environ, {"PYKARAOKE_DIR": "/tmp/test_save"}):
            result = db.getSaveDirectory()
            assert result == "/tmp/test_save"

    def test_songdb_get_temp_directory_env(self):
        db = SongDB()
        with patch.dict(os.environ, {"PYKARAOKE_TEMP_DIR": "/tmp/test_temp"}):
            result = db.getTempDirectory()
            assert result == "/tmp/test_temp"

    def test_songdb_folder_add(self):
        db = SongDB()
        db.FolderAdd("/songs/folder1")
        assert "/songs/folder1" in db.Settings.FolderList

    def test_songdb_folder_add_no_dup(self):
        db = SongDB()
        db.FolderAdd("/songs/folder1")
        db.FolderAdd("/songs/folder1")
        assert db.Settings.FolderList.count("/songs/folder1") == 1

    def test_songdb_folder_del(self):
        db = SongDB()
        db.FolderAdd("/songs/folder1")
        db.FolderDel("/songs/folder1")
        assert "/songs/folder1" not in db.Settings.FolderList

    def test_songdb_zip_files_empty(self):
        db = SongDB()
        assert db.ZipFiles == []

    def test_songdb_database_dirty_initial(self):
        db = SongDB()
        assert db.databaseDirty is False

    def test_songdb_got_titles_initial(self):
        db = SongDB()
        assert db.GotTitles is False

    def test_songdb_got_artists_initial(self):
        db = SongDB()
        assert db.GotArtists is False

    def test_songdb_settings_is_settings_struct(self):
        db = SongDB()
        assert isinstance(db.Settings, SettingsStruct)

    def test_songdb_save_settings(self):
        db = SongDB()
        with tempfile.TemporaryDirectory() as tmpdir:
            db.SaveDir = tmpdir
            db.SaveSettings()
            assert os.path.exists(os.path.join(tmpdir, "settings.dat"))

    def test_songdb_save_and_load_settings(self):
        db = SongDB()
        with tempfile.TemporaryDirectory() as tmpdir:
            db.SaveDir = tmpdir
            db.Settings.SampleRate = 22050
            db.SaveSettings()
            # Load into a new DB
            db2 = SongDB()
            db2.SaveDir = tmpdir
            db2.load_settings(None)
            assert db2.Settings.SampleRate == 22050


class TestSongStructExtended:
    """Additional SongStruct tests."""

    def test_song_struct_type_cdg(self):
        settings = SettingsStruct()
        song = SongStruct("/songs/test.cdg", settings)
        assert song.Type == SongStruct.T_CDG

    def test_song_struct_type_kar(self):
        settings = SettingsStruct()
        song = SongStruct("/songs/test.kar", settings)
        assert song.Type == SongStruct.T_KAR

    def test_song_struct_type_mid(self):
        settings = SettingsStruct()
        song = SongStruct("/songs/test.mid", settings)
        assert song.Type == SongStruct.T_KAR

    def test_song_struct_type_mpg(self):
        settings = SettingsStruct()
        song = SongStruct("/songs/test.mpg", settings)
        assert song.Type == SongStruct.T_MPG

    def test_song_struct_display_filename(self):
        settings = SettingsStruct()
        song = SongStruct("/path/to/My Song.cdg", settings)
        assert song.DisplayFilename == "My Song.cdg"

    def test_song_struct_zip_stored_name(self):
        settings = SettingsStruct()
        song = SongStruct("/path/to/songs.zip", settings, zip_stored_name="inner.cdg")
        assert song.ZipStoredName == "inner.cdg"
        assert song.DisplayFilename == "inner.cdg"

    def test_song_struct_title(self):
        settings = SettingsStruct()
        song = SongStruct("/path/to/song.cdg", settings, title="My Title")
        assert song.Title == "My Title"

    def test_song_struct_artist(self):
        settings = SettingsStruct()
        song = SongStruct("/path/to/song.cdg", settings, artist="My Artist")
        assert song.Artist == "My Artist"

    def test_song_struct_default_title(self):
        settings = SettingsStruct()
        song = SongStruct("/path/to/song.cdg", settings)
        assert song.Title == ""

    def test_song_struct_default_artist(self):
        settings = SettingsStruct()
        song = SongStruct("/path/to/song.cdg", settings)
        assert song.Artist == ""

    def test_song_struct_same_songs(self):
        settings = SettingsStruct()
        song = SongStruct("/path/to/song.cdg", settings)
        assert song.sameSongs == []

    def test_song_struct_get_mark_key(self):
        settings = SettingsStruct()
        song = SongStruct("/path/to/song.cdg", settings)
        assert song.getMarkKey() == ("/path/to/song.cdg", None)

    def test_song_struct_get_mark_key_zip(self):
        settings = SettingsStruct()
        song = SongStruct("/path/to/songs.zip", settings, zip_stored_name="inner.cdg")
        assert song.getMarkKey() == ("/path/to/songs.zip", "inner.cdg")


class TestTitleStruct:
    """Tests for TitleStruct class."""

    def test_title_struct_init(self):
        ts = TitleStruct("/path/to/titles.txt")
        assert ts.Filepath == "/path/to/titles.txt"
        assert ts.songs == []
        assert ts.dirty is False

    def test_title_struct_zip(self):
        ts = TitleStruct("/path/to/archive.zip", zip_stored_name="titles.txt")
        assert ts.Filepath == "/path/to/archive.zip"
        assert ts.ZipStoredName == "titles.txt"


class TestAppYielderExtended:
    """Extended tests for AppYielder."""

    def test_yielder_yield_does_nothing(self):
        y = AppYielder()
        y.Yield()  # Abstract, should not raise

    def test_yielder_consider_yield(self):
        y = AppYielder()
        y.ConsiderYield()  # Should not raise
