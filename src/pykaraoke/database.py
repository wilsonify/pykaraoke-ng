"""Pure-Python karaoke song library (Pyodide-compatible).

Replaces the legacy pygame-coupled ``SongDB`` with a small in-memory
library fed from the web UI (file entries produced by a folder picker).
Everything is JSON-serializable so the UI can persist the library and
settings in localStorage.
"""

from __future__ import annotations

import fnmatch
import io
import json
import os
import re
import zipfile
from dataclasses import dataclass, field

from pykaraoke.filename_parser import FilenameParser, FileNameType

# ---------------------------------------------------------------------------
# Extensions and format kinds
# ---------------------------------------------------------------------------

AUDIO_EXTENSIONS = (".mp3", ".ogg", ".wav")
ZIP_EXTENSIONS = (".zip",)

_KIND_BY_EXT = {
    ".cdg": "cdg",
    ".kar": "kar",
    ".mid": "kar",
    ".mpg": "mpg",
    ".mpeg": "mpg",
    ".avi": "mpg",
    ".divx": "mpg",
    ".xvid": "mpg",
    ".lrc": "lrc",
    ".lcr": "lrc",
}


def kind_for_name(name: str) -> str | None:
    """Return the song kind ('cdg' | 'kar' | 'mpg') for *name*, or None."""
    return _KIND_BY_EXT.get(os.path.splitext(name)[1].lower())


# Scan-report categories. "unsupported" and "filtered" are ordinary outcomes;
# the rest explain why an input produced no songs.
REPORT_CATEGORIES = (
    "unsupported",
    "filtered",
    "corrupt_archive",
    "unsupported_compression",
    "unreadable",
    "parse_failure",
    "duplicate_lyric",
    "missing_audio",
)


def _pattern_match(pattern: str, name: str) -> bool:
    """Match *name* (already lowercased) against one case-insensitive glob.

    An untranslatable pattern degrades to a literal substring match rather
    than raising, so a stray character in a user pattern cannot break a scan.
    """
    pattern = pattern.strip().lower()
    if not pattern:
        return False
    try:
        return fnmatch.fnmatchcase(name, pattern)
    except re.error:
        return pattern in name


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


@dataclass
class Song:
    """A single karaoke song entry (a .cdg/.kar/.mpg file or zip member)."""

    id: str  # unique key: path + zip member
    title: str
    artist: str
    filename: str  # display name (basename, or zip member name)
    kind: str  # 'cdg' | 'kar' | 'mpg'
    path: str  # folder-relative path as reported by the web file picker
    disc: str = ""
    track: str = ""
    zip_name: str | None = None  # zip file name when the song is inside one
    audio_name: str | None = None  # companion mp3/ogg for .cdg songs
    # Full path of the paired audio file.  It is what playback loads: a base
    # name alone cannot tell two folders' "A - Song.mp3" apart.
    audio_path: str | None = None
    size: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "disc": self.disc,
            "track": self.track,
            "filename": self.filename,
            "kind": self.kind,
            "path": self.path,
            "zip_name": self.zip_name,
            "audio_name": self.audio_name,
            "audio_path": self.audio_path,
            "size": self.size,
        }

    @staticmethod
    def from_dict(data: dict) -> Song:
        return Song(
            id=data["id"],
            title=data.get("title", ""),
            artist=data.get("artist", ""),
            disc=data.get("disc", ""),
            track=data.get("track", ""),
            filename=data.get("filename", ""),
            kind=data.get("kind", "cdg"),
            path=data.get("path", ""),
            zip_name=data.get("zip_name"),
            audio_name=data.get("audio_name"),
            # Optional: a library exported before audio_path existed still
            # loads, and the next scan re-pairs it from the folder index.
            audio_path=data.get("audio_path"),
            size=data.get("size", 0),
        )


