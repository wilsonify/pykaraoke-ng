# PyKaraoke NG — Rust Engine Migration Plan

## Overview

Migrate the PyKaraoke NG karaoke engine from Python to Rust, module by module, keeping the Python backend operational throughout. The Rust engine will ultimately replace the Python `backend.exe` spawned by the Tauri desktop application.

## Architecture

```
┌──────────────────────────────┐
│   Tauri Desktop App (Rust)   │
│  (src/runtimes/tauri/)       │
├──────────────────────────────┤
│   Native Backend (Rust)      │  ◄── NEW: replaces Python backend
│   crates/pykaraoke-engine    │
│                              │
│   ┌──────────────────────┐   │
│   │  Backend Service     │   │
│   │  (stdio JSON IPC)    │   │
│   ├──────────────────────┤   │
│   │  Queue Manager       │   │
│   │  Playback Controller │   │
│   │  Library Scanner     │   │
│   │  Song Discovery      │   │
│   │  Filename Parser     │   │
│   │  Format Handlers     │   │
│   │  Database/Persistence│   │
│   └──────────────────────┘   │
└──────────────────────────────┘

Python backend (src/pykaraoke/) — kept operational throughout migration
Rust compatibility tests exercise both and compare outputs.
```

## Migration Priority Order

Each priority is a self-contained deliverable with its own tests.

### Priority 1 — Filename Parsing [`crates/pykaraoke-engine/src/filename_parser.rs`]
- [x] `ParsedSong` data struct with `artist`, `title`, `disc`, `track`
- [x] `FileNameType` enum (DISC_TRACK_ARTIST_TITLE, DISCTRACK_ARTIST_TITLE, DISC_ARTIST_TITLE, ARTIST_TITLE)
- [x] `FilenameParser` struct with configurable `file_name_type`
- [x] `parse()` — handles `" - "` space-dash-space and legacy dash formats
- [x] Abbreviation heuristic for artist names with dashes (e.g. "AC-DC")
- [x] `parse_zip_path()` — directory-based artist fallback for ZIP members
- [x] Directory dashes ignored (basename-only parsing)
- [x] Extension stripping
- **Validation**: Same inputs → identical `ParsedSong` outputs in both engines

### Priority 2 — Song Discovery [`crates/pykaraoke-engine/src/discovery.rs`]
- [ ] File extension filtering (`.cdg`, `.kar`, `.mid`, `.mpg`, `.mpeg`, `.avi`, `.divx`, `.xvid`, `.mp3`, `.ogg`)
- [ ] Recursive directory scanning
- [ ] ZIP file introspection
- [ ] `titles.txt` reading
- [ ] `SongStruct` creation from file paths
- **Validation**: Scan same directories → identical song lists

### Priority 3 — Library Scanning/Management [`crates/pykaraoke-engine/src/library.rs`]
- [ ] In-memory song database
- [ ] Multi-term case-insensitive search
- [ ] Sort by title, artist, filename
- [ ] Duplicate detection (SHA-256)
- [ ] Folder add/remove
- **Validation**: Same search/sort inputs → identical results

### Priority 4 — Queue Management [`crates/pykaraoke-engine/src/queue.rs`]
- [ ] Playlist (ordered list of songs)
- [ ] Add/remove/clear
- [ ] Current index tracking
- [ ] Auto-advance on song finish
- [ ] Event emission on mutation
- **Validation**: Same sequence of add/remove/play ops → identical queue state

### Priority 5 — Playback State Management [`crates/pykaraoke-engine/src/player.rs`]
- [ ] State machine: Init → Playing → Paused → NotPlaying → Closing → Closed
- [ ] Time tracking (play_time, play_start_time)
- [ ] Seek position tracking
- [ ] State transition validation
- **Validation**: Same state transitions → identical state, position, timing

### Priority 6 — Database/Persistence [`crates/pykaraoke-engine/src/database.rs`]
- [ ] Settings storage (key-value, JSON-based)
- [ ] Song database serialization (JSON instead of pickle)
- [ ] Save/load cycle
- **Validation**: Same data in → identical data out

### Priority 7 — Playback Control Operations [`crates/pykaraoke-engine/src/backend.rs`]
- [ ] Command dispatch (play, pause, stop, next, previous, seek, volume)
- [ ] HTTP API parity (FastAPI-compatible REST endpoints)
- [ ] stdio JSON-line IPC protocol
- [ ] State serialization for frontend
- **Validation**: Same commands → identical state after each command

### Priority 8 — Format-Specific Handlers [`crates/pykaraoke-engine/src/format/`]
- [ ] CD+G constants and command set
- [ ] KAR/MIDI constants and structure
- [ ] MPEG constants
- **Validation**: Same format definitions → constants are byte-identical

## File Layout

```
crates/
  pykaraoke-engine/
    Cargo.toml
    src/
      lib.rs              — crate root, re-exports
      filename_parser.rs  — Priority 1
      song.rs             — SongStruct, SongData, etc.
      discovery.rs        — Priority 2
      library.rs          — Priority 3
      queue.rs            — Priority 4
      player.rs           — Priority 5
      database.rs         — Priority 6
      backend.rs          — Priority 7
      format/
        mod.rs            — module root
        cdg.rs            — CD+G constants
        kar.rs            — KAR/MIDI constants
        mpg.rs            — MPEG constants
```

## Validation Strategy

### Compatibility Test Harness

Each compatibility test:
1. Runs the same input through the Python engine
2. Runs it through the Rust engine
3. Compares outputs, errors, and side effects

```python
# tests/compat/test_filename_parser_compat.py
def test_parse_artist_title():
    py_result = py_parse("Artist - Title.mp3")
    rs_result = rs_parse("Artist - Title.mp3")
    assert py_result == rs_result
```

### Test Data Sources
- All existing Python test cases (parameterized)
- Real-world song library files
- Edge cases documented in Python tests

## Incremental Delivery

Each priority ends with:
1. Rust implementation complete
2. Python ↔ Rust compatibility tests passing
3. Documented in RUST_COMPATIBILITY_REPORT.md

## Completion Criteria

The migration is complete when:
- [ ] All 8 priority modules are implemented in Rust
- [ ] Compatibility test suite passes for all modules
- [ ] Tauri desktop app operates against the Rust backend directly
- [ ] `RUST_COMPATIBILITY_REPORT.md` documents all intentional differences
- [ ] Existing Python end-to-end tests remain passing
- [ ] No behavioral regressions in the desktop application
