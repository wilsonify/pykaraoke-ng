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
            # Expect at least 2 parts: artist, title…
            if len(parts) >= 2:
                return ParsedSong(
                    artist=parts[0].strip(),
                    title="-".join(parts[1:]).strip(),
                )

        logger.debug("Could not parse filename stem %r; returning as title only.", stem)
        return ParsedSong(title=stem.strip())
