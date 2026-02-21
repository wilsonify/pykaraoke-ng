#!/usr/bin/env python

"""
PyKaraoke Backend API
=====================

Headless backend service for PyKaraoke that provides a JSON-based API
for controlling playback, managing the library, and handling playlists.

This module decouples the karaoke engine from the UI layer, allowing
it to be controlled via IPC (stdin/stdout, WebSocket, or HTTP).

Architecture:
- Backend runs as a standalone service (no wx dependencies)
- Communicates via JSON commands and events
- Maintains playback state, playlist, and library
- Can be used with Tauri, Electron, or web frontends
"""

import argparse
import asyncio
import contextlib
import json
import logging
import os
import signal
import sys
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

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
    from pykaraoke.core.player import pykPlayer  # noqa: F401 - Used for type hints
    from pykaraoke.players import cdg, kar, mpg  # noqa: F401 - Used for player creation

    IMPORTS_AVAILABLE = True
except (ImportError, SyntaxError) as e:
    # Backend can still be imported for testing/documentation
    # but won't function without these dependencies
    IMPORTS_AVAILABLE = False
    import warnings

    warnings.warn(
        f"PyKaraoke dependencies not available: {e}. Backend will not function.", stacklevel=2
    )

# Configure logging
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
        """Initialize the backend service"""
        if not IMPORTS_AVAILABLE:
            logger.error("PyKaraoke dependencies not available - backend cannot function")
            raise RuntimeError("Backend dependencies not available")

        self.state = BackendState.IDLE
        self.current_player: Any | None = None  # pykPlayer when available
        self.current_song: Any | None = None  # database.SongStruct when available
        self.playlist: list[Any] = []  # List[database.SongStruct] when available
        self.playlist_index: int = -1
        self.song_db: Any | None = None  # database.SongDatabase when available
        self.volume: float = 0.75
        self.position_ms: int = 0
        self.duration_ms: int = 0
        self.error_message: str | None = None

        # Event callback for notifying frontend of state changes
        self.event_callback: Callable[[dict[str, Any]], None] | None = None

        # Initialize the song database
        self._init_database()

        logger.info("PyKaraoke backend initialized")

    def _init_database(self):
        """Initialize the song database"""
        try:
            self.song_db = database.globalSongDB
            self.song_db.LoadSettings(None)
            logger.info("Song database loaded")
        except (OSError, RuntimeError, ValueError) as e:
            logger.error(f"Failed to initialize database: {e}")
            self.error_message = str(e)

    def set_event_callback(self, callback: Callable[[dict[str, Any]], None]):
        """Set callback for sending events to frontend"""
        self.event_callback = callback

    def _emit_event(self, event_type: str, data: dict[str, Any] | None = None):
        """Emit an event to the frontend"""
        event = {"type": event_type, "timestamp": time.time(), "data": data or {}}
        if self.event_callback:
            try:
                self.event_callback(event)
            except (TypeError, ValueError, RuntimeError) as e:
                logger.error(f"Error emitting event: {e}")

    def _emit_state_change(self):
        """Emit a state change event"""
        self._emit_event("state_changed", self.get_state())

    def handle_command(self, command: dict[str, Any]) -> dict[str, Any]:
        """
        Handle a command from the frontend.

        Args:
            command: Dictionary with 'action' and optional parameters

        Returns:
            Response dictionary with status and data
        """
        action = command.get("action")
        params = command.get("params", {})

        logger.debug(f"Handling command: {action}")

        try:
            # Route to appropriate handler
            if action == "play":
                return self._handle_play(params)
            elif action == "pause":
                return self._handle_pause()
            elif action == "stop":
                return self._handle_stop()
            elif action == "next":
                return self._handle_next()
            elif action == "previous":
                return self._handle_previous()
            elif action == "seek":
                return self._handle_seek(params)
            elif action == "set_volume":
                return self._handle_set_volume(params)
            elif action == "load_song":
                return self._handle_load_song(params)
            elif action == "add_to_playlist":
                return self._handle_add_to_playlist(params)
            elif action == "remove_from_playlist":
                return self._handle_remove_from_playlist(params)
            elif action == "clear_playlist":
                return self._handle_clear_playlist()
            elif action == "get_state":
                return {"status": "ok", "data": self.get_state()}
            elif action == "search_songs":
                return self._handle_search_songs(params)
            elif action == "get_library":
                return self._handle_get_library(params)
            elif action == "scan_library":
                return self._handle_scan_library(params)
            elif action == "add_folder":
                return self._handle_add_folder(params)
            elif action == "get_settings":
                return self._handle_get_settings()
            elif action == "update_settings":
                return self._handle_update_settings(params)
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Error handling command {action}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def get_state(self) -> dict[str, Any]:
        """Get current backend state"""
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
        """Convert a SongStruct to a dictionary"""
        return {
            "title": getattr(song, "Title", ""),
            "artist": getattr(song, "Artist", ""),
            "filename": getattr(song, "DisplayFilename", ""),
            "filepath": getattr(song, "Filepath", ""),
            "zip_name": getattr(song, "ZipStoredName", None),
        }

    # Playback control handlers

    def _handle_play(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle play command"""
        song_index = params.get("playlist_index")

        if song_index is not None:
            # Play specific song from playlist
            if 0 <= song_index < len(self.playlist):
                self.playlist_index = song_index
                self.current_song = self.playlist[song_index]
                return self._start_playback()
            else:
                return {"status": "error", "message": "Invalid playlist index"}

        elif self.current_player and self.state == BackendState.PAUSED:
            # Resume from pause
            self.current_player.Pause()  # Toggle pause
            self.state = BackendState.PLAYING
            self._emit_state_change()
            return {"status": "ok"}

        elif self.current_song:
            # Play current song
            return self._start_playback()

        else:
            return {"status": "error", "message": "No song loaded"}

    def _handle_pause(self) -> dict[str, Any]:
        """Handle pause command"""
        if self.current_player and self.state == BackendState.PLAYING:
            self.current_player.Pause()
            self.state = BackendState.PAUSED
            self._emit_state_change()
            return {"status": "ok"}
        return {"status": "error", "message": "Not playing"}

    def _handle_stop(self) -> dict[str, Any]:
        """Handle stop command"""
        if self.current_player:
            self.current_player.Stop()
            self.state = BackendState.STOPPED
            self.position_ms = 0
            self._emit_state_change()
            return {"status": "ok"}
        return {"status": "ok"}  # Already stopped

    def _handle_next(self) -> dict[str, Any]:
        """Handle next track command"""
        if self.playlist_index < len(self.playlist) - 1:
            self.playlist_index += 1
            self.current_song = self.playlist[self.playlist_index]
            return self._start_playback()
        return {"status": "error", "message": "No next song"}

    def _handle_previous(self) -> dict[str, Any]:
        """Handle previous track command"""
        if self.playlist_index > 0:
            self.playlist_index -= 1
            self.current_song = self.playlist[self.playlist_index]
            return self._start_playback()
        return {"status": "error", "message": "No previous song"}

    def _handle_seek(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle seek command"""
        # Note: Seeking support depends on player implementation
        position_ms = params.get("position_ms", 0)
        self.position_ms = position_ms
        logger.warning("Seek functionality not yet implemented")
        return {"status": "ok", "message": "Seek not yet supported"}

    def _handle_set_volume(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle volume change"""
        volume = params.get("volume", 0.75)
        volume = max(0.0, min(1.0, volume))  # Clamp to [0, 1]
        self.volume = volume
        manager.SetVolume(volume)
        self._emit_event("volume_changed", {"volume": volume})
        return {"status": "ok"}

    def _start_playback(self) -> dict[str, Any]:
        """Start playing the current song"""
        if not self.current_song:
            return {"status": "error", "message": "No song loaded"}

        try:
            self.state = BackendState.LOADING
            self._emit_state_change()

            # Stop current player if any
            if self.current_player:
                self.current_player.Close()

            # Create new player for the song
            self.current_player = self.current_song.MakePlayer(
                self.song_db,
                errorNotifyCallback=self._on_player_error,
                doneCallback=self._on_song_finished,
            )

            if not self.current_player:
                raise Exception("Failed to create player")

            # Start playback
            self.current_player.Play()
            self.state = BackendState.PLAYING
            manager.SetVolume(self.volume)

            self._emit_state_change()
            return {"status": "ok"}

        except (RuntimeError, OSError, ValueError) as e:
            logger.error(f"Playback error: {e}")
            self.state = BackendState.ERROR
            self.error_message = str(e)
            self._emit_state_change()
            return {"status": "error", "message": str(e)}

    def _on_player_error(self, error: str):
        """Callback when player encounters an error"""
        logger.error(f"Player error: {error}")
        self.error_message = error
        self.state = BackendState.ERROR
        self._emit_event("playback_error", {"error": error})

    def _on_song_finished(self):
        """Callback when song finishes"""
        logger.info("Song finished")
        self._emit_event("song_finished", {})

        # Auto-advance to next song if available
        if self.playlist_index < len(self.playlist) - 1:
            self.playlist_index += 1
            self.current_song = self.playlist[self.playlist_index]
            self._start_playback()
        else:
            self.state = BackendState.IDLE
            self._emit_state_change()

    # Playlist management handlers

    def _handle_load_song(self, params: dict[str, Any]) -> dict[str, Any]:
        """Load a song for playback"""
        filepath = params.get("filepath")
        if not filepath:
            return {"status": "error", "message": "filepath required"}

        try:
            self.current_song = self.song_db.makeSongStruct(filepath)
            self._emit_state_change()
            return {"status": "ok"}
        except (RuntimeError, ValueError) as e:
            return {"status": "error", "message": str(e)}

    def _handle_add_to_playlist(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add song to playlist"""
        filepath = params.get("filepath")
        if not filepath:
            return {"status": "error", "message": "filepath required"}

        try:
            song = self.song_db.makeSongStruct(filepath)
            self.playlist.append(song)
            self._emit_event(
                "playlist_updated", {"playlist": [self._song_to_dict(s) for s in self.playlist]}
            )
            return {"status": "ok"}
        except (ValueError, IndexError, AttributeError) as e:
            return {"status": "error", "message": str(e)}

    def _handle_remove_from_playlist(self, params: dict[str, Any]) -> dict[str, Any]:
        """Remove song from playlist"""
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
        """Clear the playlist"""
        self.playlist = []
        self.playlist_index = -1
        self._emit_event("playlist_updated", {"playlist": []})
        return {"status": "ok"}

    # Library management handlers

    def _handle_search_songs(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search the song library"""
        query = params.get("query", "")
        try:
            results = self.song_db.SearchDatabase(query)
            return {
                "status": "ok",
                "data": {"results": [self._song_to_dict(song) for song in results]},
            }
        except (AttributeError, ValueError) as e:
            return {"status": "error", "message": str(e)}

    def _handle_get_library(self, params: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG002
        """Get library contents"""
        try:
            songs = self.song_db.SongList if hasattr(self.song_db, "SongList") else []
            return {"status": "ok", "data": {"songs": [self._song_to_dict(song) for song in songs]}}
        except (AttributeError, ValueError) as e:
            return {"status": "error", "message": str(e)}

    def _handle_scan_library(self, params: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG002
        """Scan library folders"""
        # This is a long-running operation that should be async
        logger.info("Starting library scan")
        try:
            self.song_db.BuildSearchDatabase()
            self._emit_event("library_scan_complete", {})
            return {"status": "ok", "message": "Scan started"}
        except (OSError, RuntimeError, ValueError) as e:
            return {"status": "error", "message": str(e)}

    def _handle_add_folder(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add a folder to the library"""
        folder = params.get("folder")
        if not folder:
            return {"status": "error", "message": "folder required"}

        try:
            self.song_db.FolderAdd(folder)
            return {"status": "ok"}
        except (OSError, ValueError, AttributeError) as e:
            return {"status": "error", "message": str(e)}

    # Settings handlers

    def _handle_get_settings(self) -> dict[str, Any]:
        """Get current settings"""
        settings = self.song_db.Settings if hasattr(self.song_db, "Settings") else {}
        return {
            "status": "ok",
            "data": {
                "fullscreen": getattr(settings, "FullScreen", False),
                "player_size": getattr(settings, "PlayerSize", [640, 480]),
                "zoom_mode": getattr(settings, "CdgZoom", "soft"),
            },
        }

    def _handle_update_settings(self, params: dict[str, Any]) -> dict[str, Any]:
        """Update settings"""
        # Update settings as needed
        logger.info("Updating settings: %d key(s)", len(params))
        return {"status": "ok", "message": "Settings updated"}

    def poll(self):
        """Poll the manager - should be called regularly"""
        if self.current_player:
            manager.Poll()

            # Update position
            if self.state == BackendState.PLAYING:
                with contextlib.suppress(BaseException):
                    self.position_ms = self.current_player.GetPos()

    def shutdown(self):
        """Shutdown the backend"""
        logger.info("Shutting down backend")
        if self.current_player:
            self.current_player.Close()
        manager.Quit()


def create_stdio_server(backend: PyKaraokeBackend):
    """
    Create a stdio-based command server.
    Reads JSON commands from stdin and writes responses to stdout.
    """

    def event_callback(event: dict[str, Any]):
        """Send events to frontend via stdout"""
        output = {"type": "event", "event": event}
        print(json.dumps(output), flush=True)

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
                output = {"type": "response", "response": response}
                print(json.dumps(output), flush=True)
            except json.JSONDecodeError as e:
                error_response = {
                    "type": "response",
                    "response": {"status": "error", "message": f"Invalid JSON: {e}"},
                }
                print(json.dumps(error_response), flush=True)
            except (ValueError, TypeError) as e:
                error_response = {
                    "type": "response",
                    "response": {"status": "error", "message": str(e)},
                }
                print(json.dumps(error_response), flush=True)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        backend.shutdown()


def create_http_server(backend: PyKaraokeBackend, host: str = "0.0.0.0", port: int = 8080):
    """
    Create an HTTP-based command server using FastAPI.
    Exposes a REST API for controlling the backend.
    """
    try:
        import uvicorn
        from fastapi import FastAPI, HTTPException
    except ImportError as e:
        logger.error(
            "FastAPI/Uvicorn not available. Install with: pip install fastapi uvicorn"
        )
        raise RuntimeError("HTTP mode requires fastapi and uvicorn") from e

    app = FastAPI(
        title="PyKaraoke Backend API",
        description="Headless karaoke backend with JSON API",
        version="0.7.5",
    )

    # Store events in memory for polling (simple implementation)
    events_queue: list[dict[str, Any]] = []

    def event_callback(event: dict[str, Any]):
        """Store events for retrieval via API"""
        events_queue.append(event)
        # Keep only last 100 events to prevent memory issues
        if len(events_queue) > 100:
            events_queue.pop(0)

    backend.set_event_callback(event_callback)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for container orchestration"""
        return {"status": "healthy", "timestamp": time.time()}

    # Get current state
    @app.get("/api/state")
    async def get_state():
        """Get current backend state"""
        return backend.get_state()

    # Execute a command
    @app.post("/api/command")
    async def execute_command(command: dict[str, Any]):
        """Execute a command on the backend"""
        try:
            response = backend.handle_command(command)
            return response
        except Exception as e:
            logger.error(f"Error executing command: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e

    # Get events (polling endpoint)
    @app.get("/api/events")
    async def get_events(since: float = 0):
        """Get events since a given timestamp"""
        filtered_events = [e for e in events_queue if e.get("timestamp", 0) > since]
        return {"events": filtered_events}

    # Clear events queue
    @app.delete("/api/events")
    async def clear_events():
        """Clear the events queue"""
        events_queue.clear()
        return {"status": "ok"}

    # Playback control endpoints
    @app.post("/api/play")
    async def play(playlist_index: int | None = None):
        """Start playback"""
        params = {}
        if playlist_index is not None:
            params["playlist_index"] = playlist_index
        return backend.handle_command({"action": "play", "params": params})

    @app.post("/api/pause")
    async def pause():
        """Pause playback"""
        return backend.handle_command({"action": "pause", "params": {}})

    @app.post("/api/stop")
    async def stop():
        """Stop playback"""
        return backend.handle_command({"action": "stop", "params": {}})

    @app.post("/api/next")
    async def next_track():
        """Next track"""
        return backend.handle_command({"action": "next", "params": {}})

    @app.post("/api/previous")
    async def previous_track():
        """Previous track"""
        return backend.handle_command({"action": "previous", "params": {}})

    @app.post("/api/volume")
    async def set_volume(volume: float):
        """Set volume (0.0 to 1.0)"""
        return backend.handle_command({"action": "set_volume", "params": {"volume": volume}})

    # Playlist management endpoints
    @app.post("/api/playlist/add")
    async def add_to_playlist(filepath: str):
        """Add song to playlist"""
        return backend.handle_command({"action": "add_to_playlist", "params": {"filepath": filepath}})

    @app.delete("/api/playlist/{index}")
    async def remove_from_playlist(index: int):
        """Remove song from playlist"""
        return backend.handle_command(
            {"action": "remove_from_playlist", "params": {"index": index}}
        )

    @app.delete("/api/playlist")
    async def clear_playlist():
        """Clear playlist"""
        return backend.handle_command({"action": "clear_playlist", "params": {}})

    # Library endpoints
    @app.get("/api/library/search")
    async def search_songs(query: str):
        """Search song library"""
        return backend.handle_command({"action": "search_songs", "params": {"query": query}})

    @app.get("/api/library")
    async def get_library():
        """Get library contents"""
        return backend.handle_command({"action": "get_library", "params": {}})

    @app.post("/api/library/scan")
    async def scan_library():
        """Scan library folders"""
        return backend.handle_command({"action": "scan_library", "params": {}})

    @app.post("/api/library/folder")
    async def add_folder(folder: str):
        """Add folder to library"""
        return backend.handle_command({"action": "add_folder", "params": {"folder": folder}})

    # Graceful shutdown handling
    def handle_shutdown(signum, frame):  # noqa: ARG001
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        # Use uvicorn's documented shutdown mechanism
        server.should_exit = True

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Configure uvicorn
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(config)

    logger.info(f"Starting HTTP server on {host}:{port}")

    try:
        # Run server
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        backend.shutdown()


def main():
    """
    Main entry point with mode selection.

    Supports two modes:
    1. stdio: Read commands from stdin, write responses to stdout (default for compatibility)
    2. http: Run HTTP API server

    Mode can be selected via:
    - Command-line argument: --mode stdio|http or --stdio|--http
    - Environment variable: BACKEND_MODE=stdio|http
    """
    parser = argparse.ArgumentParser(
        description="PyKaraoke Backend - Headless karaoke service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in stdio mode (default)
  python -m pykaraoke.core.backend --stdio

  # Run in HTTP mode
  python -m pykaraoke.core.backend --http

  # HTTP mode with custom host and port
  python -m pykaraoke.core.backend --http --host 127.0.0.1 --port 8080

  # Using environment variable
  BACKEND_MODE=http python -m pykaraoke.core.backend
        """,
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--stdio",
        action="store_const",
        const="stdio",
        dest="mode",
        help="Run in stdio mode (read from stdin, write to stdout)",
    )
    mode_group.add_argument(
        "--http",
        action="store_const",
        const="http",
        dest="mode",
        help="Run in HTTP API mode",
    )
    mode_group.add_argument(
        "--mode",
        type=str,
        choices=["stdio", "http"],
        help="Explicitly set the mode (stdio or http)",
    )

    # HTTP-specific options
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("PYKARAOKE_API_HOST", "0.0.0.0"),
        help="HTTP server host (default: 0.0.0.0, env: PYKARAOKE_API_HOST)",
    )

    # Parse port with error handling for invalid env var
    default_port = 8080
    try:
        port_env = os.getenv("PYKARAOKE_API_PORT")
        if port_env:
            default_port = int(port_env)
    except ValueError:
        logger.warning(f"Invalid PYKARAOKE_API_PORT value, using default: {default_port}")

    parser.add_argument(
        "--port",
        type=int,
        default=default_port,
        help="HTTP server port (default: 8080, env: PYKARAOKE_API_PORT)",
    )

    args = parser.parse_args()

    # Determine mode from args or environment
    mode = args.mode or os.getenv("BACKEND_MODE", "stdio")

    logger.info(f"PyKaraoke Backend starting in {mode} mode")

    # Create backend instance
    backend = PyKaraokeBackend()

    # Start appropriate server
    if mode == "http":
        create_http_server(backend, host=args.host, port=args.port)
    else:
        create_stdio_server(backend)


if __name__ == "__main__":
    main()
