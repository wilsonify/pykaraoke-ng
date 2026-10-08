# User Guide

Install PyKaraoke-NG, set up a song library, and run karaoke at a live event.

[← Home](index.md)

---

## Quick Reference

```
┌────────────────────────────────┐
│  🔍 Search songs...           │  ← Search bar (always visible)
├────────────────────────────────┤
│  Results / Queue              │  ← Scrollable area
│  ┌──────────────────────────┐ │
│  │ Song Title — Artist      │ │
│  │ Song Title — Artist      │ │
│  └──────────────────────────┘ │
├────────────────────────────────┤
│  ▶ Now Playing               │  ← Current song + controls
│    Title — Artist             │
│    ⏮ ⏪ ▶⏸ ⏩ ⏭              │
│    ─────●──────────── 🔊      │
│         1:23 / 4:30           │
├────────────────────────────────┤
│  Queue (3 songs)              │
│  ┌──────────────────────────┐ │
│  │ 1. Song — Artist      ✕ │ │
│  │ 2. Song — Artist      ✕ │ │
│  └──────────────────────────┘ │
├────────────────────────────────┤
│  Status: Connected            │  ← Status bar (always visible)
└────────────────────────────────┘
```

The app is a **narrow sidebar** (~380 px) designed to sit beside your DJ
software. You never need to switch away from your primary application.

---

## Desktop App

The recommended way to use PyKaraoke-NG is the Tauri desktop app — a native
window with a slim sidebar UI.

### Install

