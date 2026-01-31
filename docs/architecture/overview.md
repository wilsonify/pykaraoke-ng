# PyKaraoke NG Architecture Documentation

[← Back to Home](../index.md) | [Developer Guide](../developers.md)

---

## Migration from wxPython to Tauri

This document describes the architectural transformation of PyKaraoke from a monolithic wxPython application to a modern, decoupled Tauri-based architecture.

## Problem Statement

The original PyKaraoke application was tightly coupled to wxPython:
- UI and business logic were intertwined
- Difficult to modernize the UI
- Limited to platforms where wxPython is available
- Hard to test components independently
- No clear separation of concerns

## Solution Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────────────────────┐
│                         Desktop Application                       │
│                                                                    │
│  ┌─────────────────┐           ┌──────────────────────────┐     │
│  │  Web Frontend   │           │   Tauri Shell (Rust)     │     │
│  │  (HTML/CSS/JS)  │◄─────────►│   • Window Management    │     │
│  │                 │   Events  │   • Native Integration   │     │
│  │  • UI Views     │           │   • IPC Router           │     │
│  │  • User Input   │           │   • Process Manager      │     │
│  └─────────────────┘           └──────────────────────────┘     │
│                                           │                       │
│                                           │ stdin/stdout          │
│                                           │ (JSON Protocol)       │
│                                           ▼                       │
│                          ┌─────────────────────────────┐         │
│                          │  Python Backend Service     │         │
│                          │  (pykbackend.py)            │         │
│                          │                             │         │
│                          │  ┌──────────────────────┐  │         │
│                          │  │  Command Processor   │  │         │
│                          │  └──────────────────────┘  │         │
│                          │            ▼                │         │
│                          │  ┌──────────────────────┐  │         │
│                          │  │  Core Engine         │  │         │
│                          │  │  (pykplayer,         │  │         │
│                          │  │   pykmanager, etc)   │  │         │
│                          │  └──────────────────────┘  │         │
│                          │            ▼                │         │
│                          │  ┌──────────────────────┐  │         │
│                          │  │  Database & Library  │  │         │
│                          │  │  (pykdb)             │  │         │
│                          │  └──────────────────────┘  │         │
│                          │            ▼                │         │
│                          │  ┌──────────────────────┐  │         │
│                          │  │  Players             │  │         │
│                          │  │  (pycdg, pykar,      │  │         │
│                          │  │   pympg)             │  │         │
│                          │  └──────────────────────┘  │         │
│                          └─────────────────────────────┘         │
└──────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### 1. Python Backend Service (`pykbackend.py`)

**Purpose**: Headless service managing all karaoke business logic

**Responsibilities**:
- Playback control (play, pause, stop, seek)
- Song database management
- Playlist management
- Library scanning and indexing
- Settings persistence
- Event emission to frontend

**Key Features**:
- Runs as subprocess
- Communicates via JSON over stdin/stdout
- No UI dependencies (no wx imports)
- Maintains authoritative state
- Emits events on state changes

**API Design**:
- Command-based interface
- Asynchronous event notifications
- Stateless request/response pattern
- Clear error handling

### 2. Tauri Shell (Rust)

**Purpose**: Native desktop wrapper and IPC bridge

**Responsibilities**:
- Window lifecycle management
- Python subprocess management
- Message routing between frontend and Python
- Native OS integrations
- Security boundaries

**Key Components**:
- Process manager: Starts/stops Python backend
- IPC router: Forwards commands and events
- Event emitter: Notifies frontend of backend events
- State manager: Tracks backend connection status

### 3. Web Frontend (HTML/CSS/JavaScript)

**Purpose**: User interface layer

**Responsibilities**:
- Display current state
- Capture user interactions
- Send commands to backend
- Respond to backend events
- Provide visual feedback

**UI Sections**:
1. **Player Controls**: Play/pause/stop, progress, volume
2. **Library Browser**: Search, filter, browse songs
3. **Playlist Manager**: Queue, reorder, remove songs
4. **Settings**: Configure app behavior

**Technology Choices**:
- Vanilla JS (can be upgraded to React/Vue/Svelte)
- CSS Grid/Flexbox for layout
- Modern ES6+ features
- Event-driven updates

## Communication Protocol

### Message Format

All messages are JSON objects sent over stdin/stdout.

#### Command (Frontend → Backend)

```json
{
  "action": "string",       // Command name
  "params": {               // Optional parameters
    "key": "value"
  }
}
```

#### Response (Backend → Frontend)

```json
{
  "type": "response",
  "response": {
    "status": "ok|error",   // Result status
    "message": "string",    // Optional message
    "data": {}              // Optional data payload
  }
}
```

#### Event (Backend → Frontend)

```json
{
  "type": "event",
  "event": {
    "type": "event_name",
    "timestamp": 1234567890.123,
    "data": {}
  }
}
```

### Command Reference

