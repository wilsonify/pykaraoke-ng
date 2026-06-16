# Rust-First Architecture

**Objective**: A desktop application that can be built, packaged, installed, and run
without requiring Python at runtime.

**Technology preference order**:
1. **Rust** — all business logic, state, persistence, media management
2. **Tauri UI layer** — window management, native dialogs, IPC bridge
3. **JavaScript/TypeScript** — only where required by the Tauri framework
4. **Python** — transitional; eliminated from runtime dependency chain

---

## 1. Current Architecture (Baseline)

```
┌──────────────────────────────────────────────────────────────┐
│                    Tauri Desktop (Rust)                       │
│  main.rs ── 3 commands (start, send_command, stop)           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  pykaraoke-engine (Rust crate)                            │   │
│  │    backend.rs     — 18 command handlers, IPC protocol     │   │
│  │    queue.rs       — playlist management                   │   │
│  │    library.rs     — song database, search, dedup          │   │
│  │    discovery.rs   — file scanning (ZIP stubbed)           │   │
│  │    player.rs      — state machine, timing                 │   │
│  │    database.rs    — JSON persistence                      │   │
│  │    song.rs        — data structures                       │   │
│  │    filename_parser.rs — artist/title extraction           │   │
│  │    format/        — constants + stubs (CDG, KAR, MPEG)    │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
         │ IPC (Tauri invoke)
         ▼
┌──────────────────────────────────────────────────────────────┐
│  Tauri Frontend (JavaScript) — app.js                         │
│    sendCommand() → invoke('send_command', {action, params})   │
│    ensureBackendStarted() → invoke('start_backend')           │
│    startStatePolling() → setInterval(1s) get_state            │
│    updateUIFromState() — maps backend state to DOM            │
│    Business logic: double-click debounce, hold-to-seek,       │
│      keyboard shortcuts, drag-and-drop, search debounce       │
└──────────────────────────────────────────────────────────────┘
```

### Current state
- **Rust engine**: 126 tests pass, covers filename parsing, queue, library, player, database,
  backend command dispatch.  Zero audio decoding or playback.
- **Format handlers**: CDG packet parsing works but no rendering; KAR/MIDI structures defined
  but no parser; MPEG constants only.
- **Frontend business logic**: Significant (~200 lines of UX logic: double-click debounce,
  hold-to-seek timers, drag-and-drop, keyboard shortcuts, search debounce).
- **Python runtime required**: `pygame` for audio/video playback; `numpy` for CDG pixel ops;
  `mutagen` for metadata; `wxPython` for performer prompt.

---

