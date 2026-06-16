# Python Dependency Audit

**Date**: 2026-06-16  
**Scope**: All Python runtime dependencies of PyKaraoke NG (`src/pykaraoke/`)  
**Goal**: Eliminate Python from the runtime dependency chain of the desktop application

---

## Summary

| Category | Count | Recommendation |
|----------|-------|----------------|
| **Runtime (required)** | 3 | 2 replaceable (`numpy`, `mutagen`), 1 complex (`pygame`) |
| **Runtime (optional)** | 4 | All removable (HTTP server, wxPython, pymedia, win32api) |
| **Build-time** | 3 | All removable by using `cargo build` instead |
| **C extensions** | 2 | 1 replaceable (`_pycdgAux` → Rust), 1 hardware-specific (`_cpuctrl` → remove) |
| **Total unique** | 10 | 8 removable, 2 complex replacements |

---

## 1. Runtime Dependencies (Required)

### 1.1 `pygame >= 2.5.0`

**Why it exists**:
- **Audio playback** (`pygame.mixer`, `pygame.mixer.music`) — CD+G companion MP3/OGG, MIDI
- **Video display** (`pygame.display`) — window creation, surface blitting, fullscreen toggle
- **Video playback** (`pygame.movie` — deprecated, `pygame.mpegvideo`) — MPEG/AVI
- **MIDI playback** (`pygame.midi`) — KAR/MIDI song playback
- **Font rendering** (`pygame.font`) — on-screen lyrics, karaoke text display
- **Event loop** (`pygame.event`) — keyboard/joystick event handling
- **CDG pixel rendering** (`pygame.surfarray.blit_array`) — blitting decoded CDG frames to screen
- **CDG color operations** (`pygame.Color`, `pygame.Surface`) — colour table management

**Files that import it**:
- `core/manager.py` — `pygame.init()`, display setup, event loop, font loading, CPU control
- `core/player.py` — `pygame.event`, `pygame.key`, `pygame.joystick`, `pygame.font`
- `players/cdg.py` — `pygame.display`, `pygame.surfarray`, `pygame.mixer.music`, `pygame.transform`
- `players/cdg_aux.py` — `pygame.surfarray` (via numpy)
- `players/kar.py` — `pygame.midi`, `pygame.font`, `pygame.event`
- `players/mpg.py` — `pygame.movie` (deprecated) or `pygame.mpegvideo`

**Lines of code depending on pygame**: ~3,000+ lines across 6 files

**Rust replacement feasibility**:
- **Audio output**: **Feasible** — `rodio` (pure Rust, WAV/MP3/OGG/Vorbis/FLAC) or `cpal` (lower-level)
  - Effort: **Medium** (2-3 weeks for basic playback, no MIDI synth)
  - MIDI synthesis would require a SoundFont synthesizer (`rustysynth`, `syntex`) — **High** effort
- **Display**: **Not applicable** — Tauri provides the window via WebView, not Rust rendering
  - CDG pixel data → Tauri command → `<canvas>` in frontend
- **Video playback**: **Complex** — `gstreamer-rs` (bindings) or bundled `ffplay`
  - Effort: **High** (4-6 weeks for reliable cross-platform MPEG playback)
- **Font rendering**: **Not applicable** — handled by the frontend's CSS/Canvas text rendering
- **Event loop**: **Not applicable** — Tauri event system replaces pygame event loop
- **Joystick/GP2X**: **Removable** — GP2X target is obsolete

**Estimate**: 6-10 weeks for full pygame replacement
**Verdict**: **Migrate** — phased approach:
  1. Phase 1: `rodio` for audio (playback-only, no MIDI synth)
  2. Phase 2: CDG pixel pipeline (Rust decoder → frontend canvas)
  3. Phase 3: MIDI/KAR with external SoundFont or embedded synthesizer
  4. Phase 4: MPEG via GStreamer or external player

---

### 1.2 `numpy >= 1.24.0`