@dataclass
class Settings:
    """User settings persisted by the UI."""

    folders: list = field(default_factory=list)
    cdg_zoom: str = "int"  # 'quick' | 'int' | 'full' | 'soft' | 'none'
    derive_song_info: bool = True
    file_name_type: int = int(FileNameType.ARTIST_TITLE)
    exclude_non_matching: bool = False
    look_inside_zips: bool = True
    sort: str = "filename"  # 'filename' | 'title' | 'artist'
    volume: float = 0.75
    include_patterns: list = field(default_factory=list)
    exclude_patterns: list = field(default_factory=list)
    lyric_size: str = "medium"  # 'small' | 'medium' | 'large'

    def to_dict(self) -> dict:
        return {
            "folders": list(self.folders),
            "cdg_zoom": self.cdg_zoom,
            "derive_song_info": self.derive_song_info,
            "file_name_type": self.file_name_type,
            "exclude_non_matching": self.exclude_non_matching,
            "look_inside_zips": self.look_inside_zips,
            "sort": self.sort,
            "volume": self.volume,
            "include_patterns": [str(p) for p in self.include_patterns],
            "exclude_patterns": [str(p) for p in self.exclude_patterns],
            "lyric_size": self.lyric_size,
        }

    @staticmethod
    def from_dict(data: dict) -> Settings:
        s = Settings()
        s.folders = list(data.get("folders", []))
        s.cdg_zoom = data.get("cdg_zoom", s.cdg_zoom)
        s.derive_song_info = bool(data.get("derive_song_info", s.derive_song_info))
        s.file_name_type = int(data.get("file_name_type", s.file_name_type))
        s.exclude_non_matching = bool(data.get("exclude_non_matching", s.exclude_non_matching))
        s.look_inside_zips = bool(data.get("look_inside_zips", s.look_inside_zips))
        s.sort = data.get("sort", s.sort)
        s.volume = float(data.get("volume", s.volume))
        s.include_patterns = [str(p) for p in data.get("include_patterns", [])]
        s.exclude_patterns = [str(p) for p in data.get("exclude_patterns", [])]
        s.lyric_size = str(data.get("lyric_size", s.lyric_size))
        return s


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------


def _strip_articles(text: str) -> str:
    """Lowercase *text* and remove a leading article for sorting."""
    text = text.strip().lower()
    if text and text[0] == "(":
        rparen = text.find(")")
        if rparen != -1:
            text = text[rparen + 1 :].strip()
    if text:
        first_word = text.split()[0]
        if first_word in ("a", "an", "the"):
            text = text[len(first_word) :].strip()
    return text


