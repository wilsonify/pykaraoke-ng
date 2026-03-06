"""MPEG/AVI video player.

Canonical location for the MPEG player implementation. The code
currently lives in :mod:`pykaraoke.players.mpg` and is re-exported
here for the new layered architecture.
"""

from pykaraoke.players.mpg import *  # noqa: F401,F403
from pykaraoke.players.mpg import main  # noqa: F401

if __name__ == "__main__":
    main()
