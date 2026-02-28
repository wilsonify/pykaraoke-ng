# User Guide

Install PyKaraoke-NG, set up a song library, and run karaoke at a live event.

[← Home](index.md)

---

## Install

### Requirements

- Python 3.10+
- A sound card and speakers
- Karaoke files (CDG, KAR, or MPEG)

### pip

```bash
pip install pykaraoke-ng
# or
uv pip install pykaraoke-ng
```

### From source

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
pip install -e .
```

### System dependencies

pygame and SDL usually install automatically. If they don't:

```bash
# Debian / Ubuntu
sudo apt install python3-pygame libsdl2-mixer-2.0-0

# Fedora
sudo dnf install python3-pygame SDL2_mixer

# macOS
brew install sdl2 sdl2_mixer
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

### Command-line players

```bash
pycdg /path/to/song.cdg     # CD+G (needs matching .mp3)
pykar /path/to/song.kar      # MIDI / KAR
pympg /path/to/song.mpg      # video
```

### Desktop app

Launch the Tauri desktop app (see [Admin Guide](administrators.md#tauri-desktop-builds)
for install instructions). The app is a slim sidebar designed to sit beside
your DJ software.

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

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No sound | Check system volume; verify the `.mp3` sits next to the `.cdg` file |
| Video stuttering | Close other apps; try a smaller window |
| Songs not found after scan | Re-scan (**Scan Library**); check file extensions (`.cdg`, `.kar`, `.mpg`) |
| `ModuleNotFoundError` | Run `pip install -e .` or `uv sync` |

---

## Where to Get Karaoke Files

Respect copyright laws in your jurisdiction.

- **Create your own** — CDG creator software + royalty-free music.
- **Public domain** — Classical and traditional songs.
- **Licensed services** — Some vendors sell downloadable CDG packs.
- **MIDI** — Many `.kar` files are freely available online.