class SongLibrary:
    """In-memory song collection with search, sort, and JSON persistence.

    Files are supplied by the UI as plain dicts::

        {"name": "Artist - Title.cdg", "path": "Folder/Artist - Title.cdg", "size": 1234}

    ``path`` is the folder-relative path from the web folder picker
    (e.g. ``webkitdirectory``'s ``webkitRelativePath``); ``name`` is the
    basename.  For songs inside a zip, use :meth:`scan_zip` with the zip's
    bytes so members can be listed without a filesystem.
    """

    def __init__(self):
        self.songs: list[Song] = []
        self.settings: Settings = Settings()
        self._files: dict[str, dict] = {}  # path(lower) -> file entry
        # Parsed member sets per zip (lowercased archive name), so a rebuild
        # can restore zip songs without the archive bytes.
        self._zip_cache: dict[str, list[dict]] = {}
        # Scan diagnostics: ordered problem entries plus a set used to keep
        # each (category, path) pair reported once across repeated rebuilds.
        self._report_entries: list[dict] = []
        self._report_seen: set[tuple[str, str]] = set()

    # ------------------------------------------------------------------
    # Scan reporting and filename filters
    # ------------------------------------------------------------------

    def _report(self, category: str, path: str) -> None:
        """Record one scan outcome. Never raises for an unknown category."""
        key = (category, path)
        if key in self._report_seen:
            return
        self._report_seen.add(key)
        self._report_entries.append({"category": category, "path": path})

    def scan_report(self) -> dict:
        """Return the accumulated scan report as a JSON-compatible dict."""
        counts = dict.fromkeys(REPORT_CATEGORIES, 0)
        for entry in self._report_entries:
            counts[entry["category"]] = counts.get(entry["category"], 0) + 1
        return {"entries": list(self._report_entries), "counts": counts}

    def clear_scan_report(self) -> None:
        """Forget every recorded scan outcome."""
        self._report_entries = []
        self._report_seen = set()

    def _name_allowed(self, name: str) -> bool:
        """True when *name* passes the include/exclude pattern settings."""
        base = os.path.basename(name).lower()
        includes = [p for p in self.settings.include_patterns if str(p).strip()]
        excludes = [p for p in self.settings.exclude_patterns if str(p).strip()]
        if includes and not any(_pattern_match(str(p), base) for p in includes):
            return False
        return not any(_pattern_match(str(p), base) for p in excludes)

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan(self, files: list[dict], replace: bool = False) -> dict:
        """Add a batch of file entries from the folder picker.

        With ``replace=True`` the previously scanned loose files and zip
        expansions are cleared first (Settings are untouched), supporting
        library relocation; the default stays additive.

        Returns ``{"added": n, "total": m}``.
        """
        if replace:
            self._files.clear()
            self._zip_cache.clear()
            self.songs = []
        if not files:
            return {"added": 0, "total": len(self.songs)}
        before = {song.id for song in self.songs}
        for entry in files:
            name = entry.get("name", "")
            path = entry.get("path", name)
            if not name:
                continue
            ext = os.path.splitext(name)[1].lower()
            # Zip archives are expanded separately via scan_zip (they need
            # their bytes); do not count them as unsupported loose files.
            if kind_for_name(name) is None and ext not in ZIP_EXTENSIONS:
                self._report("unsupported", path or name)
            self._files[(path or name).lower()] = entry
        self._rebuild()
        # `added` is what this scan introduced; re-scanning an unchanged
        # library must say 0, not repeat the whole library size.
        added = sum(1 for song in self.songs if song.id not in before)
        return {"added": added, "total": len(self.songs)}

    def prune_songs(self, known_paths) -> int:
        """Remove loose and zip songs whose paths are absent from *known_paths*.

        An empty known-set is a no-op so an accidental empty call cannot wipe
        the library. Returns the number of songs removed.
        """
        known = {str(p).replace("\\", "/").lower() for p in known_paths}
        if not known:
            return 0
        self._files = {k: v for k, v in self._files.items() if k in known}
        kept_cache: dict[str, list[dict]] = {}
        for key, entries in self._zip_cache.items():
            kept = [
                d for d in entries if str(d.get("path", "")).replace("\\", "/").lower() in known
            ]
            if kept:
                kept_cache[key] = kept
        self._zip_cache = kept_cache
        before = len(self.songs)
        self.songs = [s for s in self.songs if s.path.replace("\\", "/").lower() in known]
        # A pruned library must not keep pointing at a companion that is gone.
        self.pair_cdg_audio()
        return before - len(self.songs)

    def _open_archive(self, name: str, data: bytes):
        """Open zip *data*, reporting corrupt/unreadable archives (None then).

        The categories are kept apart on purpose: "not a zip" and "a zip the
        runtime cannot decompress" need different fixes from the operator.
        """
        try:
            return zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            self._report("corrupt_archive", name)
            return None
        except NotImplementedError:
            self._report("unsupported_compression", name)
            return None
        except (OSError, RuntimeError, ValueError):
            self._report("unreadable", name)
            return None

    def _select_zip_members(self, zf: zipfile.ZipFile, name: str) -> list:
        """Karaoke members of *zf*, reporting pattern-filtered ones."""
        members = []
        for member in zf.namelist():
            if not kind_for_name(member):
                continue
            if not self._name_allowed(member):
                self._report("filtered", name + "!" + member)
                continue
            members.append(member)
        return members

    def _member_readable(self, zf: zipfile.ZipFile, member: str, name: str) -> bool:
        """Whether one member can be read, reporting only that member on failure.

        A per-member probe means one corrupt entry costs its own song instead
        of the whole archive's songs.  An unsupported compression method is
        still reported against the archive, because every member using it will
        fail the same way.
        """
        try:
            with zf.open(member) as fh:
                fh.read(1)
            return True
        except NotImplementedError:
            self._report("unsupported_compression", name)
            return False
        except Exception:
            self._report("unreadable", name + "!" + member)
            return False

    def _store_zip_songs(self, name: str, members: list) -> int:
        """Build songs for *members*, skipping duplicates; returns added count."""
        base = os.path.splitext(name)[0]
        existing = {s.id for s in self.songs if s.zip_name == name}
        added = 0
        for member in members:
            song = self._make_song(
                path=base + "/" + member,
                name=os.path.basename(member),
                size=0,
                zip_name=name,
                zip_member=member,
            )
            if song and song.id not in existing:
                self.songs.append(song)
                added += 1
        return added

    def scan_zip(self, name: str, data: bytes) -> dict:
        """Scan a zip archive's bytes and add its karaoke members as songs."""
        if not self.settings.look_inside_zips:
            return {"added": 0, "total": len(self.songs)}
        zf = self._open_archive(name, data)
        if zf is None:
            return {"added": 0, "total": len(self.songs)}
        members: list = []
        try:
            members = [
                member
                for member in self._select_zip_members(zf, name)
                if self._member_readable(zf, member, name)
            ]
        finally:
            zf.close()
        if not members:
            return {"added": 0, "total": len(self.songs)}

        added = self._store_zip_songs(name, members)
        # Cache the full member set so later rebuilds (which no longer have
        # the archive bytes) can restore this zip's songs.
        self._zip_cache[name.lower()] = [s.to_dict() for s in self.songs if s.zip_name == name]
        self._dedupe_and_sort()
        return {"added": added, "total": len(self.songs)}

    def _song_key(self, path: str) -> tuple[str, str]:
        """Folder and stem of *path*, both lowercased, to identify a performance."""
        folder = os.path.dirname(path.replace("\\", "/")).lower()
        stem = os.path.splitext(os.path.basename(path))[0]
        return folder, stem.lower()

    def _audio_index(self) -> dict:
        """Companion-audio lookups, built once per rebuild.

        Four tables let pairing ask the narrowest question first: same folder
        with an exact stem, same folder normalised, any folder exact, then any
        folder normalised.  Entries are visited in path order and the first
        wins, so the same inputs always pair the same way.
        """
        exact: dict = {}
        norm: dict = {}
        global_exact: dict = {}
        global_norm: dict = {}
        ordered = sorted(
            self._files.values(), key=lambda e: str(e.get("path", e.get("name", "")))
        )
        for entry in ordered:
            name = str(entry.get("name", ""))
            if os.path.splitext(name)[1].lower() not in AUDIO_EXTENSIONS:
                continue
            path = str(entry.get("path", name))
            folder, stem = self._song_key(path)
            normalised = _normalize_stem(stem)
            exact.setdefault((folder, stem), path)
            norm.setdefault((folder, normalised), path)
            global_exact.setdefault(stem, path)
            global_norm.setdefault(normalised, path)
        return {
            "exact": exact,
            "norm": norm,
            "global_exact": global_exact,
            "global_norm": global_norm,
        }

    def _resolve_audio(self, path: str, index: dict) -> str | None:
        """Companion audio path for the song at *path*, or None."""
        folder, stem = self._song_key(path)
        normalised = _normalize_stem(stem)
        for table, key in (
            ("exact", (folder, stem)),
            ("norm", (folder, normalised)),
            ("global_exact", stem),
            ("global_norm", normalised),
        ):
            hit = index[table].get(key)
            if isinstance(hit, str) and hit:
                return hit
        return None

    def _rebuild(self) -> None:
        """Rebuild the song list from the raw file entries and zip cache."""
        songs = self._build_songs()
        for cached in self._zip_cache.values():
            for song_dict in cached:
                songs.append(Song.from_dict(song_dict))
        self.songs = songs
        self._dedupe_and_sort()

    def _build_songs(self) -> list[Song]:
        """Songs for the loose files, with companions classified per stem.

        Files that share a folder and a stem are one performance: a CD+G wins
        over a lyric file, a lyric file needs its audio, and anything left over
        is reported instead of being dropped without a trace.
        """
        index = self._audio_index()
        groups: dict = {}
        order: list = []
        for entry in self._files.values():
            name = str(entry.get("name", ""))
            if os.path.splitext(name)[1].lower() in ZIP_EXTENSIONS:
                # Zips are expanded separately via scan_zip (they need their
                # bytes read); skip them here.
                continue
            if kind_for_name(name) is None:
                continue
            key = self._song_key(str(entry.get("path", name)))
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(entry)
        songs: list[Song] = []
        for key in order:
            songs.extend(self._songs_for_group(groups[key], index))
        return songs

    def _songs_for_group(self, entries: list, index: dict) -> list[Song]:
        """The songs one folder+stem group contributes."""
        cdg = [e for e in entries if kind_for_name(str(e.get("name", ""))) == "cdg"]
        lyrics = [e for e in entries if kind_for_name(str(e.get("name", ""))) == "lrc"]
        others = [
            e for e in entries if kind_for_name(str(e.get("name", ""))) not in ("cdg", "lrc")
        ]
        songs = [song for entry in others if (song := self._song_from_entry(entry, index))]
        lyric_paths = [str(e.get("path", e.get("name", ""))) for e in lyrics]
        if cdg:
            song = self._song_from_entry(cdg[0], index)
            if song:
                songs.append(song)
            for path in lyric_paths:
                # The CD+G is the performance; the lyrics are its companion.
                self._report("duplicate_lyric", path)
            return songs
        if not lyrics:
            return songs
        # One lyric per performance: `.lrc` before `.lcr`, then path order.
        lyrics.sort(key=lambda e: (0 if str(e.get("name", "")).lower().endswith(".lrc") else 1, str(e.get("path", ""))))
        for entry in lyrics[1:]:
            self._report("duplicate_lyric", str(entry.get("path", entry.get("name", ""))))
        song = self._song_from_entry(lyrics[0], index)
        if song is None:
            return songs
        if not song.audio_path:
            # A lyric file cannot play on its own; listing it would only give
            # the operator a row that fails on click.
            self._report("missing_audio", song.path)
            return songs
        songs.append(song)
        return songs

    def _song_from_entry(self, entry: dict, index: dict) -> Song | None:
        """Build one Song from a file entry, pairing its companion audio."""
        name = str(entry.get("name", ""))
        path = str(entry.get("path", name))
        kind = kind_for_name(name)
        audio_path = self._resolve_audio(path, index) if kind in ("cdg", "lrc") else None
        return self._make_song(
            path=path,
            name=name,
            size=int(entry.get("size", 0) or 0),
            zip_name=None,
            zip_member=None,
            audio_path=audio_path,
        )

    def _make_song(
        self,
        path: str,
        name: str,
        size: int,
        zip_name: str | None,
        zip_member: str | None,
        audio_path: str | None = None,
    ) -> Song | None:
        """Build a Song from a file entry, or None if it should be excluded."""
        if not self._name_allowed(name):
            self._report("filtered", path)
            return None
        parsed = self._parse_name(name if zip_member is None else zip_member, zip_member)
        title = parsed.title or os.path.splitext(name)[0]
        artist = parsed.artist
        if not artist and self.settings.exclude_non_matching:
            self._report("filtered", path)
            return None
        return Song(
            id=path if zip_member is None else f"{zip_name}!{zip_member}",
            title=title,
            artist=artist,
            disc=parsed.disc,
            track=parsed.track,
            filename=os.path.basename(name),
            kind=kind_for_name(name) or "cdg",
            path=path,
            zip_name=zip_name,
            audio_name=os.path.basename(audio_path) if audio_path else None,
            audio_path=audio_path,
            size=size,
        )

    def _parse_name(self, name: str, zip_member: str | None):
        parser = FilenameParser(file_name_type=FileNameType(self.settings.file_name_type))
        try:
            if zip_member:
                return parser.parse_zip_path(zip_member)
            return parser.parse(name)
        except Exception:  # defensive: never let one bad name kill a scan
            self._report("parse_failure", zip_member or name)
            return _EmptyParsed()

    def pair_cdg_audio(self) -> None:
        """(Re)attach companion audio to every loose .cdg/.lrc/.lcr song.

        Resolution prefers the song's own folder (see :meth:`_resolve_audio`),
        so two packs that share a base name keep their own audio; a normalised
        match still ignores track-number prefixes and trailing
        "karaoke"/"instrumental" suffixes.
        """
        index = self._audio_index()
        for song in self.songs:
            if song.zip_name is not None or song.kind not in ("cdg", "lrc"):
                continue
            audio_path = self._resolve_audio(song.path, index)
            song.audio_path = audio_path
            song.audio_name = os.path.basename(audio_path) if audio_path else None

    def _dedupe_and_sort(self) -> None:
        seen: set[str] = set()
        unique = []
        for song in self.songs:
            if song.id in seen:
                continue
            seen.add(song.id)
            unique.append(song)
        self.songs = unique
        self.pair_cdg_audio()
        self.sort_by(self.settings.sort)

    # ------------------------------------------------------------------
    # Search / sort / access
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 500) -> list[Song]:
        """Return songs whose title/artist/filename match all query terms."""
        terms = [t for t in query.lower().split() if t]
        if not terms:
            return []
        results = []
        for song in self.songs:
            haystack = " ".join([song.title.lower(), song.artist.lower(), song.filename.lower()])
            if all(term in haystack for term in terms):
                results.append(song)
                if len(results) >= limit:
                    break
        return results

    def sort_by(self, sort: str) -> None:
        self.settings.sort = sort if sort in ("filename", "title", "artist") else "filename"
        key = self.settings.sort
        if key == "title":
            self.songs.sort(
                key=lambda s: (
                    _strip_articles(s.title),
                    _strip_articles(s.artist),
                    s.filename.lower(),
                )
            )
        elif key == "artist":
            self.songs.sort(
                key=lambda s: (
                    _strip_articles(s.artist),
                    _strip_articles(s.title),
                    s.filename.lower(),
                )
            )
        else:
            self.songs.sort(key=lambda s: (s.filename.lower(), _strip_articles(s.artist)))

    def get_song(self, song_id: str) -> Song | None:
        for song in self.songs:
            if song.id == song_id:
                return song
        return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "version": 2,
            "songs": [s.to_dict() for s in self.songs],
            "settings": self.settings.to_dict(),
        }

    EXPORT_FORMAT = "pykaraoke-ng-library"
    EXPORT_SCHEMA = 1

    def export_json(self) -> str:
        """Export the library as a self-describing JSON envelope string."""
        return json.dumps(
            {
                "format": self.EXPORT_FORMAT,
                "schema": self.EXPORT_SCHEMA,
                "library": self.to_dict(),
            }
        )

    def import_json(self, payload: str) -> dict:
        """Replace the library from *payload* (envelope or bare library dict).

        Returns ``{"ok": True}`` on success. On any failure the previous
        library is left untouched and ``{"ok": False, "error": …}`` is
        returned — never a partial state.
        """
        try:
            data = json.loads(payload)
        except (TypeError, ValueError):
            return {"ok": False, "error": "payload is not valid JSON"}
        if not isinstance(data, dict):
            return {"ok": False, "error": "payload is not a JSON object"}
        if "library" in data or "format" in data or "schema" in data:
            if data.get("schema") != self.EXPORT_SCHEMA:
                return {
                    "ok": False,
                    "error": f"unrecognised schema: {data.get('schema')!r}",
                }
            lib_data = data.get("library")
        else:
            lib_data = data
        if not isinstance(lib_data, dict):
            return {"ok": False, "error": "library payload is not an object"}
        if lib_data.get("version") != 2:
            return {
                "ok": False,
                "error": f"unrecognised library version: {lib_data.get('version')!r}",
            }
        try:
            new_lib = SongLibrary.from_dict(lib_data)
        except Exception as exc:  # report, never raise
            return {"ok": False, "error": f"invalid library: {exc}"}
        # Atomic swap: build fully, then copy state over in one step.
        self.songs = new_lib.songs
        self.settings = new_lib.settings
        self._files = new_lib._files
        self._zip_cache = new_lib._zip_cache
        return {"ok": True}

    @staticmethod
    def from_dict(data: dict) -> SongLibrary:
        lib = SongLibrary()
        if data.get("version") == 2:
            lib.settings = Settings.from_dict(data.get("settings", {}))
            lib.songs = [Song.from_dict(d) for d in data.get("songs", [])]
            for song in lib.songs:
                if song.zip_name:
                    # Rebuild the zip-member cache so a later scan of loose
                    # files does not drop the restored zip songs.
                    lib._zip_cache.setdefault(song.zip_name.lower(), []).append(song.to_dict())
                elif song.path:
                    lib._files.setdefault(
                        song.path.lower(),
                        {
                            "name": os.path.basename(song.path),
                            "path": song.path,
                            "size": song.size,
                        },
                    )
        return lib


