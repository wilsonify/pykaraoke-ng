# PyKaraoke NG - Tauri Architecture

## Overview

This directory contains the Tauri-based desktop application for PyKaraoke NG. The architecture separates the Python karaoke engine (backend) from the web-based UI (frontend), enabling cross-platform desktop deployment without wxPython dependencies.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Tauri Desktop Shell                       │
│  ┌────────────────────┐         ┌──────────────────────┐   │
│  │   Web Frontend     │         │   Rust Backend       │   │
│  │  (HTML/CSS/JS)     │◄───────►│   (Tauri Core)       │   │
│  │                    │  IPC    │                      │   │
│  │  • Player UI       │         │  • Process Mgmt      │   │
│  │  • Library Browser │         │  • IPC Bridge        │   │
│  │  • Playlist        │         │  • Event Routing     │   │
│  └────────────────────┘         └──────────────────────┘   │
│                                           │                  │
│                                           │ stdio/JSON       │
│                                           ▼                  │
│                          ┌──────────────────────────┐       │
│                          │   Python Backend         │       │
│                          │   (pykbackend.py)        │       │
│                          │                          │       │
│                          │  • Playback Engine       │       │
│                          │  • Song Database         │       │
│                          │  • Media Control         │       │
│                          │  • Library Management    │       │
│                          └──────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Python Backend (`pykbackend.py`)

Headless service that provides:
- **Playback Control**: Play, pause, stop, seek, volume
- **Library Management**: Search, scan folders, database management
- **Playlist Management**: Add, remove, reorder songs
- **State Management**: Current song, position, playlist state
- **Event Emission**: Notifies frontend of state changes

**API**: JSON commands via stdin/stdout

### 2. Tauri Rust Backend (`src-tauri/src/main.rs`)

Manages:
- Python subprocess lifecycle
- IPC message routing between frontend and Python backend
- Event forwarding to frontend
- Native OS integration

**Commands**:
- `start_backend()`: Launch Python backend
- `send_command(action, params)`: Send command to Python
- `stop_backend()`: Shutdown Python backend

### 3. Web Frontend (`src/`)

Modern web UI with:
- **Library Browser**: Search and browse song database
- **Player Controls**: Play, pause, stop, volume, progress
- **Playlist Manager**: Queue songs, reorder, remove
- **Settings**: Configure library folders, preferences

**Technologies**: Vanilla JavaScript (can be replaced with React/Vue/Svelte)

## Message Protocol

### Commands (Frontend → Python)

```json
{
  "action": "play",
  "params": {
    "playlist_index": 0
  }
}
```

**Available Actions**:
- `play`, `pause`, `stop`, `next`, `previous`
- `seek`, `set_volume`
- `load_song`, `add_to_playlist`, `remove_from_playlist`, `clear_playlist`
- `search_songs`, `get_library`, `scan_library`, `add_folder`
- `get_state`, `get_settings`, `update_settings`

### Events (Python → Frontend)

```json
{
  "type": "event",
  "event": {
    "type": "state_changed",
    "timestamp": 1234567890.123,
    "data": {
      "playback_state": "playing",
      "current_song": {...},
      "position_ms": 12345,
      ...
    }
  }
}
```

**Event Types**:
- `state_changed`: Playback state update
- `song_finished`: Track completed
- `playback_error`: Error occurred
- `playlist_updated`: Playlist changed
- `library_scan_complete`: Library scan done
- `volume_changed`: Volume adjusted

## Development

### Prerequisites

- Rust (1.60+)
- Node.js (optional, for advanced frontend)
- Python 3.10+
- PyKaraoke dependencies (pygame, etc.)

### Setup

1. **Install Tauri CLI**:
   ```bash
   cargo install tauri-cli
   ```

2. **Build the app**:
   ```bash
   cd tauri-app
   cargo tauri dev  # Development mode
   cargo tauri build  # Production build
   ```

3. **Run Python backend standalone** (for testing):
   ```bash
   python3 pykbackend.py
   # Then send JSON commands via stdin
   ```

### Development Workflow

1. **Backend changes**: Edit `pykbackend.py`, restart Tauri app
2. **Frontend changes**: Edit files in `src/`, hot-reload enabled
3. **Rust changes**: Edit `src-tauri/src/main.rs`, rebuild with `cargo tauri dev`

## Project Structure

```
tauri-app/
├── src/                      # Frontend web app
│   ├── index.html           # Main UI
│   ├── styles.css           # Styling
│   └── app.js               # Frontend logic
├── src-tauri/               # Rust backend
│   ├── src/
│   │   └── main.rs          # Tauri application entry
│   ├── Cargo.toml           # Rust dependencies
│   ├── tauri.conf.json      # Tauri configuration
│   └── build.rs             # Build script
└── README.md                # This file
```

## Testing

### Backend API Testing

Use the provided test script:

```bash
python3 << 'EOF'
import json
import subprocess

proc = subprocess.Popen(
    ['python3', 'pykbackend.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Send command
cmd = {"action": "get_state", "params": {}}
proc.stdin.write(json.dumps(cmd) + '\n')
proc.stdin.flush()

# Read response
response = proc.stdout.readline()
print(json.loads(response))

proc.terminate()
EOF
```

### Integration Testing

1. Start Tauri app in dev mode
2. Open browser console to monitor events
3. Test playback controls, library search, etc.

## Migration from wxPython

The following wxPython components have been migrated:

| wxPython Component | New Component | Notes |
|-------------------|---------------|-------|
| `PyKaraokeWindow` | `index.html` | Main UI layout |
| `SearchResultsPanel` | Library browser | Search + results list |
| `Playlist` | Playlist section | Queue management |
| Player controls | Player controls | Play/pause/stop/etc |
| `DatabaseSetupWindow` | Settings (TBD) | Library configuration |
| Event loop | Tauri event system | State updates via events |

## Deployment

### Building for Distribution

```bash
cd tauri-app
cargo tauri build
```

This creates platform-specific installers:
- **Windows**: `.exe`, `.msi`
- **macOS**: `.app`, `.dmg`
- **Linux**: `.AppImage`, `.deb`, `.rpm`

### Bundle Contents

The bundle includes:
- Tauri executable
- Python backend script (`pykbackend.py`)
- Python dependencies (bundled with PyInstaller/similar)
- Frontend assets

## Roadmap

- [ ] Complete IPC response handling (bidirectional)
- [ ] Add folder picker dialog (native file chooser)
- [ ] Implement settings UI
- [ ] Add drag-and-drop for playlist
- [ ] Implement key/tempo change controls
- [ ] Add lyrics display panel
- [ ] Create installer packages
- [ ] Add auto-update functionality

## Contributing

See main repository documentation for contribution guidelines.

## License

LGPL-2.1-or-later (same as PyKaraoke)
