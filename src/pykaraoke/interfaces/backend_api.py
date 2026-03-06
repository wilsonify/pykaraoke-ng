"""Backend API entry point for UI / Tauri / CLI consumers.

Canonical location for the headless backend service. The implementation
currently lives in :mod:`pykaraoke.core.backend` and is re-exported here
so that callers can start migrating to the new layered import path::

    from pykaraoke.interfaces.backend_api import PyKaraokeBackend
"""

from pykaraoke.core.backend import (  # noqa: F401
    BackendState,
    PyKaraokeBackend,
    create_http_server,
    create_stdio_server,
    main,
)

__all__ = [
    "BackendState",
    "PyKaraokeBackend",
    "create_http_server",
    "create_stdio_server",
    "main",
]

if __name__ == "__main__":
    main()
