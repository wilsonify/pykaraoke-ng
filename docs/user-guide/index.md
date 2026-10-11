# User Guide

Install PyKaraoke-NG, set up a song library, and run karaoke at a live event.

[← Home](../index.md)

---

## Quick Reference

```
┌────────────────────────────────┐
│  🎤 PyKaraoke NG  Add folder ⚙ │  ← Header (always visible)
├────────────────────────────────┤
│  Library            272 songs  │  ← ▸ Manage library: rescan, replace,
│                                │     export, import, folder list
│  🔍 Search title or artist…    │  ← Search bar ( / focuses it )
│  Format ☑ CDG ☑ KAR/MID ☑ MPG  │  ← Combine format filters
│  Songs                272      │  ← Browsable list, or your search results
│  ┌──────────────────────────┐  │
│  │ CDG Song — Artist ▶ ➕    │  │  ← ▶ play now, ➕ queue
│  │ KAR Song — Artist ▶ ➕    │  │
│  └──────────────────────────┘  │
├────────────────────────────────┤
│  Now Playing      ● Playing    │  ← State: Nothing loaded / Playing /
│    Title — Artist              │     Paused / Playback failed
│    ⏮ ⏪ ⏸ ⏹ ⏩ ⏭                │  ← ▶/⏸ toggle, stop, prev, next
│    ─────●──────────── 🔊 75%   │
│         1:23 / 4:30            │
├────────────────────────────────┤
│  Queue  3 songs       Clear    │
│  Up next: Song — Artist        │
│  ┌──────────────────────────┐  │
│  │ 1 CDG Song — Artist  ▶ ✕ │  │  ← ▶ play now, ✕ remove
│  │ 2 KAR Song — Artist  ▶ ✕ │  │
│  └──────────────────────────┘  │
├────────────────────────────────┤
│  Added Song — Undo ✕           │  ← Notice bar (only when there is news)
│  Ready — 272 songs      Ready  │  ← Status bar + engine state
└────────────────────────────────┘
```

The app is a **narrow sidebar** (380 px by default, usable from 300 px to
450 px) designed to sit beside your DJ software. You never need to switch away
from your primary application.

The panel stacks top to bottom: **library** (actions, search, format filters,
song list), **Now Playing** (stage, transport, volume) and the **queue**. The
whole column scrolls, and a notice bar appears just above the status bar for
scan results, queue changes, and errors you can act on.

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
2. **Add your songs:** Click **Add folder** and choose the directory that
   holds your karaoke files. It is scanned straight away, and the songs are
   indexed in a local database so the next launch already knows them.
3. **Browse or search:** With the search box empty the list shows the first
   songs of the library — type to narrow it, or press `/` to jump to the
   search box from anywhere.
4. **Queue:** Press `↓` to highlight a song, then `Enter` to add it to the
   queue — or just click a row.
5. **Play:** Double-click a row, press its ▶ button, or press `Space` for the
   loaded song. **Now Playing** shows the title, progress, and transport
   controls, and the queue below shows what comes next.

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

The **Library** panel (top of the sidebar, under the header) shows how many
songs you have and holds the scan and maintenance actions behind **Manage
library**:

| Action | What it does |
|--------|--------------|
| **Rescan library** | Re-reads the configured folders and *adds* their songs (existing songs are kept). Use it after adding files to a folder you have already picked. |
| **Replace library** | Clears the current song list, then re-scans the configured folders — use this after *moving* your collection so no ghost entries from the old location remain. Because it discards the current list it asks twice: the button becomes **Confirm replace** and the hint spells out what will happen, and the request expires after six seconds if you do not confirm. In the browser, files are re-read from the already-picked folder handles. |
| **Export** | Downloads the whole library (songs, pairing, folders, settings — not the media files) as `pykaraoke-library.json`. |
| **Import** | Loads a previously exported JSON file, replacing the current library after validation. A corrupt or wrong-version file is rejected cleanly and the existing library stays intact. |
| **Add folder** | In the header — picks another folder to add to the library. |

The folders a rescan will re-read are listed under the buttons, so **Rescan
library** is never a mystery. A scan in progress says **Scanning library…** in
the status bar and disables the library buttons until it finishes.

**Relocating a library** (moved to a new drive or folder): move the files on
disk, pick the new folder with **Add folder**, then click **Replace library**
and confirm. Settings (volume, naming convention, patterns) are preserved.

**Sharing with another machine**: click **Export** on the source machine,
copy `pykaraoke-library.json` across, and click **Import** on the target —
the song list, metadata, folders, and settings arrive intact (the media
files themselves must be reachable at the imported paths).

### Scan Results

After a scan, a summary line under the library header says what happened, in
plain language:

- `Library scan complete — 272 songs` in the status bar when everything was
  usable.
- `Scan finished — skipped 2,382 files that are not karaoke and 3 files you
  filtered out` when files were simply not karaoke (nothing is broken).
- `Scan finished with 1 problem: 1 damaged ZIP archive` when a file genuinely
  could not be used.

