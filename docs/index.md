# 🎤 PyKaraoke-NG

A free, open-source karaoke player for Linux, Windows, and macOS

---

**[User Guide](users.md)** | **[Developer Guide](developers.md)** | **[Admin Guide](administrators.md)** | **[GitHub](https://github.com/wilsonify/pykaraoke-ng)**

---

## Features

| 🎵 Multiple Formats | 📚 Song Database | 🖥️ Cross-Platform | 🚀 Desktop Apps |
|---------------------|------------------|-------------------|-----------------|
| CDG+MP3, MIDI/KAR, MPEG video | Automatically catalog and search | Linux, Windows, macOS | Electron & Tauri |

## Quick Start

```bash
# Install with pip
pip install pykaraoke-ng

# Or using uv (recommended)
uv pip install pykaraoke-ng

# Run the GUI
pykaraoke

# Play a specific file
pycdg song.cdg
pykar song.kar
pympg song.mpg
```

## Supported Formats

| Format | Extension | Player | Description |
|--------|-----------|--------|-------------|
| CD+G | .cdg + .mp3 | pycdg | Standard karaoke format with graphics |
| MIDI Karaoke | .kar, .mid | pykar | MIDI files with embedded lyrics |
| MPEG Video | .mpg, .mpeg, .avi | pympg | Video karaoke files |

## Documentation

- **[User Guide](users.md)** - Install and use PyKaraoke-NG
- **[Developer Guide](developers.md)** - Set up development environment and contribute
- **[Admin Guide](administrators.md)** - Deploy with Docker, Kubernetes, Electron, or Tauri

## License

PyKaraoke-NG is licensed under [LGPL-2.1-or-later](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)
