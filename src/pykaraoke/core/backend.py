#!/usr/bin/env python

"""
PyKaraoke Backend API
=====================

Headless backend service for PyKaraoke that provides a JSON-based API
for controlling playback, managing the library, and handling playlists.

This module decouples the karaoke engine from the UI layer, allowing
it to be controlled via IPC (stdin/stdout JSON protocol).

Architecture:
- Backend runs as a standalone service (no wx dependencies)
- Communicates via JSON commands and events on stdin/stdout
- Maintains playback state, playlist, and library
- Used by the Tauri desktop app via Rust bridge
"""

import argparse
import contextlib
import json
import logging
import os
import sys
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

# Suppress the pygame "Hello from the pygame community" banner that would
# otherwise be printed to stdout and corrupt the JSON IPC protocol.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# Core pykaraoke imports (business logic only)
try:
    from pykaraoke.config.constants import (  # noqa: F401 - Used for future expansion
        STATE_CLOSED,
        STATE_CLOSING,
        STATE_INIT,
        STATE_NOT_PLAYING,
        STATE_PAUSED,
        STATE_PLAYING,
    )
    from pykaraoke.core import database
    from pykaraoke.core.manager import manager
    from pykaraoke.core.player import PykPlayer  # noqa: F401 - Used for type hints
    from pykaraoke.players import cdg, kar, mpg  # noqa: F401 - Used for player creation

    IMPORTS_AVAILABLE = True
except (ImportError, SyntaxError) as e:
    IMPORTS_AVAILABLE = False
    import warnings
    warnings.warn(
        f"PyKaraoke dependencies not available: {e}. Backend will not function.", stacklevel=2
    )

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BackendState(Enum):
    """Playback state enumeration"""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    LOADING = "loading"
    ERROR = "error"


