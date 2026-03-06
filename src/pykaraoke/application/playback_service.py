"""Playback service for controlling karaoke playback.

Canonical location for the base player class. The implementation
currently lives in :mod:`pykaraoke.core.player` and is re-exported here
so that callers can start migrating to the new layered import path::

    from pykaraoke.application.playback_service import PykPlayer
"""

from pykaraoke.core.player import *  # noqa: F401,F403

__all__ = [
    "PykPlayer",
]
