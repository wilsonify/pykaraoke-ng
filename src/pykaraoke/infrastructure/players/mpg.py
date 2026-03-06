"""MPEG/AVI video player.

Canonical location for the MPEG player implementation. The code
currently lives in :mod:`pykaraoke.players.mpg` and is re-exported
here for the new layered architecture.
"""

from pykaraoke.players.mpg import (  # noqa: F401
    ExternalPlayer,
    MpgPlayer,
    main,
)

__all__ = [
    "ExternalPlayer",
    "MpgPlayer",
    "main",
]

if __name__ == "__main__":
    main()
