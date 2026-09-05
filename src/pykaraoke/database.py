"""Pure-Python karaoke song library (Pyodide-compatible).

Replaces the legacy pygame-coupled ``SongDB`` with a small in-memory
library fed from the web UI (file entries produced by a folder picker).
Everything is JSON-serializable so the UI can persist the library and
settings in localStorage.
"""

from __future__ import annotations

import io
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
        }

    @staticmethod
    def from_dict(data: dict) -> Settings:
        s = Settings()
        s.folders = list(data.get("folders", []))
        s.cdg_zoom = data.get("cdg_zoom", s.cdg_zoom)
        s.derive_song_info = bool(data.get("derive_song_info", s.derive_song_info))
        s.file_name_type = int(data.get("file_name_type", s.file_name_type))
        s.exclude_non_matching = bool(
            data.get("exclude_non_matching", s.exclude_non_matching)
        )
        s.look_inside_zips = bool(data.get("look_inside_zips", s.look_inside_zips))
        s.sort = data.get("sort", s.sort)
        s.volume = float(data.get("volume", s.volume))
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
        self.settings = Settings()
        self._files: dict[str, dict] = {}  # path(lower) -> file entry

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan(self, files: list[dict]) -> dict:
        """Add a batch of file entries from the folder picker.

        Returns ``{"added": n, "total": m}``.
        """
        if not files:
            return {"added": 0, "total": len(self.songs)}
        for entry in files:
            name = entry.get("name", "")
            path = entry.get("path", name)
            if name:
                self._files[(path or name).lower()] = entry
        self._rebuild()
        return {"added": len(self.songs), "total": len(self.songs)}

    def scan_zip(self, name: str, data: bytes) -> dict:
        """Scan a zip archive's bytes and add its karaoke members as songs."""
        if not self.settings.look_inside_zips:
            return {"added": 0, "total": len(self.songs)}
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            return {"added": 0, "total": len(self.songs)}
        members = [m for m in zf.namelist() if kind_for_name(m)]
        zf.close()
        if not members:
            return {"added": 0, "total": len(self.songs)}

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
        self._dedupe_and_sort()
        return {"added": added, "total": len(self.songs)}

    def _rebuild(self) -> None:
        """Rebuild the song list from the raw file entries."""
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
        self.songs = songs
        self._dedupe_and_sort()

    def _make_song(self, path, name, size, zip_name, zip_member):
        """Build a Song from a file entry, or None if it should be excluded."""
        parsed = self._parse_name(name if zip_member is None else zip_member, zip_member)
        title = parsed.title or os.path.splitext(name)[0]
        artist = parsed.artist
        if not artist and self.settings.exclude_non_matching:
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
        if zip_member:
            return parser.parse_zip_path(zip_member)
        try:
            return parser.parse(name)
        except Exception:  # defensive: never let one bad name kill a scan
            return _EmptyParsed()

    def pair_cdg_audio(self) -> None:
        """Attach companion audio files to .cdg and .lrc/.lcr songs.

        Exact basename match first; then a normalized match that ignores
        track-number prefixes and "karaoke"/"instrumental" suffixes
        (e.g. ``01 - Inside Out.lrc`` pairs with ``Inside Out.mp3``).
        """
        for song in self.songs:
            if song.kind not in ("cdg", "lrc") or song.zip_name is not None or song.audio_name:
                continue
            song_stem = os.path.splitext(os.path.basename(song.path))[0]
            song_norm = _normalize_stem(song_stem)
            best = None
            best_is_exact = False
            for entry in self._files.values():
                name = entry.get("name", "")
                if os.path.splitext(name)[1].lower() not in AUDIO_EXTENSIONS:
                    continue
                audio_stem = os.path.splitext(os.path.basename(name))[0]
                exact = audio_stem.lower() == song_stem.lower()
                if exact:
                    best = name
                    best_is_exact = True
                    break
                if not best_is_exact and _normalize_stem(audio_stem) == song_norm:
                    best = name
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
            haystack = " ".join(
                [song.title.lower(), song.artist.lower(), song.filename.lower()]
            )
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
            self.songs.sort(
                key=lambda s: (s.filename.lower(), _strip_articles(s.artist))
            )

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

    @staticmethod
    def from_dict(data: dict) -> SongLibrary:
        lib = SongLibrary()
        if data.get("version") == 2:
            lib.settings = Settings.from_dict(data.get("settings", {}))
            lib.songs = [Song.from_dict(d) for d in data.get("songs", [])]
            for song in lib.songs:
                if not song.zip_name and song.path:
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
