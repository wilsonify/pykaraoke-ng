"""KAR/MIDI format player.

Canonical location for the KAR/MIDI player implementation. The code
currently lives in :mod:`pykaraoke.players.kar` and is re-exported
here for the new layered architecture.
"""

from pykaraoke.players.kar import *  # noqa: F401,F403

if __name__ == "__main__":
    from pykaraoke.players.kar import main

    main()