## 2. Target Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Tauri Desktop (Rust)                                                    │
│  main.rs — auto-starts engine on app launch, persists on shutdown     │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  pykaraoke-engine (Rust crate)  — owns ALL business logic         │  │
│  │                                                                  │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  Backend (orchestrator)                                     │  │  │
│  │  │    - Singleton state machine                                │  │  │
│  │  │    - Command dispatch (no change)                           │  │  │
│  │  │    - Event emission (state_changed, song_finished)          │  │  │
│  │  │    - Auto-advance on song completion                        │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                                                                  │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │  │
│  │  │ Audio Engine  │ │ CDG Decoder  │ │ MIDI/KAR Parser         │  │  │
│  │  │ (cpal/rodio)  │ │ (full impl)  │ │ (full lyric extraction) │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘  │  │
│  │                                                                  │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │  │
│  │  │ File Watcher  │ │ ZIP Scanner  │ │ Settings / DB            │  │  │
│  │  │ (notify crate)│ │ (zip crate)  │ │ (exists, JSON-based)     │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Tauri Commands                                                   │  │
│  │    #[tauri::command] fn send_command(action, params) → Response   │  │
│  │    #[tauri::command] fn get_state() → BackendFullState            │  │
│  │    #[tauri::command] fn fetch_frame() → Vec<u8> (CDG pixels)     │  │
│  │    #[tauri::command] fn get_settings() → Settings                 │  │
│  │    #[tauri::command] fn update_settings(s) → Result               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
         │ IPC (Tauri invoke)
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Tauri Frontend (minimal JS)                                           │
│    - Renders CDG canvas from pixel frames received via invoke         │
│    - Renders KAR lyrics from structured data                          │
│    - Playback controls (play, pause, stop, next, prev, seek, volume) │
│    - Library browser (search, filter, sort)                          │
│    - Playlist view (add, remove, reorder)                           │
│    - Settings modal                                                  │
│    - Folder management (add, remove)                                 │
│    - NO business logic — all logic in Rust backend                   │
│    - State polling eliminated; event-driven via Tauri events         │
└──────────────────────────────────────────────────────────────────────┘
```

### Key differences from current architecture

| Aspect | Current | Target |
|--------|---------|--------|
| **State polling** | 1-second `setInterval` polling `get_state` | Event-driven: backend emits `state_changed`, `song_finished`, `playlist_updated` events via Tauri event system |
| **Audio playback** | Python `pygame` subprocess | Rust `rodio` or `cpal` in-process |
| **CDG rendering** | Python `pygame` surfarray + C extension | Rust pixel pipeline → send frame data to frontend for canvas rendering |
| **CDG pixel output** | pygame video surface | `Vec<u8>` RGBA pixels sent via Tauri command, rendered on `<canvas>` |
| **KAR/MIDI playback** | Python `pygame.midi` | Rust `midly` → send lyrics + timing to frontend for rendering |
| **MPEG playback** | Python `pygame.movie` or external player | Rust `gstreamer` or bundled `ffplay` subprocess |
| **File watching** | Manual "Scan Library" button | `notify` crate — auto-detect new/deleted files |
| **Performer prompt** | wxPython dialog | Tauri dialog command + JS prompt |
| **Frontend logic** | ~200 lines UX logic (debounce, timers, shortcuts) | All moved to Rust; JS only handles DOM manipulation |
| **IPC** | `send_command(action, params)` single command | Multiple typed commands: `play`, `pause`, `stop` as separate `#[tauri::command]` functions (type-safe, self-documenting) |

---

## 3. Module Ownership

| Domain | Owner | Notes |
|--------|-------|-------|
| Filename parsing | **Rust** | Done — `filename_parser.rs`, 38 tests, production-ready |
| Song data structures | **Rust** | Done — `song.rs` |
| Queue / playlist | **Rust** | Done — `queue.rs`, 14 tests, production-ready |
| Library / search | **Rust** | Done — `library.rs`, 12 tests, production-ready |
| Settings persistence | **Rust** | Done — `database.rs`, 5 tests, JSON-based |
| Backend command dispatch | **Rust** | Done — `backend.rs`, 22 tests, 18 handlers |
| Player state machine | **Rust** | Done — `player.rs`, 11 tests |
| File scanner | **Rust** | Done — `discovery.rs`, 5 tests, ZIP stubbed |
| ZIP file scanning | **Rust** | Pending — add `zip` crate to dependencies |
| CDG packet decoding | **Rust** | Partially done — constants + packet struct, no rendering |
| CDG pixel rendering | **Rust** | Not started — needs pixel pipeline (RGBA buffer → frontend canvas) |
| KAR/MIDI parsing | **Rust** | Not started — needs `midly` crate for MIDI event parsing + lyric extraction |
| MPEG playback | **Rust** | Not started — external player or `gstreamer` binding |
| Audio output | **Rust** | Not started — needs `rodio` or `cpal` |
| File watching | **Rust** | Not started — needs `notify` crate |
| Performer prompt | **Rust/Tauri** | Tauri dialog + lightweight JS UI |
| UI rendering | **JavaScript** | `<canvas>` for CDG, DOM for lyrics, HTML/CSS for controls |
| Window management | **Tauri** | Already handled by Tauri framework |
| Native dialogs | **Tauri** | Already handled by Tauri `dialog` plugin |

---

## 4. IPC Architecture (Event-Driven)

### Current: Poll-based