| Action | Parameters | Description |
|--------|-----------|-------------|
| `play` | `playlist_index?` | Start/resume playback |
| `pause` | - | Pause playback |
| `stop` | - | Stop and reset |
| `next` | - | Next track |
| `previous` | - | Previous track |
| `seek` | `position_ms` | Seek to position |
| `set_volume` | `volume` (0-1) | Adjust volume |
| `load_song` | `filepath` | Load a song file |
| `add_to_playlist` | `filepath` | Add to queue |
| `remove_from_playlist` | `index` | Remove from queue |
| `clear_playlist` | - | Empty playlist |
| `search_songs` | `query` | Search library |
| `get_library` | - | List all songs |
| `scan_library` | - | Rescan folders |
| `add_folder` | `folder` | Add library folder |
| `get_state` | - | Get current state |
| `get_settings` | - | Get app settings |
| `update_settings` | `settings` | Update settings |

### Event Reference

| Event Type | Data | Description |
|-----------|------|-------------|
| `state_changed` | Full state object | State updated |
| `song_finished` | - | Track completed |
| `playback_error` | `error` | Error occurred |
| `playlist_updated` | `playlist` | Queue changed |
| `library_scan_complete` | - | Scan finished |
| `volume_changed` | `volume` | Volume adjusted |

## State Management

### Backend State

The Python backend maintains authoritative state:

```python
{
    "playback_state": "idle|playing|paused|stopped|loading|error",
    "current_song": {
        "title": str,
        "artist": str,
        "filename": str,
        "filepath": str,
        "zip_name": str?
    },
    "playlist": [SongStruct, ...],
    "playlist_index": int,
    "volume": float (0-1),
    "position_ms": int,
    "duration_ms": int,
    "error": str?
}
```

### Frontend State

Frontend maintains local UI state:
- Search results (from search queries)
- UI element states (expanded panels, etc.)
- Form inputs
- Temporary UI feedback

The frontend regularly polls `get_state` to sync with backend.

## Migration Strategy

### Phase 1: Backend Extraction ✅

1. Created `pykbackend.py` - headless backend service
2. Extracted core logic from wx dependencies
3. Implemented JSON command API
4. Added event emission system

### Phase 2: Tauri Setup ✅

1. Created Tauri project structure
2. Implemented Rust IPC handlers
3. Created Python subprocess manager
4. Configured message routing

### Phase 3: Frontend Development ✅

1. Built web UI (HTML/CSS/JS)
2. Implemented player controls
3. Created library browser
4. Added playlist management

### Phase 4: Integration (In Progress)

- [ ] Test end-to-end communication
- [ ] Verify all playback functions
- [ ] Validate state synchronization
- [ ] Add error handling
- [ ] Performance tuning

### Phase 5: Testing & Polish

- [ ] Write integration tests
- [ ] Add unit tests for backend
- [ ] UI/UX improvements
- [ ] Documentation
- [ ] Packaging and distribution

## Benefits of New Architecture

1. **Separation of Concerns**: UI and logic are decoupled
2. **Modern UI**: Web technologies enable rich, responsive UI
3. **Testability**: Components can be tested independently
4. **Cross-Platform**: Tauri supports Windows, macOS, Linux
5. **Maintainability**: Clear interfaces and boundaries
6. **Extensibility**: Easy to add new features
7. **Performance**: Rust runtime is lightweight and fast
8. **Distribution**: Single binary with embedded assets

## Development Workflow

### Running the App

```bash
# Development mode
cd tauri-app
cargo tauri dev

# Production build
cargo tauri build
```

### Testing Backend Standalone

```bash
# Run backend service
python3 pykbackend.py

# Send test commands (in another terminal)
echo '{"action":"get_state","params":{}}' | python3 pykbackend.py
```

### Debugging

- **Backend logs**: Python logging to stderr
- **Rust logs**: Printed to Tauri console
- **Frontend logs**: Browser DevTools console

## Future Enhancements

1. **WebSocket Support**: Replace stdio with WebSocket for better performance
2. **HTTP API**: Add REST API for remote control
3. **Plugin System**: Allow extensions via plugins
4. **Cloud Sync**: Sync playlists and settings
5. **Mobile App**: Build companion mobile app
6. **Web Version**: Deploy frontend as web app with backend as service

## Backward Compatibility

The original wxPython code remains available in:
- `pykaraoke.py` - Original GUI app
- Can be run separately for legacy support
- Migration is non-destructive

## Technical Decisions

### Why Tauri vs Electron?

- **Smaller bundle**: ~3MB vs ~100MB
- **Better performance**: Rust runtime
- **Lower memory**: System webview
- **Security**: Built-in security features

### Why stdio vs WebSocket?

- **Simplicity**: No network configuration
- **Security**: No exposed ports
- **Reliability**: Direct parent-child process
- **Can upgrade**: Easy to switch later

### Why JSON vs Protocol Buffers?

- **Simplicity**: Human-readable, debuggable
- **Flexibility**: Easy schema evolution
- **Tooling**: Native JS support
- **Sufficient**: Performance not critical

## Conclusion

This architecture modernizes PyKaraoke while preserving its core functionality. The separation of UI and logic enables:

- Easier maintenance and testing
- Modern, responsive user interface
- Better cross-platform support
- Foundation for future enhancements

The migration is incremental and non-breaking, allowing gradual adoption.
