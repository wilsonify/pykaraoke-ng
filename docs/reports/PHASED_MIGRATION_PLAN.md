# Migration Plan: Python to Rust-First Desktop Application

**Priority**: High risk/complexity items first (eliminate major blockers early),
followed by medium-risk items that deliver user-visible features.

---

## Phase 0 — Lay the Foundation (Weeks 1-2)

| # | Task | Risk | Effort | Dependencies | Deliverable |
|---|------|------|--------|--------------|-------------|
| 0.1 | Add typed `#[tauri::command]` functions for each action (play, pause, stop, etc.) replacing the single `send_command` dispatcher | Low | 3 days | None | `main.rs` with explicit commands; deprecate `send_command` |
| 0.2 | Add event emission from Backend (state_changed, song_finished, playlist_updated) via Tauri event system | Low | 2 days | 0.1 | `Backend.emit()` using Tauri `AppHandle`; frontend removes polling |
| 0.3 | Merge frontend UX logic into Rust backend: double-click debounce → single "enqueue" command; hold-to-seek → `seek_start`/`seek_stop` commands; search debounce → backend filters; keyboard shortcuts → backend keybinding config | Low | 3 days | 0.1 | Cleaner frontend, richer backend |
| 0.4 | Add `zip` crate to `discovery.rs`, implement real ZIP central directory parsing | Low | 2 days | None | ZIP file scanning works |
| 0.5 | Replace `mutagen` with `mp3-duration`/`lofty` crate for MP3 metadata | Low | 2 days | None | Rust reads MP3 duration, no Python needed |
| 0.6 | Remove wxPython performer prompt, implement as Tauri dialog + HTML modal | Low | 1 day | None | Eliminates wxPython dependency |

**Phase 0 outcome**: Eliminates 3 Python dependencies (mutagen, wxPython, win32api),
removes polling, event-driven IPC, cleaner command API. No user-visible changes yet
(still uses Python `pygame` for actual playback).

---

## Phase 1 — CDG Playback Engine (Weeks 3-6)

| # | Task | Risk | Effort | Dependencies | Deliverable |
|---|------|------|--------|--------------|-------------|
| 1.1 | Implement Rust CDG decoder: tile block rendering, border preset, memory preset, scroll, XOR, colour table loading | Medium | 2 weeks | None | `format/cdg.rs` has full rendering logic, pixel output |
| 1.2 | Implement CDG render-to-RGBA: convert 300×216 indexed buffer to `Vec<u8>` RGBA pixels | Low | 2 days | 1.1 | Frame data ready for Tauri IPC |
| 1.3 | Add `#[tauri::command] fn render_cdg_frame(song_id) -> Vec<u8>` that returns RGBA pixels | Low | 1 day | 1.2, 0.1 | Frontend can fetch frames |
| 1.4 | Frontend: implement CDG canvas renderer (put decoded RGBA pixels onto `<canvas>` element) | Medium | 1 week | 1.3 | CDG graphics appear in Tauri app |
| 1.5 | Integrate `rodio` for audio playback: play companion MP3/OGG synchronized with CDG frames | Medium | 2 weeks | 1.4 | CD+G songs play with audio |
| 1.6 | CDG zoom modes: implement Quick, Int, Full, Soft pixel interpolation in Rust | Medium | 1 week | 1.2 | Feature parity with Python CDG player |
| 1.7 | Port CDG test suite: ensure all instruction combinations match Python reference output | High | 1 week | 1.1-1.6 | 100% compat with Python CDG decoder |

**Phase 1 outcome**: CD+G karaoke files play in the Tauri app without Python.
This is the highest-impact user-facing feature. ~200 Python test cases for CDG format
must pass against Rust implementation.

---

## Phase 2 — KAR/MIDI Playback Engine (Weeks 5-8)

| # | Task | Risk | Effort | Dependencies | Deliverable |
|---|------|------|--------|--------------|-------------|
| 2.1 | Add `midly` crate, implement MIDI file header + track parser | Low | 3 days | None | Rust reads MIDI files |
| 2.2 | Extract KAR lyrics: parse lyric meta events (0x05), cue points (0x07), text events, build timed lyric syllables | Medium | 1 week | 2.1 | Lyric data stream available |
| 2.3 | Implement MIDI timing: tick-to-millisecond conversion, tempo map, time signature | Medium | 1 week | 2.1 | Frame-accurate playback timing |
| 2.4 | Integrate `rustysynth` (SoundFont synthesizer) for MIDI audio playback | High | 2 weeks | 2.3 | MIDI audio without Python |
| 2.5 | Frontend: render timed lyrics as DOM elements with colour sweep | Medium | 1 week | 2.2 | KAR lyrics displayed in app |
| 2.6 | Implement lyric scrolling (view-percent cursor, paragraph lead time) in Rust → send formatted lyric lines + positions to frontend | Medium | 1 week | 2.2, 2.5 | Feature parity with Python KAR player |

**Phase 2 outcome**: KAR/MIDI karaoke files play in the Tauri app without Python.
Can overlap with Phase 1 (different format, independent engine component).

---

## Phase 3 — Frontend Modernization (Weeks 7-9)

