# Architecture Overview

[← Home](../index.md) · [Developer Guide](../developers.md)

---

## Design

PyKaraoke-NG uses a decoupled frontend/backend architecture. The Python
backend owns all business logic; the Tauri desktop shell provides a slim
sidebar UI.

```
┌──────────────────────────────────────────┐
│          Tauri Desktop App               │
│                                          │
│  ┌────────────┐    ┌─────────────────┐   │
│  │ Web UI     │◄──►│ Tauri Shell     │   │
│  │ (HTML/JS)  │IPC │ (Rust)          │   │
│  └────────────┘    └─────────────────┘   │
│                          │               │
│                   stdin / stdout         │
│                    (JSON lines)          │
│                          ▼               │
│              ┌─────────────────────┐     │
│              │  Python Backend     │     │
│              │  • Playback engine  │     │
│              │  • Song database    │     │
│              │  • Queue manager    │     │
│              │  • Event emitter    │     │
│              └─────────────────────┘     │
└──────────────────────────────────────────┘
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
- Search bar and song results
- Queue manager
- Playback controls (play, pause, stop, seek, volume)

Designed as a slim sidebar (300–450 px). See [UX Design Spec](../../specs/ux-design.md).

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
| **Tauri** | ~10 MB bundle; native webview; low memory |
| **stdio IPC** | No exposed ports; no network config; easy to secure |
| **JSON lines** | Human-readable; easy to debug; sufficient performance |
| **Vanilla JS** | No build step; zero frontend dependencies |
| **Python backend** | Reuses mature player code (pygame, CDG parser) |
| **Slim sidebar UI** | DJs need screen space for primary software (see [constitution §2](../../specs/constitution.md)) |
