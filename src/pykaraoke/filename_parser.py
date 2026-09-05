"""Robust filename parser for karaoke files.

Parses artist, title, disc, and track information from karaoke filenames.
Handles common naming patterns including multiple dashes, directory path
dashes, and configurable strategies.

Supported patterns:
  - "Artist - Title.mp3"                (space-dash-space separator)
  - "Artist - Title - Live.mp3"         (multiple space-dash-space segments)
  - "Artist - Title (Remix).cdg"        (parenthetical modifiers)
  - "SC1234-05-John Doe-My Song.cdg"    (legacy Disc-Track-Artist-Title)
  - "SC123405-John Doe-My Song.cdg"     (legacy DiscTrack-Artist-Title)
  - "SC1234-John Doe-My Song.cdg"       (legacy Disc-Artist-Title)
  - "John Doe-My Song.cdg"              (legacy Artist-Title)
"""

import logging
import os
import re
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger(__name__)


class FileNameType(IntEnum):
    """Supported legacy filename naming conventions."""

    DISC_TRACK_ARTIST_TITLE = 0  # Disc-Track-Artist-Title.ext
    DISCTRACK_ARTIST_TITLE = 1  # DiscTrack-Artist-Title.ext
    DISC_ARTIST_TITLE = 2  # Disc-Artist-Title.ext
    ARTIST_TITLE = 3  # Artist-Title.ext


@dataclass
class ParsedSong:
    """Result of parsing a karaoke filename."""

    artist: str = ""
    title: str = ""
    disc: str = ""
    track: str = ""


# Regex matching " - " with optional surrounding whitespace
_SPACE_DASH_RE = re.compile(r"\s+-\s+")


def _is_abbreviation_part(part: str) -> bool:
    """Return True if *part* looks like a short all-caps abbreviation.

    Examples of abbreviation parts: "AC", "DC", "DJ", "MC", "ZZ".
    A part qualifies when it has at least one alphabetic character, every
    *cased* character is uppercase, and the total length is at most 3.
    This identifies artist-name components that contain internal dashes
    (e.g. "AC-DC") so they can be grouped together before the title begins.
    """
    return bool(part) and len(part) <= 3 and part.isupper() and any(c.isalpha() for c in part)


class FilenameParser:
    """Parses karaoke filenames to extract artist, title, disc, and track.

    Strategy:
    1. Extracts only the basename of the filepath so that directory path
       dashes are always ignored.
    2. Strips the file extension.
    3. If the basename contains a " - " (space-dash-space) separator the
       modern split strategy is used: the first segment becomes the artist
       and all remaining segments are joined back as the title.
    4. Otherwise the legacy dash-split strategy is applied according to
       ``file_name_type``.

    Args:
        file_name_type: The legacy naming scheme to fall back to when the
            " - " separator is absent.  Defaults to
            ``FileNameType.ARTIST_TITLE``.
    """

    def __init__(self, file_name_type: FileNameType = FileNameType.ARTIST_TITLE) -> None:
        self.file_name_type = file_name_type

    def parse(self, filepath: str) -> ParsedSong:
        """Parse *filepath* and return a :class:`ParsedSong`.

        Args:
            filepath: Full or relative file path (directory components are
                ignored).

        Returns:
            :class:`ParsedSong` with extracted fields.
        """
        # Normalise path separators so Windows paths are handled on all
        # platforms, then strip directory components so dashes in directory
        # names do not interfere with parsing.
        filename = os.path.basename(filepath.replace("\\", "/"))
        # Remove file extension.
        stem, _ = os.path.splitext(filename)

        if _SPACE_DASH_RE.search(stem):
            return self._parse_space_dash(stem)

        return self._parse_legacy(stem)

    def parse_zip_path(self, zip_stored_name: str) -> ParsedSong:
        """Parse a ZIP member path, using directory structure as a fallback.

        First tries to parse the filename component using the regular strategy
        (``parse``).  If that yields no artist — e.g. the filename is a plain
        title with no separator — uses the *parent directory* component as the
        artist.

        This supports the common karaoke ZIP layout::

            Language/Artist/Title.kar
            Artist/Title.kar

        Args:
            zip_stored_name: The path of the member inside the ZIP archive,
                using forward or backward slashes.

        Returns:
            :class:`ParsedSong` with extracted fields.
        """
        # Try regular parsing on the basename first.
        result = self.parse(zip_stored_name)
        if result.artist:
            return result

        # Fallback: derive artist from the parent directory component.
        # result.title already holds the filename stem from the parse() call above.
        normalized = zip_stored_name.replace("\\", "/")
        components = normalized.split("/")
        if len(components) >= 2:
            artist = components[-2].strip()
            if artist:
                return ParsedSong(artist=artist, title=result.title)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_space_dash(self, stem: str) -> ParsedSong:
        """Handle the modern ``"Artist - Title"`` family of patterns.

        All text before the first " - " separator is treated as the artist;
        everything after (including any additional " - " segments) becomes
        the title, so that subtitles like "Live" or "(Remix)" are preserved.
        """
        parts = _SPACE_DASH_RE.split(stem, maxsplit=1)
        if len(parts) == 2:
            return ParsedSong(artist=parts[0].strip(), title=parts[1].strip())
        # Only one part means the regex found nothing useful; fall back.
        return ParsedSong(title=stem.strip())

    def _parse_legacy(self, stem: str) -> ParsedSong:
        """Handle the legacy ``"Disc-Track-Artist-Title"`` family of patterns.

        Uses the configured :attr:`file_name_type` to determine how many
        leading fields (disc, track) to consume before artist and title.
        Any *extra* dashes within the title are preserved by joining the
        remaining parts.
        """
        parts = stem.split("-")

        if self.file_name_type == FileNameType.DISC_TRACK_ARTIST_TITLE:
            # Expect at least 4 parts: disc, track, artist, title…
            if len(parts) >= 4:
                return ParsedSong(
                    disc=parts[0].strip(),
                    track=parts[1].strip(),
                    artist=parts[2].strip(),
                    title="-".join(parts[3:]).strip(),
                )
        elif self.file_name_type in (
            FileNameType.DISCTRACK_ARTIST_TITLE,
            FileNameType.DISC_ARTIST_TITLE,
        ):
            # Expect at least 3 parts: disc(/track), artist, title…
            if len(parts) >= 3:
                return ParsedSong(
                    disc=parts[0].strip(),
                    artist=parts[1].strip(),
                    title="-".join(parts[2:]).strip(),
                )
        elif self.file_name_type == FileNameType.ARTIST_TITLE:
            return self._parse_artist_title(parts)

        logger.debug("Could not parse filename stem %r; returning as title only.", stem)
        return ParsedSong(title=stem.strip())

    def _parse_artist_title(self, parts: list) -> ParsedSong:
        """Handle the ``"Artist-Title"`` legacy pattern.

        Includes a heuristic for artists whose names contain dashes
        (e.g. "AC-DC"): consecutive short all-caps abbreviation parts
        are grouped into the artist name.
        """
        if len(parts) < 2:
            return ParsedSong(title="-".join(parts).strip())

        if _is_abbreviation_part(parts[0]):
            i = 1
            while i < len(parts) - 1 and _is_abbreviation_part(parts[i]):
                i += 1
            return ParsedSong(
                artist="-".join(parts[:i]).strip(),
                title="-".join(parts[i:]).strip(),
            )

        return ParsedSong(
            artist=parts[0].strip(),
            title="-".join(parts[1:]).strip(),
        )
