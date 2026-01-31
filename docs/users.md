# 👤 User Guide

Everything you need to host your own karaoke night.

[← Back to Home](index.md)

---

## Installation

### Prerequisites

- Python 3.10 or higher
- A sound card and speakers
- Karaoke files (CDG, KAR, or MPEG format)

### Install with pip

```bash
# Standard installation
pip install pykaraoke-ng

# Or using uv (faster)
uv pip install pykaraoke-ng
```

### Install from Source

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
pip install -e .
```

### System Dependencies

PyKaraoke-NG requires pygame and SDL. On most systems, these install automatically. If you have issues:

```bash
# Debian/Ubuntu
sudo apt install python3-pygame libsdl2-mixer-2.0-0

# Fedora
sudo dnf install python3-pygame SDL2_mixer

# macOS (with Homebrew)
brew install sdl2 sdl2_mixer
```

---

## Getting Started

### Launch the GUI

```bash
pykaraoke
```

This opens the song browser where you can:
- Browse and search your song library
- Create playlists and queues
- Configure audio/video settings

### Play Files Directly

```bash
# Play a CDG file (requires matching .mp3)
pycdg /path/to/song.cdg

# Play a MIDI/KAR file
pykar /path/to/song.kar

# Play a video karaoke file
pympg /path/to/song.mpg
```

### Mini Player

For resource-limited systems:

```bash
pykaraoke_mini
```

### Desktop Apps

PyKaraoke-NG also provides standalone desktop applications that bundle everything needed:

- **Electron App**: Cross-platform desktop application (see [Admin Guide](administrators.md#electron-desktop-deployment))
- **Tauri App**: Lightweight native desktop application (see [Admin Guide](administrators.md#tauri-desktop-deployment))

---

## Setting Up Your Song Library

### Organize Your Files

For best results, organize songs like this:

```
~/Karaoke/
├── Artist Name/
│   ├── Song Title.cdg
│   ├── Song Title.mp3
│   └── Another Song.kar
└── Another Artist/
    └── Great Song.mpg
```

> **Tip:** CDG files require a matching audio file (MP3 or OGG) with the same base name in the same folder.

### Scan Your Library

1. Open PyKaraoke
2. Go to **File → Add Songs Folder**
3. Select your karaoke folder
4. Wait for the scan to complete

Songs are indexed in a local database for fast searching.

---

## Playing Karaoke

### Keyboard Controls

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `Escape` | Stop / Exit fullscreen |
| `F` | Toggle fullscreen |
| `+` / `-` | Volume up / down |
| `Left` / `Right` | Seek backward / forward |
| `N` | Next song in queue |

### Using the Queue

1. Search for a song
2. Right-click and select **Add to Queue**
3. Repeat for more songs
4. Click **Play Queue** to start

---

## Where to Get Karaoke Files

> **Note:** Respect copyright laws in your jurisdiction. Many karaoke files are copyrighted.

### Legal Sources

- **Create your own** - Use CDG creator software with royalty-free music
- **Public domain** - Classical music and traditional songs
- **Licensed services** - Some services sell downloadable CDG files
- **MIDI files** - Many .kar files are available for free online

---

## Troubleshooting

### No Sound

- Check your system volume and speaker connections
- Verify the audio file exists alongside the CDG file
- Try a different audio output in Settings

### Video Stuttering

- Close other applications
- Try a smaller window size
- Use `pykaraoke_mini` for better performance

### Songs Not Found

- Rescan your library: **File → Rescan Songs**
- Check file permissions
- Ensure files have correct extensions (.cdg, .kar, .mpg)
