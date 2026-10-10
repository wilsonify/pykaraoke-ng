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


# ===========================================================================
# Scan diagnostics, include/exclude patterns, zip-member cache
# ===========================================================================


def _entry(name, path=None, size=100):
    return {"name": name, "path": path or name, "size": size}


def _make_zip_bytes(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for member in members:
            zf.writestr(member, b"x")
    return buf.getvalue()


def _make_unsupported_compression_zip():
    """Build a stored zip whose headers claim an unreadable method."""
    data = bytearray(_make_zip_bytes(["A - B.kar"]))
    # Local file header: method at offset 8; central directory: offset 10.
    data[8:10] = (99).to_bytes(2, "little")
    idx = data.find(b"PK\x01\x02")
    assert idx != -1
    data[idx + 10 : idx + 12] = (99).to_bytes(2, "little")
    return bytes(data)


class TestPatternFilters:
    def test_exclude_pattern_filters_loose_file(self):
        lib = SongLibrary()
        lib.settings.exclude_patterns = ["*_(vocal)_*"]
        lib.scan([_entry("Song - Artist_(Vocal)_.cdg"), _entry("Good - Song.cdg")])
        titles = {s.title for s in lib.songs}
        assert "Artist_(Vocal)_" not in titles  # filtered file's parsed title
        assert "Song" in titles  # kept file: artist "Good", title "Song"
        report = lib.scan_report()
        assert report["counts"]["filtered"] == 1

    def test_include_pattern_narrows_scan(self):
        lib = SongLibrary()
        lib.settings.include_patterns = ["CB*.cdg"]
        lib.scan([_entry("CB1 - Song.cdg"), _entry("Artist - Other.cdg")])
        assert len(lib.songs) == 1
        assert lib.songs[0].title == "Song"

    def test_exclude_beats_include(self):
        lib = SongLibrary()
        lib.settings.include_patterns = ["CB*.cdg"]
        lib.settings.exclude_patterns = ["*live*"]
        lib.scan([_entry("CB1 - Song Live.cdg"), _entry("CB2 - Song.cdg")])
        assert [s.title for s in lib.songs] == ["Song"]

    def test_empty_include_means_everything(self):
        lib = SongLibrary()
        lib.scan([_entry("A - B.cdg"), _entry("C - D.kar")])
        assert len(lib.songs) == 2

    def test_patterns_apply_inside_zips(self):
        lib = SongLibrary()
        lib.settings.exclude_patterns = ["*_(vocal)_*"]
        lib.scan_zip(
            "pack.zip",
            _make_zip_bytes(["Artist - Song_(Vocal)_.kar", "Artist - Song.kar"]),
        )
        assert [s.title for s in lib.songs] == ["Song"]
        report = lib.scan_report()
        assert report["counts"]["filtered"] == 1

    def test_patterns_roundtrip_through_settings(self):
        s = Settings(include_patterns=["CB*"], exclude_patterns=["*demo*"])
        s2 = Settings.from_dict(s.to_dict())
        assert s2.include_patterns == ["CB*"]
        assert s2.exclude_patterns == ["*demo*"]

    def test_odd_pattern_does_not_break_scan(self):
        lib = SongLibrary()
        lib.settings.exclude_patterns = ["[unclosed"]
        lib.scan([_entry("A - [unclosed].cdg"), _entry("B - Safe.cdg")])
        # fnmatch treats an unmatched bracket literally and matches the whole
        # name, so nothing is filtered and no exception escapes the scan.
        assert len(lib.songs) == 2


class TestScanReport:
    def test_mixed_batch_reports_categories(self):
        lib = SongLibrary()
        lib.settings.exclude_patterns = ["*_(vocal)_*"]
        lib.scan(
            [
                _entry("notes.txt"),
                _entry("Song_(Vocal)_.cdg"),
                _entry("Queen - Bohemian Rhapsody.cdg"),
            ]
        )
        counts = lib.scan_report()["counts"]
        assert counts["unsupported"] == 1
        assert counts["filtered"] == 1
        assert len(lib.songs) == 1

    def test_report_is_clearable(self):
        lib = SongLibrary()
        lib.scan([_entry("notes.txt")])
        assert lib.scan_report()["counts"]["unsupported"] == 1
        lib.clear_scan_report()
        report = lib.scan_report()
        assert report["entries"] == []
        assert report["counts"]["unsupported"] == 0

    def test_reporting_never_aborts_batch(self):
        lib = SongLibrary()
        lib.scan_zip("bad.zip", b"not a zip at all")
        lib.scan([_entry("Queen - Bohemian Rhapsody.cdg")])
        assert lib.scan_report()["counts"]["corrupt_archive"] == 1
        assert len(lib.songs) == 1

    def test_corrupt_archive_reported(self):
        lib = SongLibrary()
        lib.scan_zip("bad.zip", b"\x00\x01\x02")
        assert lib.scan_report()["counts"]["corrupt_archive"] == 1

    def test_unsupported_compression_reported(self):
        lib = SongLibrary()
        lib.scan_zip("future.zip", _make_unsupported_compression_zip())
        assert lib.scan_report()["counts"]["unsupported_compression"] == 1
        assert lib.songs == []

    def test_parse_failure_reported_not_raised(self, monkeypatch):
        from pykaraoke import database

        class _Boom:
            def parse(self, name):
                raise RuntimeError("boom")

            def parse_zip_path(self, name):
                raise RuntimeError("boom")

        monkeypatch.setattr(database, "FilenameParser", lambda **kwargs: _Boom())
        lib = SongLibrary()
        lib.scan([_entry("A - B.cdg")])
        assert lib.scan_report()["counts"]["parse_failure"] == 1
        assert len(lib.songs) == 1  # kept as title-only

    def test_report_entries_are_deduplicated_across_rebuilds(self):
        lib = SongLibrary()
        lib.scan([_entry("A - B.cdg")])
        lib.scan([_entry("C - D.cdg")])  # rebuild re-visits the first file
        entries = lib.scan_report()["entries"]
        assert entries == []


class TestZipMemberCache:
    def test_zip_songs_survive_later_loose_scan(self):
        lib = SongLibrary()
        lib.scan_zip("pack.zip", _make_zip_bytes(["Artist - Title.kar"]))
        assert len(lib.songs) == 1
        lib.scan([_entry("Other - Song.cdg")])
        zip_titles = [s.title for s in lib.songs if s.zip_name == "pack.zip"]
        assert zip_titles == ["Title"]

    def test_zip_survive_settings_triggered_rebuild(self):
        lib = SongLibrary()
        lib.scan_zip("pack.zip", _make_zip_bytes(["Artist - Title.kar"]))
        lib.settings.volume = 0.5
        lib._rebuild()  # what a settings change may trigger
        assert any(s.zip_name == "pack.zip" for s in lib.songs)

    def test_zip_cache_rebuilt_from_persistence(self):
        lib = SongLibrary()
        lib.scan_zip("pack.zip", _make_zip_bytes(["Artist - Title.kar"]))
        restored = SongLibrary.from_dict(lib.to_dict())
        restored.scan([_entry("Other - Song.cdg")])
        zip_titles = [s.title for s in restored.songs if s.zip_name == "pack.zip"]
        assert zip_titles == ["Title"]

    def test_rescanning_same_zip_is_idempotent(self):
        lib = SongLibrary()
        data = _make_zip_bytes(["Artist - Title.kar"])
        lib.scan_zip("pack.zip", data)
        lib.scan_zip("pack.zip", data)
        assert len([s for s in lib.songs if s.zip_name == "pack.zip"]) == 1


class TestReplaceScan:
    def test_replace_clears_prior_songs_and_keeps_settings(self):
        lib = SongLibrary()
        lib.settings.volume = 0.5
        lib.scan([_entry("Old - Song.cdg")])
        lib.scan([_entry("New - Song.cdg")], replace=True)
        assert [s.artist for s in lib.songs] == ["New"]
        assert lib.settings.volume == 0.5

    def test_default_scan_stays_additive(self):
        lib = SongLibrary()
        lib.scan([_entry("A - One.cdg")])
        lib.scan([_entry("B - Two.cdg")])
        assert len(lib.songs) == 2

    def test_replace_clears_zip_expansions(self):
        lib = SongLibrary()
        lib.scan_zip("pack.zip", _make_zip_bytes(["Artist - Title.kar"]))
        assert any(s.zip_name == "pack.zip" for s in lib.songs)
        lib.scan([_entry("X - Y.cdg")], replace=True)
        assert all(s.zip_name is None for s in lib.songs)

    def test_replace_with_empty_batch_clears_library(self):
        lib = SongLibrary()
        lib.scan([_entry("Old - Song.cdg")])
        result = lib.scan([], replace=True)
        assert lib.songs == []
        assert result == {"added": 0, "total": 0}


class TestPrune:
    def test_prune_removes_stale_paths(self):
        lib = SongLibrary()
        lib.scan([_entry("Keep - One.cdg"), _entry("Drop - Two.cdg")])
        removed = lib.prune_songs(["keep - one.cdg"])
        assert removed == 1
        assert [s.artist for s in lib.songs] == ["Keep"]

    def test_prune_removes_stale_zip_songs(self):
        lib = SongLibrary()
        lib.scan_zip("pack.zip", _make_zip_bytes(["Artist - One.kar", "Artist - Two.kar"]))
        zip_songs = [s for s in lib.songs if s.zip_name == "pack.zip"]
        assert len(zip_songs) == 2
        keep_path = zip_songs[0].path
        removed = lib.prune_songs([keep_path])
        assert removed == 1
        remaining = [s for s in lib.songs if s.zip_name == "pack.zip"]
        assert [s.path for s in remaining] == [keep_path]

    def test_empty_known_set_is_noop(self):
        lib = SongLibrary()
        lib.scan([_entry("A - One.cdg")])
        assert lib.prune_songs([]) == 0
        assert len(lib.songs) == 1

    def test_prune_updates_zip_cache(self):
        lib = SongLibrary()
        lib.scan_zip("pack.zip", _make_zip_bytes(["Artist - One.kar", "Artist - Two.kar"]))
        keep = next(s for s in lib.songs if s.zip_name == "pack.zip").path
        lib.prune_songs([keep])
        lib.scan([_entry("Other - Song.cdg")])  # triggers rebuild from cache
        assert len([s for s in lib.songs if s.zip_name == "pack.zip"]) == 1


class TestExportImport:
    def test_envelope_shape(self):
        import json

        lib = SongLibrary()
        lib.scan([_entry("Queen - Bohemian Rhapsody.cdg")])
        payload = json.loads(lib.export_json())
        assert payload["schema"] == 1
        assert payload["library"] == lib.to_dict()

    def test_round_trip(self):
        lib = SongLibrary()
        lib.settings.folders = ["D:/Karaoke"]
        lib.settings.volume = 0.4
        lib.scan([_entry("Queen - Bohemian Rhapsody.cdg", path="root/Queen - Bohemian Rhapsody.cdg")])
        restored = SongLibrary()
        result = restored.import_json(lib.export_json())
        assert result == {"ok": True}
        assert [s.to_dict() for s in restored.songs] == [s.to_dict() for s in lib.songs]
        assert restored.settings.folders == ["D:/Karaoke"]
        assert restored.settings.volume == 0.4

    def test_bare_dict_accepted(self):
        import json

        lib = SongLibrary()
        lib.scan([_entry("A - B.cdg")])
        restored = SongLibrary()
        assert restored.import_json(json.dumps(lib.to_dict())) == {"ok": True}
        assert len(restored.songs) == 1

    def test_malformed_json_leaves_state_intact(self):
        lib = SongLibrary()
        lib.scan([_entry("A - B.cdg")])
        result = lib.import_json("not json {")
        assert result["ok"] is False
        assert "error" in result
        assert len(lib.songs) == 1

    def test_unrecognised_schema_rejected(self):
        import json

        lib = SongLibrary()
        lib.scan([_entry("A - B.cdg")])
        payload = json.dumps({"format": "pykaraoke-ng-library", "schema": 99, "library": {}})
        result = lib.import_json(payload)
        assert result["ok"] is False
        assert len(lib.songs) == 1

    def test_unknown_library_version_rejected(self):
        import json

        lib = SongLibrary()
        lib.scan([_entry("A - B.cdg")])
        result = lib.import_json(json.dumps({"version": 99, "songs": [], "settings": {}}))
        assert result["ok"] is False
        assert len(lib.songs) == 1

    def test_non_object_payload_rejected(self):
        lib = SongLibrary()
        lib.scan([_entry("A - B.cdg")])
        assert lib.import_json("[1, 2, 3]")["ok"] is False
        assert len(lib.songs) == 1