**Pre-built installers** are available from [GitHub Releases](https://github.com/wilsonify/pykaraoke-ng/releases):

| Platform | Format | File |
|----------|--------|------|
| Windows | NSIS installer | `PyKaraoke NG_<version>_x64-setup.exe` |
| macOS | DMG | `PyKaraoke NG_<version>_x64.dmg` |
| Linux | deb | `pykaraoke-ng_<version>_amd64.deb` |

Alternatively serve `web/` and use the app in a browser — same page, same
engine, with folder picking via the directory file input.

### Requirements

- A sound card and speakers
- Karaoke files (CDG, KAR, or MPEG video)
- Windows 10+, macOS 12+, or Linux with WebKit2GTK
- No Python required on the target machine

---

## First Run

1. **Launch** the installed desktop app. A narrow sidebar window appears.
2. **Add your songs:** Click **Add Folder**, select your karaoke directory,
   then click **Scan Library**. Songs are indexed in a local database.
3. **Search:** Type in the search bar — results appear instantly as you type.
4. **Queue:** Press `↓` to highlight a song, then `Enter` to add it to the
   queue.
5. **Play:** Click ▶ **Play** or press `Space`. The queued song starts.

### Song Library Layout

Organize your files so CDG tracks have a matching audio file in the same folder:

```
~/Karaoke/
├── Artist Name/
│   ├── Song Title.cdg
│   ├── Song Title.mp3          ← audio companion for the .cdg
│   └── Another Song.kar
└── Another Artist/
    └── Great Song.mpg
```

**Supported formats:**

| Format | Extensions | Audio source |
|--------|-----------|-------------|
| CD+G | `.cdg` + `.mp3`/`.wav`/`.ogg` | Required separate audio file |
| MIDI Karaoke | `.kar`, `.mid` | Built-in MIDI synthesis |
| MPEG Video | `.mpg`, `.mpeg`, `.avi` | Embedded audio track |

---

## Playback Controls

Controls appear in the **Now Playing** section of the sidebar, below the
search results.

### Transport Buttons

| Button | ID | Action |
|--------|-----|--------|
| ⏮ Previous | `prev-btn` | Jump to previous song in queue |
| ⏪ Rewind | `rewind-btn` | Skip back 10 seconds (hold for continuous) |
| ▶ Play | `play-btn` | Start playback or resume from pause/stop |
| ⏸ Pause | `pause-btn` | Pause playback (press Play to resume) |
| ⏩ Fast Forward | `ff-btn` | Skip forward 10 seconds (hold for continuous) |
| ⏭ Next | `next-btn` | Skip to next song in queue |
| ⏹ Stop | `stop-btn` | Stop playback, reset position |

**How Stop works:** Stop resets the position to 0:00 and clears the player,
but keeps the current song loaded. Pressing **Play** after Stop restarts the
same song from the beginning — you don't need to re-queue it.

### Progress Slider

Drag to seek to any position in the current song. The current time and total
duration are shown next to the slider.

- **Click** to jump to a position (fires on mouse release).
- **Drag** to scrub — the time display updates as you drag.

### Volume

Drag the volume slider (0–100%). The percentage is displayed beside it.

### Settings

Click the gear icon (⚙) to open the inline settings panel:

- **Sort library by** — `filename`, `title`, or `artist`
- **CDG zoom** — `quick` (0.75×), `int` (1×), `full` (1.5×), `soft` (2×)
- **Look inside .zip files** — scan archives for karaoke files
- **Hide songs without artist** — drop entries with no artist metadata

---

## Search

The search bar at the top of the sidebar is the primary way to find songs.

- **Incremental:** Results update as you type — no search button needed.
- **Debounced:** 200 ms delay prevents excessive re-queries.
- **Empty query:** Clears the results list.
- **Navigate:** Use `↑` / `↓` to move through results.

### Add to Queue

- **Keyboard:** Highlight a result with `↑`/`↓`, press `Enter`.
- **Mouse:** Double-click a result.
- **Drag:** Drag a result onto the queue area beneath.

---

## Queue Management

The queue shows upcoming songs in order. The currently playing song is
highlighted.

| Action | Method |
|--------|--------|
| **Remove** | Click the ✕ button on a queue item, or select and press `Delete` |
| **Reorder** | Drag-and-drop items, or `Ctrl+↑` / `Ctrl+↓` |
| **Clear all** | Click the **Clear Queue** button |

The queue **auto-advances** — when a song finishes, the next queued song
starts automatically.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` or `Ctrl+K` | Focus search bar |
| `↑` / `↓` | Navigate search results or queue |
| `Enter` | Add selected song to queue |
| `Esc` | Clear search results |
| `Space` | Play / Pause |
| `Ctrl+→` | Skip to next song |
| `Delete` | Remove selected item from queue |
| `Ctrl+↑` / `Ctrl+↓` | Reorder queue item |

---

## Status Bar

The bottom of the window shows:

- **Engine status** — `PyScript: ready` once the WebAssembly engine and
  its wheel have loaded; otherwise a connecting/error message.
- **Status messages** — brief feedback about actions (scan complete,
  errors).

---

## Troubleshooting

| Problem | Fix |
|---------|------|
| Engine never finishes loading | The first launch downloads/builds `_assets/` and `_wheel/` — run `scripts/build-web.py` once, or wait for network |
| No sound | Check system volume and OS output device; verify `.mp3` sits next to `.cdg` |
| Video stuttering | Close other apps; use a smaller window |
| Songs missing after scan | Check extensions (`.cdg`, `.kar`, `.mpg`) and re-scan |
| Stop button restarts same song | This is by design — Stop keeps the song loaded |
| FF/Rewind doesn't change audio | Some codecs don't honour seek in the middle of a decode; position display still updates |
| Folder picker doesn't appear | Only the desktop app has it — in a browser, use **Add Folder** with the directory file input |
| Settings don't persist | Library and settings live in browser storage; clearing site data resets them |
| Installer fails | Build from source, or try the other installer format from Releases |

---

## Where to Get Karaoke Files

Respect copyright laws in your jurisdiction.

- **Create your own** — CDG creator software + royalty-free music
- **Public domain** — Classical and traditional songs
- **Licensed services** — Some vendors sell downloadable CDG packs
- **MIDI** — Many `.kar` files are freely available online