**Why it exists**:
- **CDG pixel array operations** in `cdg_aux.py`:
  - `numpy.fromstring` / `numpy.frombuffer` — convert CDG raw data to arrays
  - `numpy.reshape` — reshape 1D byte arrays to 2D pixel buffers
  - `numpy.putmask` — apply tile block XOR operations
  - `numpy.choose` — colour table lookups
- The C extension `_pycdgAux` replaces numpy with SDL-based operations (faster)

**Files that import it**:
- `players/cdg_aux.py` — all CDG frame decoding operations

**Lines of code depending on numpy**: ~150 lines in `cdg_aux.py` (the Python fallback; the C
extension `_pycdgAux.c` replaces this for performance)

**Rust replacement feasibility**:
- **Pixel array operations**: **Trivial** — CDG is 300×216×1 byte = 64,800 bytes. Simple
  `Vec<u8>` operations with `chunks()`, `iter()`, and indexing are entirely sufficient.
- **Colour table lookups**: **Trivial** — 16 colours × 3 bytes, simple lookup table
- **XOR operations**: **Trivial** — bitwise XOR on byte slices

**Estimate**: 1 week to implement in Rust (part of CDG decoder)
**Verdict**: **Migrate** — numpy is only needed for the Python CDG fallback. The Rust CDG
decoder will use native `Vec<u8>` operations, making numpy unnecessary.

---

### 1.3 `mutagen >= 1.47.0`

**Why it exists**:
- **MP3 metadata** in `cdg.py`: `getMp3AudioProperties()` reads sample rate, channels,
  length (in seconds), and bitrate from .mp3 files paired with .cdg files

**Files that import it**:
- `players/cdg.py` — `getMp3AudioProperties()` (fallback: `pygame.mixer.Sound.get_length()`)

**Lines of code depending on mutagen**: ~20 lines (one function, guarded by try/except)

**Rust replacement feasibility**:
- **MP3 header parsing**: **Low effort** — the `mp3-duration` crate reads MP3 duration
  from frame headers. For more complete metadata, `id3` (pure Rust ID3v2 tag reader)
  or `lofty` (comprehensive audio metadata, supports MP4/FLAC/OGG too).
- **File format detection**: Already handled by extension checking in `song.rs`

**Estimate**: 2-3 days to implement with `mp3-duration` or `lofty` crate
**Verdict**: **Migrate** — straightforward, well-supported Rust crates exist

---

## 2. Runtime Dependencies (Optional)

### 2.1 `fastapi >= 0.104.0` + `uvicorn >= 0.24.0`

**Why it exists**:
- **HTTP API server** in `core/backend.py`: provides a FastAPI-based REST API for
  remote control of the karaoke backend (search, play, queue management, settings)

**Files that import it**:
- `core/backend.py` — `create_http_server()` function (gated by `try/except ImportError`)

**Lines of code depending on fastapi/uvicorn**: ~50 lines

**Rust replacement feasibility**:
- **Not needed for desktop app** — the desktop application uses Tauri IPC, not HTTP
- If HTTP API is desired: `actix-web` or `axum` (both mature Rust HTTP frameworks)

