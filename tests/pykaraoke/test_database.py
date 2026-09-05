"""Tests for pykaraoke.database — the song library."""

import io
import zipfile

from pykaraoke.database import Settings, Song, SongLibrary, kind_for_name


def _file(name, path=None, size=0):
    return {"name": name, "path": path or name, "size": size}


class TestKindForName:
    def test_kinds(self):
        assert kind_for_name("a.cdg") == "cdg"
        assert kind_for_name("a.kar") == "kar"
        assert kind_for_name("a.mid") == "kar"
        assert kind_for_name("a.mpg") == "mpg"
        assert kind_for_name("a.avi") == "mpg"

    def test_non_song(self):
        assert kind_for_name("a.mp3") is None
        assert kind_for_name("a.txt") is None
        assert kind_for_name("noext") is None


class TestScan:
    def test_scan_parses_space_dash_names(self):
        lib = SongLibrary()
        result = lib.scan([_file("Queen - Bohemian Rhapsody.cdg")])
        assert result["total"] == 1
        song = lib.songs[0]
        assert song.title == "Bohemian Rhapsody"
        assert song.artist == "Queen"
        assert song.kind == "cdg"

    def test_scan_pairs_cdg_with_audio(self):
        lib = SongLibrary()
        lib.scan(
            [
                _file("Queen - Bohemian Rhapsody.cdg"),
                _file("Queen - Bohemian Rhapsody.mp3"),
            ]
        )
        assert len(lib.songs) == 1
        assert lib.songs[0].audio_name == "Queen - Bohemian Rhapsody.mp3"

    def test_scan_pairs_audio_inside_subfolder(self):
        # The audio file may live next to the cdg with the same stem.
        lib = SongLibrary()
        lib.scan(
            [
                _file("Song.cdg", path="Folder/Song.cdg"),
                _file("Song.mp3", path="Folder/Song.mp3"),
            ]
        )
        assert lib.songs[0].audio_name == "Song.mp3"

    def test_scan_ignores_unsupported_files(self):
        lib = SongLibrary()
        lib.scan(
            [
                _file("notes.txt"),
                _file("cover.jpg"),
                _file("Artist - Title.kar"),
            ]
        )
        assert len(lib.songs) == 1
        assert lib.songs[0].kind == "kar"

    def test_scan_lrc_song(self):
        lib = SongLibrary()
        lib.scan([_file("Inside Out.lrc"), _file("Inside Out.mp3")])
        assert len(lib.songs) == 1
        song = lib.songs[0]
        assert song.kind == "lrc"
        assert song.audio_name == "Inside Out.mp3"

    def test_scan_lcr_extension(self):
        # .lcr is the same LRC lyrics format under another extension.
        lib = SongLibrary()
        lib.scan([_file("Song.lcr"), _file("Song.ogg")])
        assert lib.songs[0].kind == "lrc"
        assert lib.songs[0].audio_name == "Song.ogg"

    def test_scan_pairs_lrc_with_track_number_and_suffix(self):
        # Normalized pairing: "01 - Inside Out.lrc" matches
        # "Inside Out - Karaoke.mp3" (both normalize to the same key).
        lib = SongLibrary()
        lib.scan(
            [
                _file("01 - Inside Out.lrc"),
                _file("Inside Out - Karaoke.mp3"),
            ]
        )
        assert len(lib.songs) == 1
        assert lib.songs[0].audio_name == "Inside Out - Karaoke.mp3"

    def test_rescan_updates_without_duplicates(self):
        lib = SongLibrary()
        files = [_file("A - B.cdg"), _file("C - D.kar")]
        lib.scan(files)
        lib.scan(files)
        assert len(lib.songs) == 2

    def test_same_basename_different_paths(self):
        lib = SongLibrary()
        lib.scan([_file("A - B.cdg", path="One/A - B.cdg")])
        lib.scan([_file("A - B.cdg", path="Two/A - B.cdg")])
        # Same basename in different folders are distinct songs.
        assert len(lib.songs) == 2

    def test_rescan_same_path_no_duplicates(self):
        lib = SongLibrary()
        files = [_file("A - B.cdg", path="One/A - B.cdg")]
        lib.scan(files)
        lib.scan(files)
        assert len(lib.songs) == 1

    def test_exclude_non_matching(self):
        lib = SongLibrary()
        lib.settings.exclude_non_matching = True
        lib.scan([_file("JustATitle.cdg")])  # no artist -> excluded
        assert len(lib.songs) == 0

    def test_scan_zip(self):
        lib = SongLibrary()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("Artist/Title.kar", b"data")
            zf.writestr("readme.txt", b"nope")
        lib.scan_zip("collection.zip", buf.getvalue())
        assert len(lib.songs) == 1
        song = lib.songs[0]
        assert song.zip_name == "collection.zip"
        assert song.artist == "Artist"
        assert song.title == "Title"
        assert song.kind == "kar"

    def test_scan_zip_bad_zip(self):
        lib = SongLibrary()
        assert lib.scan_zip("bad.zip", b"not a zip") == {"added": 0, "total": 0}

    def test_scan_zip_disabled(self):
        lib = SongLibrary()
        lib.settings.look_inside_zips = False
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("a.kar", b"x")
        assert lib.scan_zip("c.zip", buf.getvalue())["added"] == 0