A **Scan details (N)** chip next to the summary expands a grouped list of the
exact files the scan could not use — grouped by reason (not karaoke, filtered
out, damaged ZIP archive, unsupported compression, could not be read, name
could not be parsed). The details stay available until you press **Clear scan
details** or run another scan, so dismissing the notification never loses
them. Skipped files are never playable and are never presented as errors in
the song list.

---

## Playback Controls

Controls appear in the **Now Playing** section of the sidebar, below the
search results.

### Playback State

A chip beside **Now Playing** always says what the player is doing:

| Chip | Meaning |
|------|---------|
| **Nothing loaded** | No song is loaded — pick one from the list. |
| **Playing** | Audio (or MIDI/video) is running; ▶ shows ⏸. |
| **Paused** | Playback is held; ▶ resumes from the same position. |
| **Playback failed** | The song could not start. The notice bar explains why in plain language and offers **Retry**. |

The current title and file name sit under the stage. A control that cannot do
anything yet is **disabled** rather than failing when clicked — for example
**Next** is disabled while the queue is empty, and the seek bar is disabled
while nothing is loaded.

### Transport Buttons

| Button | Action |
|--------|--------|
| ⏮ Previous | Restart the current song, or play the previous one when it has just started (`Ctrl+↑`) |
| ⏪ Rewind | Skip back 5 seconds |
| ▶ / ⏸ Play | Start playback, resume from pause, or retry a failed song (`Space`) |
| ⏹ Stop | Stop playback and unload the current song |
| ⏩ Fast Forward | Skip forward 5 seconds |
| ⏭ Next | Play the next queued song (`Ctrl+→`) |

**How Stop works:** Stop halts playback, resets the position to 0:00, and
unloads the current song. To play it again, pick it from the list or the queue.

### Progress Slider

Drag or click the slider to seek to any position in the current song. The
current time and total duration are shown next to it, and both follow the
slider while you scrub. Seeking stays disabled until a song is loaded.

### Volume

Drag the volume slider (0–100%). The percentage is displayed beside it.

### Settings

Click the gear icon (⚙) — or press `F1` — to open the inline settings panel.
Close it with the ✕ button, `Esc`, or the gear again. Settings are grouped so
the power-user options stay out of the way of the main workflow:

**Library and scanning**

- **Sort songs by** — `File name`, `Title`, or `Artist`. Applies immediately.
- **Search inside ZIP archives** — list karaoke files inside `.zip` files.
- **Hide songs without an artist** — drop entries with no artist metadata.

**Song names**

- **Filename format** — which naming convention to read (`Artist - Title`,
  `Disc Track - Artist - Title`, …).
- **Extract title and artist from filenames** — read the artist and title out
  of the file name instead of trusting the file's own metadata.

**Playback and display**

- **CD+G zoom** — `quick` (0.75×), `Normal` (1×), `Large` (1.5×), `Full` (2×).
  Applies to the stage immediately.

**Advanced file filters** — *include* only files matching your patterns, or
*exclude* files with a pattern such as `*(vocal)*`. An empty include list
allows every file; excludes always win.

**Keyboard shortcuts** — the full list of bindings, shown in the panel.

Settings tagged **rescan** only take effect at the next scan. Changing one
shows a note with a **Rescan library now** button, so you can apply it without
hunting for the library actions. Volume, CD+G zoom and sort order apply
immediately; everything that changes which songs are in the library, or how
they are named, waits for the rescan.

---

## Search and Browsing

The search bar in the **Library** panel is the primary way to find songs, but
you do not have to know what you are looking for:

- **Empty search box:** the list shows the first songs of your library, under
  the heading **All songs**, with a count. With more than 300 songs it shows
  the first 300 with a hint to type to narrow the rest.
- **Incremental:** results appear as you type — no search button needed.
- **Debounced:** a short delay (150 ms) prevents excessive re-queries; title,
  artist, and file name all match.
- **Counted:** the heading changes to **Results** and the count tells you how
  many songs matched (and how many are shown).
- **Navigate:** use `↑` / `↓` to move through the list; the highlighted row
  gets an accent border and a ▸ marker, `Enter` queues it.
- **Clear:** press `Esc` or clear the box to go back to browsing.

### Format Filters

Four checkboxes sit under the search box: **CDG**, **KAR/MID**, **MPG**, and
**LRC**. All start checked; unchecking one hides that kind of song from the
list. The filters apply to browsing and searching alike, and the app tells you
when they are hiding your matches (see below).

### Empty States

The list always explains an empty view instead of going blank:

| What you see | What it means |
|--------------|---------------|
| **No songs yet** with an **Add folder** button | Nothing has been scanned. Pick the folder that holds your karaoke files. |
| **No songs match “…”** with a **Clear search** button | The search found nothing — check the spelling, use fewer words, or search the artist instead. |
| **N match the search but not the format filters** with a **Show all formats** button | Your search did match songs, but the format checkboxes hide them. |

### Song Rows

Each row shows the format badge, the title, and the file name (plus an **ELRC**
badge when word-level lyric timing is available). A marker on the right tells
you where the song already is: **queued**, **queued ×2** when you have added it
twice, or **playing** while it is on the stage.