**Estimate**: N/A for desktop; 1-2 weeks if HTTP API is needed
**Verdict**: **Remove** (desktop app doesn't need HTTP API)

---

### 2.2 `wxPython` (wx)

**Why it exists**:
- **Performer prompt dialog** (`core/performer_prompt.py`): `wx.Dialog` asking for a
  performer's name before loading a song
- **Home directory resolution** (`core/database.py`): `wx.GetHomeDir()` fallback

**Files that import it**:
- `core/performer_prompt.py` — `PerformerPrompt` class (wx.Dialog)
- `core/database.py` — `wx.GetHomeDir()` (guarded)

**Lines of code depending on wxPython**: ~90 lines (performer_prompt.py)

**Rust replacement feasibility**:
- **Performer prompt**: **Trivial** — use Tauri's `dialog` plugin or a simple HTML modal
- **Home directory**: **Trivial** — `dirs` crate (already a dependency) provides `data_dir()`

**Estimate**: 1 day
**Verdict**: **Remove** — replace with Tauri dialog + HTML modal

---

### 2.3 `pymedia` (optional)

**Why it exists**:
- **Frame dumping** in `core/player.py`: `setup_dump()` / `do_frame_dump()` for encoding
  CDG frames to MPEG2 video

**Files that import it**:
- `core/player.py` — `import pymedia` inside dump methods (guarded)

**Lines of code depending on pymedia**: ~30 lines

**Rust replacement feasibility**:
- Not needed — frame dumping is a niche development feature, not a user-facing requirement
- If needed: `rav1e` (AV1 encoder) or `ffmpeg-next` (FFmpeg bindings)

**Estimate**: N/A
**Verdict**: **Remove** — feature not required for desktop app

---

### 2.4 `win32api` (optional)

**Why it exists**:
- **Windows temp directory** resolution in `core/database.py`

**Files that import it**:
- `core/database.py` — `get_temp_directory()` (guarded, falls back to `os.environ`)

**Lines of code depending on win32api**: ~15 lines

**Rust replacement feasibility**: **Trivial** — `std::env::temp_dir()` in Rust provides
the same functionality

**Estimate**: Already done (Rust `Persistence` uses `std::fs` and `dirs` crate)
**Verdict**: **Migrated** — not used by Rust engine

---

## 3. Build-Time Dependencies

### 3.1 `hatchling >= 1.21.0`

**Why it exists**: Modern Python build backend (replaces setuptools/distutils)

**Rust replacement**: `cargo` — already the build system for the Rust engine
**Verdict**: **Remove** from desktop build pipeline; retain for Python reference library

### 3.2 PyInstaller (implied by `backend.spec`)

**Why it existed**: Bundle Python backend + dependencies into a single `backend.exe`

**Current status**: Already removed from build pipeline (`backend.spec` deleted)
**Verdict**: **Removed**

### 3.3 `wyversion` (legacy setup.py)

**Why it existed**: Check wxPython version during legacy installation
**Verdict**: **Removed** (legacy setup.py no longer used)

---

## 4. C Extensions

### 4.1 `_pycdgAux.c` (913 lines)

**Why it exists**: Fast C implementation of CDG packet decoding, linked against SDL.
Provides `CdgPacketReader` with the same interface as `cdg_aux.py` but significantly
faster. Used by `CdgPlayer` for frame decoding.

**Files that use it**:
- `players/cdg.py` — imports and uses `_pycdgAux` as the primary decoder

**Rust replacement feasibility**:
- **Very feasible** — the CDG format is simple (16 instructions, 24-byte packets),
  300×216 pixel buffer at 16 colours. A pure Rust implementation with efficient
  `Vec<u8>` operations would match C performance.
- The Rust `format/cdg.rs` already has the data structures and packet parsing implemented

**Estimate**: 2-3 weeks for a complete Rust CDG decoder including:
- Packet parsing (done)
- Memory preset, border preset, tile block, scroll, XOR
- Colour table loading and management
- Frame rendering to RGBA pixel buffer
- Test coverage matching the Python+C test suite

**Verdict**: **Migrate** — the Rust implementation replaces both `_pycdgAux.c` and
`cdg_aux.py`

### 4.2 `_cpuctrl.c` (214 lines)

**Why it exists**: GP2X handheld CPU frequency scaling. The GP2X is a Linux-based
handheld gaming device from 2005-2008.

**Files that use it**:
- `core/manager.py` — `CPUScaler` class

**Rust replacement feasibility**:
- **Not needed** — GP2X target is obsolete, no modern Rust crate exists for it
- If needed: platform-specific `ioctl` calls on Linux

**Estimate**: N/A
**Verdict**: **Remove** (dead platform)

---

## 5. Python Standard Library (No Replacement Needed)

These are used by the Python code but have direct Rust stdlib equivalents:

| Python stdlib module | Used for | Rust equivalent |
|----------------------|----------|-----------------|
| `os`, `os.path` | File system operations | `std::path`, `std::fs` |
| `re` | Regex (filename parsing) | `regex` crate (already in use) |
| `json` | IPC protocol, data serialization | `serde_json` (already in use) |
| `pickle` | Database serialization (legacy) | Not needed — replaced by JSON |
| `subprocess` | External player spawning | `std::process::Command` |
| `threading` | Background tasks | `std::thread` |
| `tempfile`, `shutil` | File operations | `std::fs`, `tempfile` crate (dev) |
| `base64`, `binascii` | Encoding | Not needed |
| `io`, `struct` | Binary I/O | `std::io`, byte-level operations |
| `dataclasses` | Data structures | `struct` derives |
| `pathlib` | Path manipulation | `std::path::PathBuf` |

---

## 6. Dependency Migration Roadmap

```
Phase 1: Immediate (Weeks 1-2)
┌──────────────────────────────────────────────────────┐
│  win32api     → dirs crate            REMOVED ✓      │
│  mutagen      → mp3-duration / lofty  MIGRATE        │
│  numpy        → Vec<u8> ops           MIGRATE        │
│  wxPython     → Tauri dialog          REMOVE         │
│  PyInstaller  → cargo build           REMOVED ✓      │
│  _cpuctrl.c   → (obsolete)            REMOVE         │
└──────────────────────────────────────────────────────┘

Phase 2: CDG Playback (Weeks 3-6)
┌──────────────────────────────────────────────────────┐
│  pygame.mixer → rodio audio playback  MIGRATE        │
│  _pycdgAux.c  → Rust CDG decoder      MIGRATE        │
│  cdg_aux.py   → Rust decoder          REMOVE         │
│  pygame.surfarray → canvas RGBA       MIGRATE        │
└──────────────────────────────────────────────────────┘

Phase 3: KAR/MIDI Playback (Weeks 5-8)
┌──────────────────────────────────────────────────────┐
│  pygame.midi  → midly + rustysynth    MIGRATE        │
│  pygame.font  → CSS rendered lyrics   MIGRATE        │
│  pygame.event → Tauri event system    REMOVE         │
└──────────────────────────────────────────────────────┘

Phase 4: MPEG, File Watching, Polish (Weeks 7-12)
┌──────────────────────────────────────────────────────┐
│  pygame.movie → gstreamer-rs / ffplay MIGRATE        │
│  pygame.display → Tauri window        MIGRATE        │
│  Manual scan  → notify crate          MIGRATE        │
│  fastapi/uvicorn → axum (if HTTP API) MIGRATE        │
│  pymedia      → (not needed)          REMOVE         │
└──────────────────────────────────────────────────────┘
```

**Target: Zero Python required at runtime after Phase 4**

---

## 7. Python Retention Policy

| Location | Purpose | Retention |
|----------|---------|-----------|
| `src/pykaraoke/` | Reference implementation for Rust behaviour comparison | **Retain** (not shipped) |
| `src/pykaraoke/core/filename_parser.py` | Test oracle for Rust `filename_parser.rs` | **Retain** (compat tests) |
| `src/pykaraoke/core/database.py` | Reference for database schema | **Retain** (compat tests) |
| `src/pykaraoke/players/cdg_aux.py` | Reference for CDG algorithm | **Retain** (compat tests) |
| `src/pykaraoke/players/kar.py` | Reference for MIDI/KAR parsing | **Retain** (compat tests) |
| `pyproject.toml` | Python metadata (dev, test, docs groups) | **Retain** (CI/docs only) |
| `src/runtimes/tauri/src-tauri/backend/` | Stale PyInstaller build | **Removed** |
| `backend.spec` | PyInstaller configuration | **Removed** |
| `scripts/stage-backend.js` | PyInstaller build runner | **Removed** |
| `native/_pycdgAux.c` | CDG C extension | **Retain** (reference) |
| `native/_cpuctrl.c` | GP2X CPU scaling | **Retain** (reference) |

Python source is retained in the repository as a reference/compatibility oracle but
is **not required to build, package, install, or run** the desktop application.
