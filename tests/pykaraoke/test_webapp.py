"""Tests for pykaraoke.webapp — the PyScript-facing API."""

import io
import struct
import zipfile

import pytest

from pykaraoke.webapp import KaraokeApp


def _minimal_midi() -> bytes:
    """A one-lyric MIDI file: tempo + lyric event + end-of-track."""
    header = b"MThd" + struct.pack(">LHHH", 6, 0, 1, 480)
    events = [
        b"\x00\xff\x51\x03\x07\xa1\x20",  # tempo 500000
        b"\x00\xff\x05\x03Hel",
        b"\x00\xff\x2f\x00",
    ]
    data = b"".join(events)
    return header + b"MTrk" + struct.pack(">L", len(data)) + data


class TestPersistence:
    def test_json_roundtrip(self):
        app = KaraokeApp()
        app.scan_files([{"name": "A - B.cdg", "path": "A - B.cdg", "size": 5}])
        payload = app.to_json()
        app2 = KaraokeApp()
        app2.from_json(payload)
        assert len(app2.library.songs) == 1
        assert app2.library.songs[0].title == "B"

    def test_from_json_garbage(self):
        app = KaraokeApp()
        app.from_json("not json")
        assert app.library.songs == []
        app.from_json(None)
        assert app.library.songs == []

    def test_from_json_non_dict_is_ignored(self):
        # Valid JSON that is not an object leaves the library untouched.
        app = KaraokeApp()
        app.scan_files([{"name": "A - B.cdg", "path": "A - B.cdg", "size": 0}])
        app.from_json("[1, 2, 3]")
        assert len(app.library.songs) == 1

    def test_from_json_clears_decoder_and_zip_caches(self):
        app = KaraokeApp()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("a.kar", b"x")
        app.scan_zip("s.zip", buf.getvalue())
        app.cdg_open("k", bytes(24))
        app.from_json(app.to_json())
        assert app._decoders == {}
        assert app._zip_names == {}


class TestScan:
    def test_scan_files(self):
        app = KaraokeApp()
        result = app.scan_files(
            [
                {"name": "Queen - B Rhapsody.cdg", "path": "Q/Queen - B Rhapsody.cdg", "size": 3},
                {"name": "Queen - B Rhapsody.mp3", "path": "Q/Queen - B Rhapsody.mp3", "size": 9},
                {"name": "notes.txt", "path": "Q/notes.txt", "size": 1},
            ]
        )
        assert result["total"] == 1
        song = app.library.songs[0]
        assert song.audio_name == "Queen - B Rhapsody.mp3"

    def test_scan_files_handles_bad_entries(self):
        app = KaraokeApp()
        result = app.scan_files([None, {"name": "A - B.kar"}, "junk"])
        assert result["total"] == 1

    def test_scan_files_skips_uncoercible_entries(self):
        # A size that cannot be int()-coerced is skipped, not fatal.
        app = KaraokeApp()
        result = app.scan_files(
            [
                {"name": "A - B.cdg", "size": "not-a-number"},
                {"name": "C - D.cdg", "size": 10},
            ]
        )
        assert result["total"] == 1
        assert app.library.songs[0].title == "D"

    def test_scan_zip(self):
        app = KaraokeApp()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("Artist/Title.kar", b"x")
        result = app.scan_zip("songs.zip", buf.getvalue())
        assert result["added"] == 1

    def test_read_zip_member(self):
        app = KaraokeApp()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("Artist/Title.kar", b"karbytes")
        app.scan_zip("songs.zip", buf.getvalue())
        assert app.read_zip_member("songs.zip", "Artist/Title.kar") == b"karbytes"
        assert app.read_zip_member("songs.zip", "missing.kar") is None
        assert app.read_zip_member("never-scanned.zip", "x.kar") is None
        assert app.read_zip_member("bad.zip", "x.kar") is None  # no bytes stored

    def test_read_zip_member_bad_zip_bytes(self):
        app = KaraokeApp()
        app.scan_zip("junk.zip", b"not a zip")
        assert app.read_zip_member("junk.zip", "x.kar") is None

    def test_zip_members(self):
        app = KaraokeApp()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("Artist/Title.kar", b"x")
            zf.writestr("Artist/Title.elrc", b"[00:01.00]hello\n")
        app.scan_zip("songs.zip", buf.getvalue())
        assert app.zip_members("songs.zip") == ["Artist/Title.kar", "Artist/Title.elrc"]
        assert app.zip_members("never-scanned.zip") == []

    def test_zip_members_after_rescan(self):
        # Re-scanning a zip invalidates the cached member list.
        app = KaraokeApp()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("a.kar", b"x")
        app.scan_zip("songs.zip", buf.getvalue())
        assert app.zip_members("songs.zip") == ["a.kar"]
        buf2 = io.BytesIO()
        with zipfile.ZipFile(buf2, "w") as zf:
            zf.writestr("a.kar", b"x")
            zf.writestr("b.kar", b"y")
        app.scan_zip("songs.zip", buf2.getvalue())
        assert app.zip_members("songs.zip") == ["a.kar", "b.kar"]

    def test_zip_members_bad_zip_returns_empty(self):
        # A corrupt zip yields [] and is cached as such (no retry storm).
        app = KaraokeApp()
        app.scan_zip("junk.zip", b"not a zip")
        assert app.zip_members("junk.zip") == []
        assert app.zip_members("junk.zip") == []

    def test_zip_members_caches_namelist(self):
        # A second call hits the cache instead of re-opening the zip.
        app = KaraokeApp()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("a.kar", b"x")
        app.scan_zip("songs.zip", buf.getvalue())
        assert app.zip_members("songs.zip") == ["a.kar"]
        assert "songs.zip" in app._zip_names
        assert app.zip_members("songs.zip") == ["a.kar"]