### Add to Queue

- **Keyboard:** highlight a row with `↑`/`↓`, press `Enter`.
- **Click:** click a row to add it to the queue (the row also selects).
- **Buttons:** each row has ▶ **Play … now** and ➕ **Add … to the queue**,
  both with accessible labels.
- **Double-click:** plays that song immediately.
- **Search box:** picking a suggestion from the search box's autocomplete adds
  that song to the queue.

---

## Queue Management

The queue lists what is coming up, in order, with a line telling you what is
**Up next**. A song leaves the queue when it starts playing, so the queue is
always the waiting list — nothing plays twice by accident.

| Action | Method |
|--------|--------|
| **Play one now** | Click the ▶ button on the row, or double-click it. The song leaves the queue and starts. |
| **Remove** | Click the ✕ button on the row, or select the row and press `Delete` |
| **Reorder** | Select a row, then `Alt+↑` / `Alt+↓` |
| **Select** | Click a row (or `↑`/`↓` once a row is selected). `Esc` leaves the queue and gives the arrow keys back to the song list. |
| **Clear all** | Click **Clear** — every queued song goes at once and a **Undo** action restores them |

Adding a song that is already queued is allowed: it is appended again, the
notice says so, and the row shows **queued ×2** so a double request is visible
instead of silently ignored.

The queue **auto-advances** — when a song finishes, the next queued song
starts automatically. When the last song ends the status bar says so and the
stage is unloaded. Removing a song also offers **Undo** in the notice bar.

---

## Keyboard Shortcuts

The same list lives in **Settings → Keyboard shortcuts**, so it is always one
click away.

| Key | Action |
|-----|--------|
| `/` or `Ctrl+K` | Focus the search box (works while typing elsewhere too) |
| `↑` / `↓` | Move through the song list — or the queue, while a queue row is selected |
| `Enter` | Add the highlighted song to the queue |
| `Space` | Play or pause |
| `Ctrl+→` or `Ctrl+↓` | Play the next queued song |
| `Ctrl+↑` | Restart the current song, or play the previous one |
| `Delete` | Remove the selected queue song |
| `Alt+↑` / `Alt+↓` | Move the selected queue song earlier or later |
| `Esc` | Clear the search box, leave the queue, or close settings |
| `F1` | Open settings |

Shortcuts never fire while you are typing in a text box or a select control,
except `/` and `Ctrl+K`, which always bring you to the search box.

---

## Status Bar and Notices

The bottom of the window has two parts:

- **Status message** — what the app is doing right now, in plain words:
  `Starting…`, `Scanning library…`, `Library scan complete — 272 songs`,
  `Ready — 272 songs in the library`, `Stopped — pick a song to sing`, or
  `Playback error — …` when something went wrong.
- **Engine chip** — `Starting…`, `Ready`, or `Engine unavailable` once the
  built-in karaoke engine has loaded. Hover it for the engine details; no
  runtime jargon is shown in the label.

Just above the status bar a **notice bar** appears for things you may want to
act on or undo — `Added Song — Artist`, `Removed … from the queue`, `Cleared 4
queued songs`, `Library exported — …`, `Library imported — 272 songs`, or a
scan summary. Notices never block the player: each one has an optional action
(**Undo**, **Retry**, **See details**) and a ✕ to dismiss it, and the scan
details stay reachable from the library panel afterwards.

---

## Troubleshooting

| Problem | Fix |
|---------|------|
| Engine never finishes loading | The first launch downloads/builds `_assets/` and `_wheel/` — run `src/scripts/build-web.py` once, or wait for network |
| No sound | Check system volume and OS output device; verify `.mp3` sits next to `.cdg` |
| Video stuttering | Close other apps; use a smaller window |
| Songs missing after scan | Check extensions (`.cdg`, `.kar`, `.mpg`) and re-scan. Open **Scan details** to see the exact files the scan could not use and why |
| A file inside a `.zip` is listed but will not play | Zipped songs are listed, but audio cannot yet be read out of the archive — extract the song and its `.mp3` next to it |
| Playback failed — no audio file next to it | A `.cdg`/`.lrc` needs an `.mp3`, `.ogg`, or `.wav` with the same name in the same folder; add one and press **Retry** |
| Song won't resume after Stop | Stop unloads the song — pick it again from the song list or the queue |
| FF/Rewind doesn't change audio | Some codecs don't honour seek in the middle of a decode; position display still updates |
| Folder picker doesn't appear | Only the desktop app has it — in a browser, use **Add folder** with the directory file input |
| Settings don't persist | Library and settings live in browser storage; clearing site data resets them |
| Installer fails | Build from source, or try the other installer format from Releases |

---

## Where to Get Karaoke Files

Respect copyright laws in your jurisdiction.

- **Create your own** — CDG creator software + royalty-free music
- **Public domain** — Classical and traditional songs
- **Licensed services** — Some vendors sell downloadable CDG packs
- **MIDI** — Many `.kar` files are freely available online