_WS_CHARS = " \t\n\r\f\v"


def _is_ws(ch: str) -> bool:
    """Whether *ch* matches ``\\s`` (ASCII whitespace or non-ASCII space)."""
    return ch in _WS_CHARS or (ord(ch) > 127 and ch.isspace())


def _strip_track_prefix(s: str) -> str:
    """Drop a leading ``NN - `` / ``NN. `` / ``NN) `` track marker, if any."""
    i = 0
    while i < len(s) and s[i].isdigit():
        i += 1
    if not i:
        return s
    j = i
    while j < len(s) and _is_ws(s[j]):
        j += 1
    if j >= len(s) or s[j] not in "-.)":
        return s
    k = j + 1
    while k < len(s) and _is_ws(s[k]):
        k += 1
    return s[k:]


def _strip_karaoke_suffix(s: str) -> str:
    """Drop one trailing ``karaoke``/``instrumental`` suffix with separators."""
    for suffix in ("karaoke", "instrumental"):
        if s.endswith(suffix):
            head = s[: -len(suffix)]
            while head and (head[-1] == "-" or _is_ws(head[-1])):
                head = head[:-1]
            return head
    return s


def _normalize_stem(stem: str) -> str:
    """Lowercase *stem*, dropping track numbers, suffixes and punctuation.

    Plain string operations replace three ``re.sub`` calls: the
    ``[-\\s]*(karaoke|instrumental)$`` pattern backtracks on trailing
    separator runs, and ``[^a-z0-9]+`` rescans on every punctuation run.
    """
    s = _strip_karaoke_suffix(_strip_track_prefix(stem.lower()))
    return "".join(ch for ch in s if "a" <= ch <= "z" or "0" <= ch <= "9")


class _EmptyParsed:
    """Fallback parse result when no naming scheme matched."""

    artist = ""
    title = ""
    disc = ""
    track = ""
