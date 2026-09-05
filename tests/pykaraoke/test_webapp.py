"""Tests for pykaraoke.webapp — the PyScript-facing API."""

import io
import zipfile

from pykaraoke.webapp import KaraokeApp


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


class TestCdg:
    def test_open_update_close(self):
        app = KaraokeApp()
        # Memory preset packet: 24 bytes.
        packet = bytes([0x09, 0x01, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
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
        assert upd is not None and len(upd["tiles"]) == 24

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


class TestInvalidData:
    def test_scan_zip_invalid_bytes(self):
        app = KaraokeApp()
        assert app.scan_zip("x.zip", None)["added"] == 0
