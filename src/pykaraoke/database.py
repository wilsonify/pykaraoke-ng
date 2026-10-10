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
        return {"added": len(self.songs), "total": len(self.songs)}

    def prune_songs(self, known_paths) -> int:
        """Remove loose and zip songs whose paths are absent from *known_paths*.

        An empty known-set is a no-op so an accidental empty call cannot wipe
        the library. Returns the number of songs removed.
        """
        known = {str(p).replace("\\", "/").lower() for p in known_paths}
        if not known:
            return 0
        self._files = {k: v for k, v in self._files.items() if k in known}
        for key in list(self._zip_cache):
            kept = [
                d
                for d in self._zip_cache[key]
                if str(d.get("path", "")).replace("\\", "/").lower() in known
            ]
            if kept:
                self._zip_cache[key] = kept
            else:
                del self._zip_cache[key]
        before = len(self.songs)
        self.songs = [s for s in self.songs if s.path.replace("\\", "/").lower() in known]
        return before - len(self.songs)

    def _open_archive(self, name: str, data: bytes):
        """Open zip *data*, reporting corrupt/unreadable archives (None then)."""
        try:
            return zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            self._report("corrupt_archive", name)
            return None
        except Exception:
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

    def _probe_zip_readable(self, zf: zipfile.ZipFile, member: str, name: str) -> bool:
        """Probe the first member so bad compression/encryption is classified now."""
        try:
            with zf.open(member) as fh:
                fh.read(1)
            return True
        except NotImplementedError:
            self._report("unsupported_compression", name)
            return False
        except Exception:
            self._report("unreadable", name)
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
        try:
            members = self._select_zip_members(zf, name)
            if members and not self._probe_zip_readable(zf, members[0], name):
                return {"added": 0, "total": len(self.songs)}
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

    def _rebuild(self) -> None:
        """Rebuild the song list from the raw file entries and zip cache."""
        songs = []
        for entry in self._files.values():
            name = entry.get("name", "")
            ext = os.path.splitext(name)[1].lower()
            if ext in ZIP_EXTENSIONS:
                # Zips are expanded separately via scan_zip (they need
                # their bytes read); skip them here.
                continue
            kind = kind_for_name(name)
            if kind is None:
                continue
            song = self._make_song(
                path=entry.get("path", name),
                name=name,
                size=int(entry.get("size", 0) or 0),
                zip_name=None,
                zip_member=None,
            )
            if song:
                songs.append(song)
        for cached in self._zip_cache.values():
            for song_dict in cached:
                songs.append(Song.from_dict(song_dict))
        self.songs = songs
        self._dedupe_and_sort()

    def _make_song(self, path, name, size, zip_name, zip_member):
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
            id=path if zip_member is None else zip_name + "!" + zip_member,
            title=title,
            artist=artist,
            disc=parsed.disc,
            track=parsed.track,
            filename=os.path.basename(name),
            kind=kind_for_name(name) or "cdg",
            path=path,
            zip_name=zip_name,
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

    @staticmethod
    def _needs_audio(song) -> bool:
        """Whether *song* still needs a companion audio file attached."""
        return song.kind in ("cdg", "lrc") and song.zip_name is None and not song.audio_name

    def _find_companion_audio(self, song_stem: str, song_norm: str):
        """Best audio entry for a stem: exact match wins, else normalized."""
        best = None
        for entry in self._files.values():
            name = entry.get("name", "")
            if os.path.splitext(name)[1].lower() not in AUDIO_EXTENSIONS:
                continue
            audio_stem = os.path.splitext(os.path.basename(name))[0]
            if audio_stem.lower() == song_stem.lower():
                return name
            if _normalize_stem(audio_stem) == song_norm:
                best = name
        return best

    def pair_cdg_audio(self) -> None:
        """Attach companion audio files to .cdg and .lrc/.lcr songs.

        Exact basename match first; then a normalized match that ignores
        track-number prefixes and "karaoke"/"instrumental" suffixes
        (e.g. ``01 - Inside Out.lrc`` pairs with ``Inside Out.mp3``).
        """
        for song in self.songs:
            if not self._needs_audio(song):
                continue
            song_stem = os.path.splitext(os.path.basename(song.path))[0]
            best = self._find_companion_audio(song_stem, _normalize_stem(song_stem))
            if best:
                song.audio_name = best

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
        except Exception as exc:  # noqa: BLE001 - report, never raise
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


def _normalize_stem(stem: str) -> str:
    """Lowercase *stem*, dropping track numbers, suffixes and punctuation."""
    s = stem.lower()
    s = re.sub(r"^\d+\s*[-.)]\s*", "", s)
    s = re.sub(r"[-\s]*(karaoke|instrumental)$", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


class _EmptyParsed:
    """Fallback parse result when no naming scheme matched."""

    artist = ""
    title = ""
    disc = ""
    track = ""
