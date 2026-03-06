"""Filename parsing for karaoke files.

Canonical location for filename parsing logic. The implementation
currently lives in :mod:`pykaraoke.core.filename_parser` and is
re-exported here so that callers can start migrating to the new
layered import path::

    from pykaraoke.domain.parsing.filename_parser import FilenameParser
"""

from pykaraoke.core.filename_parser import (  # noqa: F401
    FilenameParser,
    FileNameType,
    ParsedSong,
)

__all__ = [
    "FileNameType",
    "FilenameParser",
    "ParsedSong",
]
