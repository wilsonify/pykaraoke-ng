"""Karaoke session manager.

Canonical location for session management and coordination. The
implementation currently lives in :mod:`pykaraoke.core.manager` and is
re-exported here so that callers can start migrating to the new
layered import path::

    from pykaraoke.application.karaoke_manager import manager
"""

from pykaraoke.core.manager import PykManager, manager  # noqa: F401

__all__ = [
    "PykManager",
    "manager",
]
