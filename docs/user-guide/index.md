# User Guide

Install PyKaraoke-NG, set up a song library, and run karaoke at a live event.

[← Home](../index.md)

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

Alternatively serve `src/web/` and use the app in a browser — same page, same
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
    ├── Great Song.mpg
    ├── Great Song.lrc
    ├── Great Song.elrc         ← optional word timing for the .lrc
    └── Great Song.mp3          ← audio companion for the .lrc
```

**Supported formats:**

| Format | Extensions | Audio source |
|--------|-----------|-------------|
| CD+G | `.cdg` + `.mp3`/`.wav`/`.ogg` | Required separate audio file |
| MIDI Karaoke | `.kar`, `.mid` | Built-in MIDI synthesis |
| LRC lyrics | `.lrc`, `.lcr` + audio | Required separate audio file; optional `.elrc` word timing, duet part tags |
| MPEG Video | `.mpg`, `.mpeg`, `.avi` | Embedded audio track |

### Duet Songs

An LRC file can say which singer performs each line. The part tag goes
straight after the timestamp and uses generic part ids (never gendered):
`a` and `b` for the two singers, `ab` for a line they sing together.

```lrc
[pa:Alice]                ← optional singer names
[pb:Bob]

[00:01.00][a]I will sing the first line
[00:05.00][b]Then I will answer back
[00:09.00][ab]Together we hold the note
[00:13.00]An untagged line stays solo
```

- Tagged lines are coloured by singer — blue for **A**, green for **B**,
  violet for a **shared** line — with a small chip in front naming the
  singer (`Alice`, `Bob`, `Alice + Bob`, or `A`, `B`, `A+B` when the song
  does not name them).
- Songs without `[pa:]`/`[pb:]` or line tags behave exactly as before:
  solo lyrics keep their plain look and payload.
- Word-level tags (`<mm:ss.xx>` inside a line) and companion `.elrc`
  timing keep the line's part.
- `[ba]` is accepted as a synonym of `[ab]`.
- MIDI/KAR lyrics carry no duet tags: that format has no way to express
  them, so the parts stay unexposed.

---

## Library Management

The **Library** panel (top of the sidebar, under the header) holds the scan
and maintenance actions:

| Action | What it does |
|--------|--------------|
| **Rescan folders** | Re-reads the configured folders and *adds* their songs (existing songs are kept). |
| **Replace library** | Clears the current song list, then re-scans the configured folders — use this after *moving* your collection so no ghost entries from the old location remain. In the browser, files are re-read from the already-picked folder handles. |
| **Export** | Downloads the whole library (songs, pairing, folders, settings — not the media files) as `pykaraoke-library.json`. |
| **Import** | Loads a previously exported JSON file, replacing the current library after validation. A corrupt or wrong-version file is rejected cleanly and the existing library stays intact. |

**Relocating a library** (moved to a new drive or folder): move the files on
disk, pick the new folder with **＋ Folder**, then click **Replace library**.
Settings (volume, naming convention, patterns) are preserved.

**Sharing with another machine**: click **Export** on the source machine,
copy `pykaraoke-library.json` across, and click **Import** on the target —
the song list, metadata, folders, and settings arrive intact (the media
files themselves must be reachable at the imported paths).

A scan summary line under the library header reports anything the scan could
not use (unsupported files, pattern-filtered files, corrupt archives, parse
failures), with a **Dismiss** control to clear it.

---

## Playback Controls

Controls appear in the **Now Playing** section of the sidebar, below the
search results.

### Transport Buttons

| Button | ID | Action |
|--------|-----|--------|
| ⏮ Previous | `prev-btn` | Jump to previous song in queue |
| ⏪ Rewind | `rewind-btn` | Skip back 5 seconds |
| ▶ Play | `play-btn` | Start playback or resume from pause/stop |
| ⏸ Pause | `pause-btn` | Pause playback (press Play to resume) |
| ⏩ Fast Forward | `ff-btn` | Skip forward 5 seconds |
| ⏭ Next | `next-btn` | Skip to next song in queue |
| ⏹ Stop | `stop-btn` | Stop playback, reset position |

**How Stop works:** Stop halts playback, resets the position to 0:00, and
unloads the current song. To play it again, select it from the results or add
it to the queue.

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
- **Derive song info from filename** — read artist/title from the filename

---

## Search

The search bar at the top of the sidebar is the primary way to find songs.

- **Incremental:** Results update as you type — no search button needed.
- **Debounced:** a short delay (150 ms) prevents excessive re-queries.
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
| Engine never finishes loading | The first launch downloads/builds `_assets/` and `_wheel/` — run `src/scripts/build-web.py` once, or wait for network |
| No sound | Check system volume and OS output device; verify `.mp3` sits next to `.cdg` |
| Video stuttering | Close other apps; use a smaller window |
| Songs missing after scan | Check extensions (`.cdg`, `.kar`, `.mpg`) and re-scan |
| Song won't resume after Stop | Stop unloads the song — pick it again from the results or queue |
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