class TestSearch:
    def _lib(self):
        lib = SongLibrary()
        lib.scan(
            [
                _file("Queen - Bohemian Rhapsody.cdg"),
                _file("Queen - We Are The Champions.kar"),
                _file("AC-DC - Highway to Hell.mpg"),
                _file("Adele - Hello.cdg"),
            ]
        )
        return lib

    def test_search_matches_title(self):
        lib = self._lib()
        results = lib.search("bohemian")
        assert len(results) == 1
        assert results[0].artist == "Queen"

    def test_search_matches_artist(self):
        lib = self._lib()
        results = lib.search("queen")
        assert len(results) == 2

    def test_search_multiple_terms(self):
        lib = self._lib()
        results = lib.search("queen champions")
        assert len(results) == 1
        assert results[0].title == "We Are The Champions"

    def test_search_empty_query(self):
        lib = self._lib()
        assert lib.search("") == []
        assert lib.search("   ") == []

    def test_search_no_matches(self):
        lib = self._lib()
        assert lib.search("zzz") == []

    def test_search_case_insensitive(self):
        lib = self._lib()
        assert len(lib.search("BOHEMIAN")) == 1


class TestSort:
    def _lib(self):
        lib = SongLibrary()
        lib.scan(
            [
                _file("The Beatles - Let It Be.kar"),
                _file("Adele - Hello.cdg"),
                _file("Queen - A Night At The Opera.cdg"),
            ]
        )
        return lib

    def test_sort_by_title_strips_articles(self):
        lib = self._lib()
        lib.sort_by("title")
        titles = [s.title for s in lib.songs]
        assert titles == ["Hello", "Let It Be", "A Night At The Opera"]

    def test_sort_by_artist(self):
        lib = self._lib()
        lib.sort_by("artist")
        # Articles are stripped for sorting: "The Beatles" sorts under B.
        assert [s.artist for s in lib.songs] == ["Adele", "The Beatles", "Queen"]

    def test_sort_by_filename(self):
        lib = self._lib()
        lib.sort_by("filename")
        names = [s.filename for s in lib.songs]
        assert names == sorted(names)

    def test_invalid_sort_falls_back(self):
        lib = self._lib()
        lib.sort_by("bogus")
        assert lib.settings.sort == "filename"


class TestPersistence:
    def test_roundtrip(self):
        lib = SongLibrary()
        lib.scan(
            [
                _file("Queen - Bohemian Rhapsody.cdg"),
                _file("Queen - Bohemian Rhapsody.mp3"),
            ]
        )
        lib.settings.volume = 0.5
        lib.settings.folders = ["/music"]
        restored = SongLibrary.from_dict(lib.to_dict())
        assert len(restored.songs) == 1
        song = restored.songs[0]
        assert song.title == "Bohemian Rhapsody"
        assert song.audio_name == "Queen - Bohemian Rhapsody.mp3"
        assert restored.settings.volume == 0.5
        assert restored.settings.folders == ["/music"]

    def test_from_dict_wrong_version(self):
        lib = SongLibrary.from_dict({"version": 1, "songs": []})
        assert lib.songs == []


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.volume == 0.75
        assert s.sort == "filename"
        assert s.cdg_zoom == "int"

    def test_roundtrip(self):
        s = Settings(volume=0.3, folders=["a"], cdg_zoom="soft", sort="artist")
        s2 = Settings.from_dict(s.to_dict())
        assert s2.volume == 0.3
        assert s2.folders == ["a"]
        assert s2.cdg_zoom == "soft"
        assert s2.sort == "artist"

    def test_from_dict_defaults(self):
        s = Settings.from_dict({})
        assert s.volume == 0.75


class TestSong:
    def test_to_from_dict(self):
        song = Song(
            id="x",
            title="T",
            artist="A",
            filename="A - T.cdg",
            kind="cdg",
            path="A - T.cdg",
            audio_name="A - T.mp3",
            size=10,
        )
        restored = Song.from_dict(song.to_dict())
        assert restored == song
