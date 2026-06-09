# User Guide

Install PyKaraoke-NG, set up a song library, and run karaoke at a live event.

[← Home](index.md)

---

## Desktop App

The recommended way to use PyKaraoke-NG is the Tauri desktop app — a native
window with a slim sidebar UI designed to sit beside your DJ software.

### Install

**Pre-built installers** are available from [GitHub Releases](https://github.com/wilsonify/pykaraoke-ng/releases):

| Platform | Format | File |
|----------|--------|------|
| Windows | NSIS installer | `PyKaraoke NG_<version>_x64-setup.exe` |
| macOS | DMG | `PyKaraoke NG_<version>_x64.dmg` |
| Linux | AppImage | `PyKaraoke NG_<version>_x64.AppImage` |
| Linux | deb | `pykaraoke-ng_<version>_amd64.deb` |

### Build from source

See the [Admin Guide](administrators.md#tauri-desktop-builds) for
detailed build instructions.

### Requirements

- A sound card and speakers
- Karaoke files (CDG, KAR, or MPEG)
- Windows, macOS, or Linux (no Python required on the target machine)

---

## Headless Backend (for advanced users)

The Python backend runs independently of the desktop app — useful for
scripting, automation, or Docker deployments.

### From source

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
uv sync                              # or: pip install -e .
```

### Run in stdio mode

```bash
uv run python -m pykaraoke.core.backend
```

Send a command:

```bash
echo '{"action":"get_state","params":{}}' | uv run python -m pykaraoke.core.backend
```

### Run in HTTP mode

```bash
uv run python -m pykaraoke.core.backend --http
curl http://localhost:8080/health
```

### Production artifact (standalone .exe)

The built `backend.exe` requires no Python on the target machine:

```bash
./backend.exe
echo '{"action":"get_state","params":{}}' | ./backend.exe
```

Set the `PYKARAOKE_BACKEND_EXE` environment variable to use a custom
backend with the desktop app:

```bash
export PYKARAOKE_BACKEND_EXE=/path/to/custom/backend.exe
```

---

## Set Up a Song Library

Organize files so CDG tracks have a matching `.mp3` in the same folder:

```
~/Karaoke/
├── Artist Name/
│   ├── Song Title.cdg
│   ├── Song Title.mp3
│   └── Another Song.kar
└── Another Artist/
    └── Great Song.mpg
```

Then scan:

1. Open PyKaraoke.
2. Click **Add Folder** and select the karaoke directory.
3. Click **Scan Library**. Songs are indexed in a local database.

---

## Play Songs

### Desktop app

Launch the installed desktop app. The app is a slim sidebar that stays
out of the way during a live set.

### Keyboard controls

| Key | Action |
|-----|--------|
| `/` or `Ctrl+K` | Focus search bar |
| `↑` / `↓` | Navigate results or queue |
| `Enter` | Add selected song to queue |
| `Esc` | Clear search |
| `Space` | Play / Pause |
| `Ctrl+→` | Skip to next song |
| `Delete` | Remove selected from queue |
| `Ctrl+↑` / `Ctrl+↓` | Reorder queue item |

### Queue workflow

1. Type a few letters in the search bar — results filter instantly.
2. Press `↓` to highlight a result, then `Enter` to queue it.
3. The queue auto-advances when a song ends.

The goal is to go from hearing a request to having it queued in under
3 seconds — no confirmation dialogs, no page changes.

---

## Headless Usage (CLI / scripting)

Send commands to the backend via stdin or HTTP:

```bash
# stdio
echo '{"action":"play","params":{}}' | uv run python -m pykaraoke.core.backend

# HTTP
curl -X POST http://localhost:8080/api/play
curl -X POST 'http://localhost:8080/api/playlist/add?filepath=/path/to/song.cdg'
curl http://localhost:8080/api/state
```

See [Backend Modes](backend-modes.md) for the full API reference.

---

## Troubleshooting

| Problem | Fix |
|---------|------|
| Desktop window is blank (Linux) | `WEBKIT_DISABLE_DMABUF_RENDERER=1` is set automatically |
| No sound | Check system volume; verify `.mp3` sits next to `.cdg` file |
| Video stuttering | Close other apps; try a smaller window |
| Songs not found after scan | Re-scan; check file extensions (`.cdg`, `.kar`, `.mpg`) |
| `mixer not initialized` | Plug a speaker / enable audio output before playing |
| `ModuleNotFoundError` | Run `uv sync` or `pip install -e .` |
| Backend won't start | Check `PYKARAOKE_BACKEND_EXE` points to a valid `backend.exe` |
| NSIS installer fails | Download the `.msi` instead, or build from source |

---

## Where to Get Karaoke Files

Respect copyright laws in your jurisdiction.

- **Create your own** — CDG creator software + royalty-free music.
- **Public domain** — Classical and traditional songs.
- **Licensed services** — Some vendors sell downloadable CDG packs.
- **MIDI** — Many `.kar` files are freely available online.
