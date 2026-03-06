"""CD+G format player.

Canonical location for the CD+G player implementation. The code
currently lives in :mod:`pykaraoke.players.cdg` and is re-exported
here for the new layered architecture.
"""

from pykaraoke.players.cdg import (  # noqa: F401
    CdgPlayer,
    main,
)

__all__ = [
    "CdgPlayer",
    "main",
]

if __name__ == "__main__":
    main()
