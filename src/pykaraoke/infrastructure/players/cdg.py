"""CD+G format player.

Canonical location for the CD+G player implementation. The code
currently lives in :mod:`pykaraoke.players.cdg` and is re-exported
here for the new layered architecture.
"""

from pykaraoke.players.cdg import *  # noqa: F401,F403
from pykaraoke.players.cdg import main  # noqa: F401

if __name__ == "__main__":
    main()