class TestSearch:
    def test_search(self):
        app = KaraokeApp()
        app.scan_files([{"name": "Queen - Bohemian Rhapsody.cdg", "path": "x.cdg", "size": 0}])
        res = app.search("bohemian")
        assert len(res["results"]) == 1
        assert res["results"][0]["artist"] == "Queen"

    def test_library_songs(self):
        app = KaraokeApp()
        app.scan_files([{"name": "A - B.cdg", "path": "A - B.cdg", "size": 0}])
        assert len(app.library_songs()["songs"]) == 1

    def test_song_lookup(self):
        app = KaraokeApp()
        app.scan_files([{"name": "A - B.cdg", "path": "A - B.cdg", "size": 0}])
        song = app.library.songs[0]
        assert app.song(song.id)["title"] == "B"
        assert app.song("nope") is None


class TestSettings:
    def test_get_and_set(self):
        app = KaraokeApp()
        s = app.get_settings()
        assert s["volume"] == 0.75
        updated = app.set_settings({"volume": 0.4, "cdg_zoom": "soft", "sort": "artist"})
        assert updated["volume"] == 0.4
        assert updated["cdg_zoom"] == "soft"
        assert updated["sort"] == "artist"
        assert app.library.settings.sort == "artist"

    def test_file_name_type_accepts_spaced_disc_track(self):
        app = KaraokeApp()
        updated = app.set_settings({"file_name_type": 4})
        assert updated["file_name_type"] == 4
        app.scan_files(
            [
                {
                    "name": "CB30055-15 - Switchfoot - Stars.cdg",
                    "path": "/lib/CB30055-15 - Switchfoot - Stars.cdg",
                    "size": 100,
                }
            ]
        )
        songs = app.library_songs()["songs"]
        assert songs[0]["artist"] == "Switchfoot"
        assert songs[0]["title"] == "Stars"
        assert songs[0]["disc"] == "CB30055"

    def test_set_settings_boolean_and_list_keys(self):
        app = KaraokeApp()
        updated = app.set_settings(
            {
                "derive_song_info": False,
                "exclude_non_matching": True,
                "look_inside_zips": True,
                "folders": ["/lib", "/extra"],
                "include_patterns": ["*.cdg", "*.kar"],
            }
        )
        assert updated["derive_song_info"] is False
        assert updated["exclude_non_matching"] is True
        assert updated["look_inside_zips"] is True
        assert updated["folders"] == ["/lib", "/extra"]
        assert updated["include_patterns"] == ["*.cdg", "*.kar"]


class TestScanReportAPI:
    def test_report_after_mixed_scan(self):
        app = KaraokeApp()
        app.scan_files(
            [
                {"name": "notes.txt", "path": "notes.txt", "size": 1},
                {"name": "A - B.cdg", "path": "A - B.cdg", "size": 0},
            ]
        )
        report = app.scan_report()
        assert report["counts"]["unsupported"] == 1
        assert report["entries"] == [{"category": "unsupported", "path": "notes.txt"}]

    def test_clearing(self):
        app = KaraokeApp()
        app.scan_files([{"name": "notes.txt", "path": "notes.txt", "size": 1}])
        assert app.scan_report()["counts"]["unsupported"] == 1
        empty = app.clear_scan_report()
        assert empty["counts"]["unsupported"] == 0
        assert empty["entries"] == []
        assert app.scan_report()["entries"] == []


