"""Song database infrastructure.

Canonical location for the song database and library persistence logic.
The implementation currently lives in :mod:`pykaraoke.core.database` and
is re-exported here so that callers can start migrating to the new
layered import path::

    from pykaraoke.infrastructure.database.database import SongDB
"""

from pykaraoke.core.database import (  # noqa: F401
    SettingsStruct,
    SongDB,
    SongStruct,
    globalSongDB,
)

__all__ = [
    "SettingsStruct",
    "SongDB",
    "SongStruct",
    "globalSongDB",
]
