# Architecture Overview

[← Back to Home](../index.md) | [Developer Guide](../developers.md)

---

## Design

PyKaraoke-NG uses a **decoupled frontend/backend architecture**. The Python backend owns all business logic; lightweight desktop shells (Tauri, Electron) provide the UI.

```
┌───────────────────────────────────────────────┐
│            Desktop Application                │
│                                               │
│  ┌─────────────┐      ┌──────────────────┐   │
│  │ Web Frontend │◄────►│ Tauri Shell      │   │
│  │ (HTML/CSS/JS)│ IPC  │ (Rust)           │   │
│  └─────────────┘      └──────────────────┘   │
│                               │               │
│                        stdin / stdout         │
│                         (JSON lines)          │
│                               ▼               │
│                 ┌──────────────────────┐      │
│                 │  Python Backend      │      │
│                 │  (backend.py)        │      │
│                 │                      │      │
│                 │  • Playback engine   │      │
│                 │  • Song database     │      │
│                 │  • Playlist manager  │      │
│                 │  • Event emitter     │      │
│                 └──────────────────────┘      │
└───────────────────────────────────────────────┘
```

## Components

### Python Backend (`src/pykaraoke/core/backend.py`)

Headless service managing all karaoke logic. Supports two transport modes:

| Mode | Flag | Use Case |
|------|------|----------|
| **stdio** (default) | `--stdio` | Desktop apps — reads JSON from stdin, writes to stdout |
| **HTTP** | `--http` | Docker / Kubernetes — FastAPI + Uvicorn REST server |

See [Backend Modes](../backend-modes.md) for the full API reference.

### Tauri Shell (`src/runtimes/tauri/src-tauri/src/main.rs`)

Rust-based native desktop wrapper:
- Manages the Python subprocess lifecycle
- Routes IPC messages between the web frontend and the backend
- Emits events to the frontend on state changes

### Web Frontend (`src/runtimes/tauri/src/`)

Vanilla HTML/CSS/JS interface:
- Player controls (play, pause, stop, seek, volume)
- Library browser with search
- Playlist manager

Technology-agnostic — can be replaced with React, Vue, or Svelte.

## Communication Protocol

All messages are newline-delimited JSON over stdin/stdout.

### Command (Frontend → Backend)

```json
{"action": "play", "params": {"playlist_index": 0}}
```

### Response (Backend → Frontend)

```json
{"type": "response", "response": {"status": "ok"}}
```

### Event (Backend → Frontend)

```json
{"type": "event", "event": {"type": "state_changed", "timestamp": 1706745678.1, "data": {...}}}
```

### Command Reference

| Action | Parameters | Description |
|--------|-----------|-------------|
| `play` | `playlist_index?` | Start / resume playback |
| `pause` | — | Pause |
| `stop` | — | Stop and reset |
| `next` / `previous` | — | Navigate playlist |
| `seek` | `position_ms` | Seek to position |
| `set_volume` | `volume` (0–1) | Adjust volume |
| `add_to_playlist` | `filepath` | Queue a song |
| `remove_from_playlist` | `index` | Remove from queue |
| `clear_playlist` | — | Empty the playlist |
| `search_songs` | `query` | Search the library |
| `get_library` | — | List all songs |
| `scan_library` | — | Re-scan library folders |
| `add_folder` | `folder` | Add a folder to scan |
| `get_state` | — | Current state snapshot |

### Event Types

| Event | Description |
|-------|-------------|
| `state_changed` | Playback state updated |
| `song_finished` | Current track completed |
| `playback_error` | Error during playback |
| `playlist_updated` | Queue modified |
| `library_scan_complete` | Folder scan finished |
| `volume_changed` | Volume adjusted |

## State Model

The backend maintains the authoritative state:

```json
{
  "playback_state": "idle | playing | paused | stopped | loading | error",
  "current_song": {"title": "", "artist": "", "filepath": ""},
  "playlist": [],
  "playlist_index": 0,
  "volume": 0.75,
  "position_ms": 0,
  "duration_ms": 0
}
```

The frontend polls `get_state` to stay in sync.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Tauri over Electron** | ~10 MB bundle vs ~150 MB; lower memory; native webview |
| **stdio over WebSocket** | No exposed ports; no network config; easy to secure |
| **JSON over Protobuf** | Human-readable; easy to debug; sufficient performance |
| **Vanilla JS** | No build step; can upgrade to any framework later |
| **Python backend** | Reuses existing mature player code (pygame, CDG parser) |