class TestPatternSettingsAPI:
    def test_patterns_round_trip_and_apply(self):
        app = KaraokeApp()
        updated = app.set_settings({"exclude_patterns": ["*_(vocal)_*"]})
        assert updated["exclude_patterns"] == ["*_(vocal)_*"]
        assert app.get_settings()["exclude_patterns"] == ["*_(vocal)_*"]
        app.scan_files(
            [
                {
                    "name": "Song - Artist_(Vocal)_.cdg",
                    "path": "Song - Artist_(Vocal)_.cdg",
                    "size": 0,
                },
                {"name": "Plain - Song.cdg", "path": "Plain - Song.cdg", "size": 0},
            ]
        )
        songs = app.library_songs()["songs"]
        assert len(songs) == 1
        assert songs[0]["title"] == "Song"
        assert app.scan_report()["counts"]["filtered"] == 1


class TestCdg:
    def test_open_update_close(self):
        app = KaraokeApp()
        # Memory preset packet: 24 bytes.
        packet = bytes(
            [0x09, 0x01, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        )
        key = app.cdg_open("song1", packet)
        assert key == "song1"
        upd = app.cdg_update(key, 50)
        assert upd is not None
        assert upd["border"] is not None
        assert len(upd["tiles"]) == 24
        app.cdg_close(key)
        assert app.cdg_update(key, 50) is None

    def test_cdg_seek(self):
        app = KaraokeApp()
        packet = bytes([0x09, 0x01, 0, 0, 0, 3] + [0] * 18)
        key = app.cdg_open("s", packet)
        app.cdg_update(key, 0)
        app.cdg_seek(key, 1000)
        upd = app.cdg_update(key, 1000)
        assert upd is not None
        assert len(upd["tiles"]) == 24

    def test_cdg_seek_unknown_key_is_noop(self):
        app = KaraokeApp()
        app.cdg_seek("missing", 100)  # must not raise

    def test_cdg_open_invalid_data_raises(self):
        app = KaraokeApp()
        with pytest.raises(ValueError):
            app.cdg_open("s", None)

    def test_cdg_packet_count(self):
        app = KaraokeApp()
        assert app.cdg_packet_count(bytes(24 * 5)) == 5


class TestMidi:
    def test_parse_midi_invalid(self):
        app = KaraokeApp()
        res = app.parse_midi(b"garbage")
        assert "error" in res

    def test_parse_midi_bad_input(self):
        app = KaraokeApp()
        assert "error" in app.parse_midi(None)

    def test_parse_midi_success(self):
        app = KaraokeApp()
        res = app.parse_midi(_minimal_midi())
        assert "error" not in res
        assert [s["text"] for s in res["lyrics"]] == ["Hel"]
        assert "notes" in res


class TestLrc:
    def test_parse_lrc(self):
        app = KaraokeApp()
        res = app.parse_lrc("[ti:Inside Out]\n[00:12.34]Hello world\n")
        assert res["meta"]["ti"] == "Inside Out"
        assert res["lyrics"][0] == {"ms": 12340, "text": "Hello world", "type": 0, "line": 0}

    def test_parse_lrc_enhanced(self):
        # Word-level timestamps pass through the bridge unchanged.
        app = KaraokeApp()
        res = app.parse_lrc("[00:12.00]Word <00:12.50> by\n")
        assert [s["ms"] for s in res["lyrics"]] == [12000, 12500]

    def test_parse_lrc_invalid(self):
        app = KaraokeApp()
        assert "error" in app.parse_lrc("no timestamps here")
        assert "error" in app.parse_lrc("")
        assert "error" in app.parse_lrc(None)

    def test_parse_lrc_with_elrc(self):
        # A companion .elrc upgrades the line to word-level timing.
        app = KaraokeApp()
        res = app.parse_lrc(
            "[00:01.00]Hello brave new world\n",
            "[00:01.20]Hello\n[00:01.70]brave\n[00:02.20]new\n[00:02.90]world\n",
        )
        assert res["elrc"] is True
        assert [(s["ms"], s["text"]) for s in res["lyrics"]] == [
            (1200, "Hello"),
            (1700, "brave"),
            (2200, "new"),
            (2900, "world"),
        ]

    def test_parse_lrc_with_useless_elrc_keeps_line_timing(self):
        # Missing/garbage companion files are never an error.
        app = KaraokeApp()
        line_timing = [{"ms": 1000, "text": "Hello world", "type": 0, "line": 0}]
        for elrc in (None, "", "no timestamps here", "[00:01.00]zzz\n"):
            res = app.parse_lrc("[00:01.00]Hello world\n", elrc)
            assert "error" not in res
            assert "elrc" not in res
            assert res["lyrics"] == line_timing


class TestDuet:
    def test_parse_lrc_exposes_singers_and_line_parts(self):
        # The API passes duet information straight through to the UI.
        app = KaraokeApp()
        res = app.parse_lrc(
            "[pa:Alice]\n[pb:Bob]\n[00:01.00][a]first\n[00:05.00][b]second\n[00:09.00][ab]shared\n"
        )
        assert res["parts"] == {"a": "Alice", "b": "Bob"}
        assert [s.get("part") for s in res["lyrics"]] == ["a", "b", "ab"]

    def test_parse_lrc_solo_payload_is_unchanged(self):
        app = KaraokeApp()
        res = app.parse_lrc("[00:01.00]Hello world\n")
        assert "parts" not in res
        assert res["lyrics"][0] == {"ms": 1000, "text": "Hello world", "type": 0, "line": 0}

    def test_parse_lrc_duet_survives_an_elrc_merge(self):
        app = KaraokeApp()
        res = app.parse_lrc(
            "[00:01.00][a]Hello world\n",
            "[00:01.20]Hello\n[00:01.70]world\n",
        )
        assert res["elrc"] is True
        assert [s["text"] for s in res["lyrics"]] == ["Hello", "world"]
        assert [s.get("part") for s in res["lyrics"]] == ["a", "a"]


class TestInvalidData:
    def test_scan_zip_invalid_bytes(self):
        app = KaraokeApp()
        assert app.scan_zip("x.zip", None)["added"] == 0


class TestZipSlipSafety:
    """Zip member names never reach the filesystem (no extract path exists).

    Member names are used only as virtual path strings and in-memory
    ``zf.read()`` keys, so traversal-style names stay inert.
    """

    def test_traversal_member_names_stay_in_memory(self, tmp_path, monkeypatch):
        app = KaraokeApp()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../../evil - payload.kar", b"karbytes")
            zf.writestr("..\\..\\win - payload.cdg", b"cdgbytes")
        monkeypatch.chdir(tmp_path)
        result = app.scan_zip("evil.zip", buf.getvalue())
        assert result["added"] == 2
        # Bytes are only served from the in-memory archive.
        assert app.read_zip_member("evil.zip", "../../evil - payload.kar") == b"karbytes"
        # Nothing was written outside the (empty) working directory.
        assert list(tmp_path.iterdir()) == []
        assert not (tmp_path / "evil - payload.kar").exists()
        assert not (tmp_path.parent / "evil - payload.kar").exists()


class TestRelocationAPI:
    def test_replace_scan(self):
        app = KaraokeApp()
        app.scan_files([{"name": "Old - Song.cdg", "path": "Old - Song.cdg", "size": 0}])
        app.scan_files(
            [{"name": "New - Song.cdg", "path": "New - Song.cdg", "size": 0}],
            replace=True,
        )
        songs = app.library_songs()["songs"]
        assert len(songs) == 1
        assert songs[0]["artist"] == "New"

    def test_default_stays_additive(self):
        app = KaraokeApp()
        app.scan_files([{"name": "A - One.cdg", "path": "A - One.cdg", "size": 0}])
        app.scan_files([{"name": "B - Two.cdg", "path": "B - Two.cdg", "size": 0}])
        assert len(app.library_songs()["songs"]) == 2

    def test_prune(self):
        app = KaraokeApp()
        app.scan_files(
            [
                {"name": "Keep - One.cdg", "path": "Keep - One.cdg", "size": 0},
                {"name": "Drop - Two.cdg", "path": "Drop - Two.cdg", "size": 0},
            ]
        )
        result = app.prune_songs(["keep - one.cdg"])
        assert result["pruned"] == 1
        assert result["total"] == 1
        assert len(app.library_songs()["songs"]) == 1

    def test_prune_empty_is_noop(self):
        app = KaraokeApp()
        app.scan_files([{"name": "A - B.cdg", "path": "A - B.cdg", "size": 0}])
        assert app.prune_songs([])["pruned"] == 0
        assert len(app.library_songs()["songs"]) == 1

    def test_prune_non_iterable_is_noop(self):
        # A non-iterable known list is treated as empty, not an error.
        app = KaraokeApp()
        app.scan_files([{"name": "A - B.cdg", "path": "A - B.cdg", "size": 0}])
        assert app.prune_songs(42)["pruned"] == 0
        assert len(app.library_songs()["songs"]) == 1


class TestImportExportAPI:
    def test_round_trip_through_page(self):
        app = KaraokeApp()
        app.scan_files(
            [
                {
                    "name": "Queen - Bohemian Rhapsody.cdg",
                    "path": "Queen - Bohemian Rhapsody.cdg",
                    "size": 0,
                }
            ]
        )
        payload = app.export_json()
        assert app.import_json(payload) == {"ok": True}
        assert len(app.library_songs()["songs"]) == 1

    def test_corrupt_payload(self):
        app = KaraokeApp()
        app.scan_files([{"name": "A - B.cdg", "path": "A - B.cdg", "size": 0}])
        result = app.import_json("not json")
        assert result["ok"] is False
        assert "error" in result
        assert len(app.library_songs()["songs"]) == 1