class PyKaraokeBackend:
    """
    Main backend service class that manages playback, library, and state.

    Provides a command-based API for controlling karaoke playback without
    requiring any UI dependencies.
    """

    def __init__(self):
        if not IMPORTS_AVAILABLE:
            logger.error("PyKaraoke dependencies not available - backend cannot function")
            raise RuntimeError("Backend dependencies not available")

        self.state = BackendState.IDLE
        self.current_player: Any | None = None
        self.current_song: Any | None = None
        self.playlist: list[Any] = []
        self.playlist_index: int = -1
        self.song_db: Any | None = None
        self.volume: float = 0.75
        self.position_ms: int = 0
        self.duration_ms: int = 0
        self.error_message: str | None = None
        self.event_callback: Callable[[dict[str, Any]], None] | None = None

        self._command_handlers: dict[str, Callable] = {
            "play": self._handle_play,
            "pause": lambda _: self._handle_pause(),
            "stop": lambda _: self._handle_stop(),
            "next": lambda _: self._handle_next(),
            "previous": lambda _: self._handle_previous(),
            "seek": self._handle_seek,
            "fast_forward": self._handle_fast_forward,
            "rewind": self._handle_rewind,
            "set_volume": self._handle_set_volume,
            "load_song": self._handle_load_song,
            "add_to_playlist": self._handle_add_to_playlist,
            "remove_from_playlist": self._handle_remove_from_playlist,
            "clear_playlist": lambda _: self._handle_clear_playlist(),
            "get_state": lambda _: {"status": "ok", "data": self.get_state()},
            "search_songs": self._handle_search_songs,
            "get_library": self._handle_get_library,
            "scan_library": self._handle_scan_library,
            "add_folder": self._handle_add_folder,
            "get_settings": lambda _: self._handle_get_settings(),
            "update_settings": self._handle_update_settings,
        }

        self._init_database()
        self._init_manager_options()
        logger.info("PyKaraoke backend initialized")

    def _init_manager_options(self):
        """Set manager.options to sensible defaults so player constructors
        never fall through to parse_args() on the process argv."""
        from optparse import Values
        settings = self.song_db.settings if self.song_db else None
        defaults = {
            "zoom_mode": getattr(settings, "cdg_zoom", "soft") if settings else "soft",
            "fullscreen": getattr(settings, "full_screen", False) if settings else False,
            "size_x": (settings.player_size[0] if settings and hasattr(settings, "player_size") else 640),
            "size_y": (settings.player_size[1] if settings and hasattr(settings, "player_size") else 480),
            "pos_x": None, "pos_y": None, "title": None, "hide_mouse": False,
            "fps": 30, "font_scale": 1.0,
            "num_channels": getattr(settings, "num_channels", 2) if settings else 2,
            "sample_rate": getattr(settings, "sample_rate", 44100) if settings else 44100,
            "buffer": getattr(settings, "buffer_ms", 50) if settings else 50,
            "nomusic": False, "dump": "", "dump_fps": 29.97, "validate": False,
        }
        manager.options = Values(defaults)
        if self.song_db:
            manager.apply_options(self.song_db)

    def _init_database(self):
        try:
            self.song_db = database.globalSongDB
            self.song_db.load_settings(None)
            self._auto_configure_folders()
            logger.info("Song database loaded")
        except (OSError, RuntimeError, ValueError) as e:
            logger.exception("Failed to initialize database")
            self.error_message = str(e)

    def _auto_configure_folders(self):
        if self.song_db.settings.folder_list:
            return
        for d in ["/app/songs", "/app/fixtures"]:
            if os.path.isdir(d):
                self.song_db.folder_add(d)
                logger.info("Auto-added song folder: %s", d)
        if self.song_db.settings.folder_list:
            self.song_db.save_settings()

    def set_event_callback(self, callback: Callable[[dict[str, Any]], None]):
        self.event_callback = callback

    def _emit_event(self, event_type: str, data: dict[str, Any] | None = None):
        event = {"type": event_type, "timestamp": time.time(), "data": data or {}}
        if self.event_callback:
            try:
                self.event_callback(event)
            except (TypeError, ValueError, RuntimeError):
                logger.exception("Error emitting event")

    def _emit_state_change(self):
        self._emit_event("state_changed", self.get_state())

    def handle_command(self, command: dict[str, Any]) -> dict[str, Any]:
        action = command.get("action")
        params = command.get("params", {})
        logger.debug("Handling command: %s", action)
        try:
            handler = self._command_handlers.get(action)
            if handler is None:
                return {"status": "error", "message": f"Unknown action: {action}"}
            return handler(params)
        except (NameError, RuntimeError, OSError, ValueError, TypeError, AttributeError) as e:
            logger.exception("Error handling command %s", action)
            return {"status": "error", "message": str(e)}

    def get_state(self) -> dict[str, Any]:
        self.poll()
        return {
            "playback_state": self.state.value,
            "current_song": self._song_to_dict(self.current_song) if self.current_song else None,
            "playlist": [self._song_to_dict(s) for s in self.playlist],
            "playlist_index": self.playlist_index,
            "volume": self.volume,
            "position_ms": self.position_ms,
            "duration_ms": self.duration_ms,
            "error": self.error_message,
        }

    def _song_to_dict(self, song: Any) -> dict[str, Any]:
        return {
            "title": getattr(song, "title", ""),
            "artist": getattr(song, "artist", ""),
            "filename": getattr(song, "display_filename", ""),
            "filepath": getattr(song, "filepath", ""),
            "zip_name": getattr(song, "zip_stored_name", None),
        }

    # ── Playback control ──────────────────────────────────────────

    def _handle_play(self, params: dict[str, Any]) -> dict[str, Any]:
        song_index = params.get("playlist_index")
        if song_index is not None:
            if 0 <= song_index < len(self.playlist):
                self.playlist_index = song_index
                self.current_song = self.playlist[song_index]
                return self._start_playback()
            return {"status": "error", "message": "Invalid playlist index"}
        elif self.current_player and self.state == BackendState.PAUSED:
            self.current_player.pause()
            self.state = BackendState.PLAYING
            self._emit_state_change()
            return {"status": "ok"}
        elif self.current_song:
            return self._start_playback()
        elif self.playlist:
            self.playlist_index = 0
            self.current_song = self.playlist[0]
            return self._start_playback()
        return {"status": "error", "message": "No song loaded"}

    def _handle_pause(self) -> dict[str, Any]:
        if self.current_player and self.state == BackendState.PLAYING:
            self.current_player.pause()
            self.state = BackendState.PAUSED
            self._emit_state_change()
            return {"status": "ok"}
        return {"status": "error", "message": "Not playing"}

    def _handle_stop(self) -> dict[str, Any]:
        if self.current_player:
            self.current_player.stop()
            self.current_player = None
        self.state = BackendState.STOPPED
        self.position_ms = 0
        self.duration_ms = 0
        self._emit_state_change()
        return {"status": "ok"}

    def _handle_next(self) -> dict[str, Any]:
        if self.playlist_index < len(self.playlist) - 1:
            self.playlist_index += 1
            self.current_song = self.playlist[self.playlist_index]
            return self._start_playback()
        return {"status": "error", "message": "No next song"}

    def _handle_previous(self) -> dict[str, Any]:
        if self.playlist_index > 0:
            self.playlist_index -= 1
            self.current_song = self.playlist[self.playlist_index]
            return self._start_playback()
        return {"status": "error", "message": "No previous song"}

    def _handle_seek(self, params: dict[str, Any]) -> dict[str, Any]:
        position_ms = params.get("position_ms", 0)
        self.position_ms = position_ms
        if self.current_player:
            try:
                self.current_player.seek(position_ms)
            except Exception as e:
                logger.exception("Seek error")
                return {"status": "error", "message": str(e)}
        self._emit_state_change()
        return {"status": "ok"}

    def _handle_fast_forward(self, params: dict[str, Any]) -> dict[str, Any]:
        amount_seconds = max(1, params.get("amount_seconds", 10))
        new_position = min(self.position_ms + amount_seconds * 1000, self.duration_ms)
        return self._handle_seek({"position_ms": new_position})

    def _handle_rewind(self, params: dict[str, Any]) -> dict[str, Any]:
        amount_seconds = max(1, params.get("amount_seconds", 10))
        new_position = max(0, self.position_ms - amount_seconds * 1000)
        return self._handle_seek({"position_ms": new_position})

    def _handle_set_volume(self, params: dict[str, Any]) -> dict[str, Any]:
        volume = max(0.0, min(1.0, params.get("volume", 0.75)))
        self.volume = volume
        if manager.initialized:
            try:
                manager.set_volume(volume)
            except Exception:
                logger.exception("Failed to set volume on player")
        self._emit_event("volume_changed", {"volume": volume})
        return {"status": "ok"}

    def _start_playback(self) -> dict[str, Any]:
        if not self.current_song:
            return {"status": "error", "message": "No song loaded"}
        try:
            self.state = BackendState.LOADING
            self._emit_state_change()
            if self.current_player:
                self.current_player.close()
            self.current_player = self.current_song.make_player(
                self.song_db,
                error_notify_callback=self._on_player_error,
                done_callback=self._on_song_finished,
            )
            if not self.current_player:
                raise RuntimeError("Failed to create player")
            if hasattr(self.current_player, "is_valid") and not self.current_player.is_valid:
                raise RuntimeError("Song file could not be parsed (corrupt or unsupported format)")
            self.current_player.play()
            self.state = BackendState.PLAYING
            self.position_ms = 0
            self.duration_ms = int(self.current_player.get_length() * 1000) if hasattr(self.current_player, 'get_length') else 0
            manager.set_volume(self.volume)
            self._emit_state_change()
            return {"status": "ok"}
        except SystemExit:
            raise
        except Exception as e:
            logger.exception("Playback error")
            self.state = BackendState.ERROR
            self.error_message = str(e)
            self._emit_state_change()
            return {"status": "error", "message": str(e)}

    def _on_player_error(self, error: str):
        logger.error("Player error: %s", error)
        self.error_message = error
        self.state = BackendState.ERROR
        self._emit_event("playback_error", {"error": error})

    def _on_song_finished(self):
        logger.info("Song finished")
        self._emit_event("song_finished", {})
        if self.playlist_index < len(self.playlist) - 1:
            self.playlist_index += 1
            self.current_song = self.playlist[self.playlist_index]
            self._start_playback()
        else:
            self.current_player = None
            self.current_song = None
            self.position_ms = 0
            self.duration_ms = 0
            self.state = BackendState.IDLE
            self._emit_state_change()

    # ── Playlist management ───────────────────────────────────────

    def _handle_load_song(self, params: dict[str, Any]) -> dict[str, Any]:
        filepath = params.get("filepath")
        if not filepath:
            return {"status": "error", "message": "filepath required"}
        try:
            self.current_song = self.song_db.make_song_struct(filepath)
            self._emit_state_change()
            return {"status": "ok"}
        except (RuntimeError, ValueError, OSError) as e:
            logger.exception("Failed to load song %s", filepath)
            return {"status": "error", "message": str(e)}

    def _handle_add_to_playlist(self, params: dict[str, Any]) -> dict[str, Any]:
        filepath = params.get("filepath")
        if not filepath:
            return {"status": "error", "message": "filepath required"}
        try:
            song = self.song_db.make_song_struct(filepath)
            self.playlist.append(song)
            logger.info("Song enqueued: %s (queue length=%d)", song.title, len(self.playlist))
            self._emit_event(
                "playlist_updated", {"playlist": [self._song_to_dict(s) for s in self.playlist]}
            )
            return {"status": "ok"}
        except Exception as e:
            logger.exception("Failed to enqueue %s", filepath)
            return {"status": "error", "message": str(e)}

    def _handle_remove_from_playlist(self, params: dict[str, Any]) -> dict[str, Any]:
        index = params.get("index")
        if index is None or not (0 <= index < len(self.playlist)):
            return {"status": "error", "message": "Invalid index"}
        del self.playlist[index]
        if self.playlist_index >= index and self.playlist_index > 0:
            self.playlist_index -= 1
        self._emit_event(
            "playlist_updated", {"playlist": [self._song_to_dict(s) for s in self.playlist]}
        )
        return {"status": "ok"}

    def _handle_clear_playlist(self) -> dict[str, Any]:
        self.playlist = []
        self.playlist_index = -1
        self._emit_event("playlist_updated", {"playlist": []})
        return {"status": "ok"}

    # ── Library management ────────────────────────────────────────

    def _handle_search_songs(self, params: dict[str, Any]) -> dict[str, Any]:
        query = params.get("query", "")
        try:
            results = self.song_db.search_database(query, database.AppYielder())
            return {
                "status": "ok",
                "data": {"results": [self._song_to_dict(song) for song in results]},
            }
        except (AttributeError, ValueError) as e:
            return {"status": "error", "message": str(e)}

    def _handle_get_library(self, _params: dict[str, Any]) -> dict[str, Any]:
        try:
            songs = self.song_db.song_list if hasattr(self.song_db, "song_list") else []
            return {"status": "ok", "data": {"songs": [self._song_to_dict(song) for song in songs]}}
        except (AttributeError, ValueError) as e:
            return {"status": "error", "message": str(e)}

    def _handle_scan_library(self, _params: dict[str, Any]) -> dict[str, Any]:
        logger.info("Starting library scan")
        try:
            self.song_db.build_search_database(
                database.AppYielder(), database.BusyCancelDialog()
            )
            self.song_db.select_sort("filename")
            self.song_db.save_database()
            count = len(self.song_db.full_song_list)
            logger.info("Library scan complete: %d songs found", count)
            self._emit_event("library_scan_complete", {"song_count": count})
            return {"status": "ok", "message": "Library scan complete", "data": {"song_count": count}}
        except (OSError, RuntimeError, ValueError) as e:
            return {"status": "error", "message": str(e)}

    def _handle_add_folder(self, params: dict[str, Any]) -> dict[str, Any]:
        folder = params.get("folder")
        if not folder:
            return {"status": "error", "message": "folder required"}
        try:
            self.song_db.folder_add(folder)
            self.song_db.save_settings()
            self.song_db.add_file(folder)
            self.song_db.select_sort("filename")
            self.song_db.save_database()
            self._emit_event("library_scan_complete", {})
            return {"status": "ok", "message": f"Folder added and scanned: {folder}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Settings ──────────────────────────────────────────────────

    def _handle_get_settings(self) -> dict[str, Any]:
        settings = self.song_db.settings if hasattr(self.song_db, "settings") else {}
        folder_list = (
            self.song_db.get_folder_list()
            if hasattr(self.song_db, "get_folder_list")
            else []
        )
        return {
            "status": "ok",
            "data": {
                "fullscreen": getattr(settings, "full_screen", False),
                "player_size": getattr(settings, "player_size", [640, 480]),
                "zoom_mode": getattr(settings, "cdg_zoom", "soft"),
                "folder_list": folder_list,
            },
        }

    def _handle_update_settings(self, params: dict[str, Any]) -> dict[str, Any]:
        logger.info("Updating settings: %d key(s)", len(params))
        try:
            settings = self.song_db.settings if hasattr(self.song_db, "settings") else None
            if settings is None:
                return {"status": "error", "message": "Settings not available"}
            changed = False
            if "fullscreen" in params:
                settings.full_screen = bool(params["fullscreen"])
                if hasattr(manager, "options") and hasattr(manager.options, "fullscreen"):
                    manager.options.fullscreen = settings.full_screen
                changed = True
            if "zoom_mode" in params:
                settings.cdg_zoom = str(params["zoom_mode"])
                if hasattr(manager, "options") and hasattr(manager.options, "zoom_mode"):
                    manager.options.zoom_mode = settings.cdg_zoom
                changed = True
            if changed:
                self.song_db.save_settings()
            return {"status": "ok", "message": "Settings updated"}
        except Exception as e:
            logger.exception("Error updating settings")
            return {"status": "error", "message": str(e)}

    # ── Polling / lifecycle ───────────────────────────────────────

    def poll(self):
        if self.current_player:
            try:
                manager.poll()
            except Exception:
                logger.exception("Manager poll error")
            if self.state == BackendState.PLAYING:
                with contextlib.suppress(Exception):
                    self.position_ms = self.current_player.get_pos()

    def shutdown(self):
        logger.info("Shutting down backend")
        if self.current_player:
            self.current_player.close()
        manager.quit()


def create_stdio_server(backend: PyKaraokeBackend, *, json_out=None):
    """
    Create a stdio-based command server.
    Reads JSON commands from stdin and writes responses to stdout.

    Redirects sys.stdout to stderr so stray print() calls never corrupt
    the JSON IPC stream that the Tauri/Rust host reads.
    """
    if json_out is None:
        json_out = sys.stdout
        sys.stdout = sys.stderr

    def _write_json(obj: dict[str, Any]):
        json_out.write(json.dumps(obj))
        json_out.write("\n")
        json_out.flush()

    def event_callback(event: dict[str, Any]):
        _write_json({"type": "event", "event": event})

    backend.set_event_callback(event_callback)
    logger.info("Starting stdio server")

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                command = json.loads(line)
                response = backend.handle_command(command)
                _write_json({"type": "response", "response": response})
            except json.JSONDecodeError as e:
                _write_json({
                    "type": "response",
                    "response": {"status": "error", "message": f"Invalid JSON: {e}"},
                })
            except (ValueError, TypeError) as e:
                _write_json({
                    "type": "response",
                    "response": {"status": "error", "message": str(e)},
                })
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        backend.shutdown()


def main():
    """
    Main entry point. Runs in stdio mode (read commands from stdin,
    write responses to stdout) for use with the Tauri Rust bridge.
    """
    parser = argparse.ArgumentParser(
        description="PyKaraoke Backend - Headless karaoke service",
    )
    parser.add_argument(
        "--mode", type=str, choices=["stdio", "http"], default="stdio",
        help="Ignored — always uses stdio mode (kept for backward compatibility)",
    )
    parser.parse_args()

    logger.info("PyKaraoke Backend starting in stdio mode")

    # In stdio mode the real stdout is the JSON IPC channel to the Rust
    # host.  Redirect sys.stdout -> stderr *before* creating the backend
    # so that stray print() calls during initialisation never corrupt
    # the protocol stream.
    json_out = sys.stdout
    sys.stdout = sys.stderr

    backend = PyKaraokeBackend()
    create_stdio_server(backend, json_out=json_out)


if __name__ == "__main__":
    main()