```
Frontend                     Backend
   │                           │
   ├── invoke('send_command', {action:"play"}) ──► play()
   │                                               │
   │◄── Response {status:"ok"}                    │
   │                                               │
   │  (every 1 second)                             │
   ├── invoke('send_command', {action:"get_state"})──► get_state()
   │◄── Response {status:"ok", data:{...}}         │
```

### Target: Event-Driven

```
Frontend                     Backend
   │                           │
   ├── invoke('play') ────────► play()
   │                           ├── emit('state_changed', {state:"playing", ...})
   │◄── Event ─────────────────┤
   │                           │  (song finishes)
   │                           ├── emit('song_finished', {})
   │                           ├── emit('state_changed', {state:"idle", ...})
   │◄── Events ───────────────┤
```

**Benefits**:
- Lower latency (no polling interval)
- Fewer IPC calls (only emit on change)
- Cleaner separation of concerns
- Frontend is purely reactive (no polling timers)

---

## 5. Data Flow

### Playback Flow (CD+G example)
```
1. User clicks song in playlist
2. Frontend: invoke('play', {playlist_index: 2})
3. Rust: Backend.handle_play()
   → Queue.select(2) → SongStruct (filepath: "/music/song.cdg")
4. Rust: CdgDecoder.open("/music/song.cdg")
   → Read CDG packets from file
   → Decode tile blocks, color tables
5. Rust: emit('state_changed', {current_song: ..., playback_state: "playing"})
6. Rust: AudioEngine.play("/music/song.mp3")  // companion audio
   → rodio Sink in background thread
7. Rust: Each frame (40ms):
   → CdgDecoder.render_frame() → Vec<u8> RGBA pixels
   → emit('frame', {pixels: [...], timestamp_ms: ...})
8. Frontend: on 'frame' event:
   → canvas.putImageData(pixels)
9. Audio finishes:
   → Rust auto-advance: Queue.advance() → emit('state_changed')
```

### Search Flow
```
1. User types in search box
2. Frontend: invoke('search_songs', {query: "queen"})
3. Rust: Library.search("queen") → Vec<SearchResult>
4. Rust: Response {status:"ok", data: {results: [...], count: 5}}
5. Frontend: renderSearchResults(results)
```

---

## 6. Frontend Responsibility (Minimal)

The JavaScript frontend should only:
1. **Render**: DOM manipulation based on state received from backend
2. **Capture input**: Click events → invoke backend commands
3. **Display**: CDG frames as canvas pixel data, lyrics as styled DOM
4. **Native dialogs**: File picker, performer name prompt

All of the following should move to Rust:
- Double-click detection logic
- Hold-to-seek timer management
- Search debounce timing
- Keyboard shortcut dispatch
- Backend lifecycle (auto-retry, health checking)
- Volume slider optimization logic
- Backend startup/shutdown sequencing

---

## 7. Key Decisions

| Decision | Rationale |
|----------|-----------|
| **No Python at runtime** | All Python dependencies (`pygame`, `numpy`, `mutagen`, `wxPython`) replaced by Rust crates or removed. Python source retained for reference/test comparison only. |
| **Event-driven IPC over polling** | Eliminates 1-second state polling latency. Backend emits events only on state change. |
| **Separate typed commands over single dispatch** | `invoke('play')`, `invoke('pause')` instead of `invoke('send_command', {action:"play"})`. Type-safe, self-documenting, no runtime action string matching. |
| **Canvas for CDG, DOM for lyrics** | CDG is pixel data (300×216 indexed BMP) best rendered on `<canvas>`. KAR lyrics are structured text best rendered as styled DOM elements. |
| **rodio for audio** | Pure Rust audio playback, minimal dependencies, supports WAV/MP3/OGG/Vorbis/FLAC. |
| **notify for file watching** | Cross-platform filesystem events, eliminates manual "Scan Library" button. |
| **midly for MIDI parsing** | Pure Rust MIDI parser, no external dependencies, handles standard MIDI files and KAR lyric events. |
| **gstreamer or subprocess for MPEG** | MPEG video decoding is complex. GStreamer Rust bindings (`gstreamer-rs`) are the preferred path. Fallback: bundled `ffplay` subprocess. |
