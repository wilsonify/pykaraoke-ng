"""Bridge between the web UI and the karaoke engine.

This is the single entry point PyScript exposes to the frontend.  It is
kept deliberately small and JSON-friendly: every method either returns
plain dicts/lists/bytes or mutates in-memory state.
"""

from __future__ import annotations

from pykaraoke import cdg as cdg_module
from pykaraoke import database, lrc, midi


class KaraokeApp:
    """One instance per page; published to JS as ``window.pykaraoke``."""

    def __init__(self):
        self.library = database.SongLibrary()
        # Live CDG decoders keyed by song id (incremental decode state).
        self._decoders: dict[str, cdg_module.CdgDecoder] = {}
        # Zip bytes keyed by zip file name (for reading members later).
        self._zips: dict[str, bytes] = {}
        # Cached member names per zip (looked up for companion files).
        self._zip_names: dict[str, list] = {}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        """Serialize library + settings to a JSON string for localStorage."""
        import json

        return json.dumps(self.library.to_dict())

    def from_json(self, payload: str) -> None:
        """Restore library + settings from a JSON string."""
        import json

        try:
            data = json.loads(payload)
        except (TypeError, ValueError):
            return
        if isinstance(data, dict):
            self.library = database.SongLibrary.from_dict(data)
            self._decoders.clear()
            self._zip_names.clear()

    # ------------------------------------------------------------------
    # Library
    # ------------------------------------------------------------------

    def scan_files(self, files) -> dict:
        """Scan file entries ``[{name, path, size}]`` from the folder picker."""
        entries = []
        for f in files:
            if not isinstance(f, dict):
                continue
            try:
                entries.append(
                    {
                        "name": str(f.get("name", "")),
                        "path": str(f.get("path", f.get("name", ""))),
                        "size": int(f.get("size", 0) or 0),
                    }
                )
            except (TypeError, ValueError):
                continue
        return self.library.scan(entries)

    def scan_zip(self, name: str, data) -> dict:
        """Scan a zip archive (bytes) and add its karaoke members."""
        try:
            raw = bytes(data)
        except (TypeError, ValueError):
            return {"added": 0, "total": len(self.library.songs)}
        self._zips[str(name)] = raw
        self._zip_names.pop(str(name), None)
        return self.library.scan_zip(str(name), raw)

    def read_zip_member(self, zip_name: str, member: str):
        """Return the bytes of *member* inside the zip file *zip_name*.

        Returns None when the zip was never scanned or the member is
        missing.  Used to load a song's CDG/KAR bytes without a filesystem.
        """
        raw = self._zips.get(str(zip_name))
        if raw is None:
            return None
        try:
            import io
            import zipfile

            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                return zf.read(str(member))
        except (zipfile.BadZipFile, KeyError):
            return None

    def zip_members(self, zip_name: str) -> list:
        """Names of the files inside the loaded zip *zip_name*.

        Empty when the zip is not in memory.  Lets the UI check for a
        companion file (e.g. ``.elrc``) without reading it back.
        """
        name = str(zip_name)
        if name not in self._zips:
            return []
        if name not in self._zip_names:
            import io
            import zipfile

            try:
                with zipfile.ZipFile(io.BytesIO(self._zips[name])) as zf:
                    self._zip_names[name] = zf.namelist()
            except zipfile.BadZipFile:
                self._zip_names[name] = []
        return self._zip_names[name]

    def search(self, query: str, limit: int = 500) -> dict:
        results = self.library.search(str(query), limit=int(limit))
        return {"results": [s.to_dict() for s in results]}

    def library_songs(self) -> dict:
        return {"songs": [s.to_dict() for s in self.library.songs]}

    def song(self, song_id: str) -> dict | None:
        song = self.library.get_song(str(song_id))
        return song.to_dict() if song else None

    def get_settings(self) -> dict:
        return self.library.settings.to_dict()

    def set_settings(self, updates: dict) -> dict:
        settings = self.library.settings
        if "cdg_zoom" in updates:
            settings.cdg_zoom = str(updates["cdg_zoom"])
        if "sort" in updates:
            self.library.sort_by(str(updates["sort"]))
        if "volume" in updates:
            settings.volume = float(updates["volume"])
        if "file_name_type" in updates:
            settings.file_name_type = int(updates["file_name_type"])
        if "derive_song_info" in updates:
            settings.derive_song_info = bool(updates["derive_song_info"])
        if "exclude_non_matching" in updates:
            settings.exclude_non_matching = bool(updates["exclude_non_matching"])
        if "look_inside_zips" in updates:
            settings.look_inside_zips = bool(updates["look_inside_zips"])
        if "folders" in updates:
            settings.folders = [str(f) for f in updates["folders"]]
        if "include_patterns" in updates:
            settings.include_patterns = [str(p) for p in updates["include_patterns"]]
        if "exclude_patterns" in updates:
            settings.exclude_patterns = [str(p) for p in updates["exclude_patterns"]]
        return settings.to_dict()

    def scan_report(self) -> dict:
        """Structured scan outcomes (entries plus per-category counts)."""
        return self.library.scan_report()

    def clear_scan_report(self) -> dict:
        """Forget recorded scan outcomes; returns the now-empty report."""
        self.library.clear_scan_report()
        return self.library.scan_report()

    # ------------------------------------------------------------------
    # Playback data
    # ------------------------------------------------------------------

    def parse_midi(self, data) -> dict:
        """Parse a .kar/.mid file (bytes) into lyrics + notes for the synth."""
        try:
            raw = bytes(data)
        except (TypeError, ValueError):
            return {"error": "invalid data"}
        mf = midi.parse_midi(raw)
        if mf is None:
            return {"error": "could not parse MIDI file"}
        return mf.to_dict()

    def parse_lrc(self, text, elrc_text=None) -> dict:
        """Parse LRC lyrics text into timed lyric events for the UI.

        ``elrc_text`` is the optional companion ``.elrc`` file, which adds
        word-level timing on top of the line timestamps.  A missing or
        unusable ``.elrc`` is not an error: the plain LRC timing is used.

        The payload also carries duet information when present: a
        ``parts`` key with the ``[pa:]``/``[pb:]`` singer names, and a
        per-line ``part`` key (``a``/``b``/``ab``) on tagged lyric events.
        Both are preserved across an ``.elrc`` merge.
        """
        if not isinstance(text, str):
            return {"error": "invalid text"}
        parsed = lrc.parse_lrc(text)
        if parsed is None:
            return {"error": "no timed lyrics found"}
        if isinstance(elrc_text, str) and elrc_text.strip():
            merged = lrc.parse_elrc(
                elrc_text,
                parsed["lyrics"],
                offset_ms=lrc.parse_offset(parsed["meta"]),
            )
            if merged:
                parsed = {**parsed, "lyrics": merged, "elrc": True}
        return parsed

    def cdg_open(self, song_id: str, data) -> str:
        """Create a decoder for a .cdg file; returns the decoder key."""
        key = str(song_id)
        try:
            raw = bytes(data)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid cdg data") from exc
        self._decoders[key] = cdg_module.CdgDecoder(raw)
        return key

    def cdg_update(self, decoder_key: str, ms: int) -> dict | None:
        """Advance the decoder to *ms* and return changed tiles (or None).

        Returns ``{"border": [r,g,b]|None, "tiles": [{"x","y","data"}]}``.
        """
        decoder = self._decoders.get(str(decoder_key))
        if decoder is None:
            return None
        decoder.process_until(cdg_module.packet_index_at(int(ms)))
        return decoder.update()

    def cdg_seek(self, decoder_key: str, ms: int) -> None:
        decoder = self._decoders.get(str(decoder_key))
        if decoder is not None:
            decoder.seek(int(ms))

    def cdg_close(self, decoder_key: str) -> None:
        self._decoders.pop(str(decoder_key), None)

    def cdg_packet_count(self, data) -> int:
        """Total packet count of a .cdg file (used for duration)."""
        return len(bytes(data)) // 24
