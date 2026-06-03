# PyKaraoke NG - Tauri Architecture

## Overview

This directory contains the Tauri-based desktop application for PyKaraoke NG. The architecture separates the Python karaoke engine (backend) from the web-based UI (frontend), enabling cross-platform desktop deployment without wxPython dependencies.

## Architecture

```txt
┌─────────────────────────────────────────────────────────────┐
│                    Tauri Desktop Shell                      │
│  ┌────────────────────┐         ┌──────────────────────┐    │
│  │   Web Frontend     │         │   Rust Backend       │    │
│  │  (HTML/CSS/JS)     │◄───────►│   (Tauri Core)       │    │
│  │                    │  IPC    │                      │    │
│  │  • Player UI       │         │  • Process Mgmt      │    │
│  │  • Library Browser │         │  • IPC Bridge        │    │
│  │  • Playlist        │         │  • Event Routing     │    │
│  └────────────────────┘         └──────────────────────┘    │
│                                           │                 │
│                                           │ stdio/JSON      │
│                                           ▼                 │
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

2. **Install Python dependencies**:

   ```bash
   python -m pip install -e ../../..  # install pykaraoke with pygame, numpy, mutagen
   python -m pip install pyinstaller  # for production builds
   ```

3. **Development mode** (uses Python interpreter directly):

   ```bash
   npx tauri dev
   ```

   In dev mode the Rust backend searches for a Python interpreter with the
   required dependencies and runs the backend script in place.  No
   bundling is involved, so edit-test cycles are fast.

4. **Production build** (standalone, no Python required on target):

   ```bash
   npx tauri build
   ```

   The `beforeBuildCommand` (`node scripts/stage-backend.js`) compiles the
   Python backend into a standalone Windows executable via PyInstaller
   (`backend.exe`, ~12 MB).  The Tauri resource glob bundles it into the
   installer so the app runs on any Windows 10/11 machine without a
   Python interpreter.

### Development Workflow

1. **Backend changes**: Edit files in `src/pykaraoke/`, restart `npx tauri dev`
2. **Frontend changes**: Edit files in `src/`, hot-reload enabled
3. **Rust changes**: Edit `src-tauri/src/main.rs`, rebuild with `npx tauri dev`
4. **Packaging changes**: Edit `backend.spec` or `scripts/stage-backend.js`, run `npx tauri build`

## Project Structure

```txt
├── src/                      # Frontend web app
│   ├── index.html           # Main UI
│   ├── styles.css           # Styling
│   └── app.js               # Frontend logic
├── scripts/
│   └── stage-backend.js     # Build script (copies .py or runs PyInstaller)
├── backend.spec             # PyInstaller spec for standalone backend.exe
├── src-tauri/               # Rust backend
│   ├── src/
│   │   └── main.rs          # Tauri application entry + bundled exe launcher
│   ├── Cargo.toml           # Rust dependencies
│   ├── tauri.conf.json      # Tauri configuration
│   └── build.rs             # Build script (placeholder for cargo test)
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
| ------------------ | ------------- | ----- |
| `PyKaraokeWindow` | `index.html` | Main UI layout |
| `SearchResultsPanel` | Library browser | Search + results list |
| `Playlist` | Playlist section | Queue management |
| Player controls | Player controls | Play/pause/stop/etc |
| `DatabaseSetupWindow` | Settings (TBD) | Library configuration |
| Event loop | Tauri event system | State updates via events |

## Deployment

### Building for Distribution

```bash
npx tauri build
```

The build runs `scripts/stage-backend.js` which uses PyInstaller to
compile the Python backend into a standalone `backend.exe` (~12 MB),
then Tauri bundles it into platform-specific installers.

- **Windows**: `.exe` (NSIS), `.msi` (WiX)
  → `src-tauri/target/release/bundle/`

### Bundle Contents

The installer contains everything needed to run without a Python
interpreter on the target machine:

- Tauri executable (WebView2-based desktop shell, ~4 MB)
- Python backend compiled into `backend.exe` (~12 MB, includes
  pygame, numpy, mutagen, SDL2, freetype, and all pykaraoke modules)
- Frontend web assets (HTML/CSS/JS, <1 MB)
- DejaVu fonts for CDG rendering

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