| # | Task | Risk | Effort | Dependencies | Deliverable |
|---|------|------|--------|--------------|-------------|
| 3.1 | Remove state polling entirely; backend emits `state_changed` event on every state mutation | Low | 1 day | 0.2 | Event-driven UI |
| 3.2 | Move remaining frontend business logic to Rust: keyboard shortcuts, backend health monitoring as `emit('health_check')` | Low | 3 days | 3.1 | Frontend is pure presentation |
| 3.3 | Frontend: add proper loading/error states, transitions, toast notifications | Low | 1 week | 3.1 | Polish |
| 3.4 | Replace `setInterval` polling for settings with event: backend emits `settings_changed` | Low | 1 day | 0.2 | Clean settings UX |
| 3.5 | Implement file watching via `notify` crate: auto-scan on filesystem changes, emit `library_updated` event | Medium | 1 week | None | No more "Scan Library" button needed |

**Phase 3 outcome**: Modern, responsive, event-driven frontend. Library auto-updates.
Frontend is pure DOM manipulation — zero business logic or timers.

---

## Phase 4 — MPEG Playback & Final Milestones (Weeks 9-12)

| # | Task | Risk | Effort | Dependencies | Deliverable |
|---|------|------|--------|--------------|-------------|
| 4.1 | Evaluate MPEG playback options: GStreamer Rust bindings (`gstreamer-rs`) vs bundled `ffplay` subprocess vs `ffmpeg-next` | Medium | 1 week | None | Decision document |
| 4.2 | Implement MPEG video playback via chosen approach | High | 2-3 weeks | 4.1 | MPEG files play in Tauri app |
| 4.3 | Frontend: implement video element (HTML5 `<video>` for subprocess streams or GStreamer WebKit integration) | Medium | 1 week | 4.2 | Video visible in app |
| 4.4 | Remove Python backend entry points from pyproject.toml (pycdg, pykar, pympg console_scripts are no longer needed for desktop) | Low | 1 day | 1.7, 2.6, 4.2 | Python is optional |
| 4.5 | Remove `pygame`, `numpy` from CI test runner dependencies (use Python only for compatibility reference tests) | Low | 1 day | 4.4 | Faster CI |
| 4.6 | Update CI/CD: remove Python unit test stages, keep only Python compat tests (comparison oracle) | Low | 1 day | 4.5 | CI produces application without Python |
| 4.7 | Validate: build → install → run on clean Windows VM with zero Python installed | Medium | 2 days | All above | PROOF: Python-free deployment |

**Phase 4 outcome**: Full karaoke playback (CDG, KAR, MPEG) entirely in Rust.
Desktop application installs and runs with zero Python. All Python dependencies
eliminated from runtime.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `rodio` MP3 support requires system codecs on some platforms | Medium | Medium | Bundle MP3 decoders or use OGG as fallback |
| MIDI SoundFont synthesis quality differs from pygame.midi | Medium | Medium | Ship with TimGM6mb.sf2 or FluidR3 GM SoundFont |
| CDG frame timing/ sync drifts from audio | Medium | High | Use audio clock as master, render CDG frames based on audio position |
| GStreamer Rust bindings complex to cross-compile | High | High | Fall back to bundled `ffplay` subprocess for MPEG |
| Frontend canvas performance at 25fps on low-end hardware | Low | Medium | Optimize to only redraw dirty rectangles (CDG supports this natively via tile blocks) |
| Removing frontend polling misses state transitions | Low | Low | Implement reliable event delivery with sequence numbers |

---

## Effort Summary

| Phase | Duration | Rust crates to add | Python deps eliminated | Cumulative Python-free |
|-------|----------|--------------------|----------------------|------------------------|
| Phase 0 | 2 weeks | `zip`, `mp3-duration`/`lofty` | 3 (mutagen, wxPython, win32api) | No (pygame still needed) |
| Phase 1 | 4 weeks | `rodio` | 2 (pygame.mixer, pygame.surfarray partially) | Partial (CDG no Python) |
| Phase 2 | 4 weeks | `midly`, `rustysynth` | 1 (pygame.midi) | Partial (KAR no Python) |
| Phase 3 | 3 weeks | `notify` | 0 | No change |
| Phase 4 | 4 weeks | `gstreamer-rs` or `ffmpeg-next` | 2 (pygame.movie, pygame.display) | **YES** |
| **Total** | **17 weeks** | **6-7 crates** | **8 deps eliminated** | **Python-free** |

---

## Decision Flowchart

For each Python dependency:

```
Does the desktop app need this feature?
├── NO  → REMOVE (or convert to Rust-native alternative)
└── YES →
    Is there a mature Rust crate?
    ├── YES → MIGRATE (low risk)
    └── NO →
        Is it feasible to implement in Rust?
        ├── YES → IMPLEMENT (medium risk)
        └── NO → RETAIN PYTHON (high risk — plan to replace)
```

**Results**:
- **REMOVE**: wxPython, fastapi/uvicorn, pymedia, win32api, PyInstaller, _cpuctrl
- **MIGRATE (crate exists)**: mutagen→`lofty`/`mp3-duration`, pygame.mixer→`rodio`,
  pygame.midi→`midly`+`rustysynth`, ZIP→`zip`
- **IMPLEMENT (no crate, feasible)**: CDG decoder (format is simple, well-documented),
  file watcher (`notify` crate exists — trivial)
- **RETAIN PYTHON (complex, not yet feasible)**: None — all features have a viable
  Rust replacement within 17 weeks
