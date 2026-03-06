"""Core business logic and engines.

This package is the legacy home of the karaoke engine modules.
New code should prefer the layered import paths::

    pykaraoke.domain.*            — pure logic and data structures
    pykaraoke.application.*       — orchestration and services
    pykaraoke.infrastructure.*    — database, players, native extensions
    pykaraoke.interfaces.*        — entry points (Tauri, CLI, HTTP)

All original imports (e.g. ``from pykaraoke.core.database import SongDB``)
continue to work and are fully supported.
"""
