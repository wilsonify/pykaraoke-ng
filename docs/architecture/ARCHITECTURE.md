# Architecture

**Date**: 2026-06-16  
**Scope**: Interface boundaries between the Rust engine (`pykaraoke-engine`) and the Tauri desktop application  
**Design Goal**: Independent development of backend and frontend, minimal coupling, stable contracts

---

## 1. Component Dependency Diagram

```
┌══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║                        Desktop Application                           ║
║                                                                      ║
║  ┌──────────────────────────────────────────────────────────────┐    ║
║  │                     Frontend (JavaScript)                      │   ║
║  │                                                               │   ║
║  │  Responsibilities:                                            │   ║
║  │  • Render UI from view models received via IPC                 │   ║
║  │  • Capture user gestures → emit intentions (typed commands)    │   ║
║  │  • Display CDG frames on <canvas> from pixel data              │   ║
║  │  • Display KAR lyrics as styled DOM from structured data       │   ║
║  │  • Handle native dialogs (file picker, prompts)               │   ║
║  │                                                               │   ║
║  │  Does NOT contain:                                            │   ║
║  │  • Business logic (debounce, timers, validation)               │   ║
║  │  • State machine logic                                        │   ║
║  │  • File I/O or persistence                                    │   ║
║  │  • Audio/video decoding                                       │   ║
║  └──────────────────┬───────────────────────────────────────────┘    ║
║                     │ IPC (Tauri invoke + events)                     ║
║                     ▼                                                 ║
║  ┌──────────────────────────────────────────────────────────────┐    ║
║  │                   Tauri Shell (Rust)                          │    ║
║  │  src/runtimes/tauri/src-tauri/src/main.rs                     │    ║
║  │                                                               │    ║
║  │  Responsibilities:                                            │    ║
║  │  • Bridge: typed #[tauri::command] → Engine trait methods     │    ║
║  │  • Event relay: EngineEventBus → Tauri event emission         │    ║
║  │  • Lifecycle: start/stop engine, persist on shutdown          │    ║
║  │  • Window management (Tauri framework)                        │    ║
║  │                                                               │    ║
║  │  Does NOT contain:                                            │    ║
║  │  • Business logic transformations                             │    ║
║  │  • Direct engine internals access (goes through Engine trait) │    ║
║  │  • View model construction (engine provides views)            │    ║
║  └──────────────────┬───────────────────────────────────────────┘    ║
║                     │ Rust function calls (Engine trait)              ║
║                     ▼                                                 ║
║  ┌──────────────────────────────────────────────────────────────┐    ║
║  │              pykaraoke-engine (Rust crate)                    │    ║
║  │  crates/pykaraoke-engine/src/                                 │    ║
║  │                                                               │    ║
║  │  Responsibilities:                                            │    ║
║  │  • Owns all application state (singleton Backend)             │    ║
║  │  • Owns persistence (settings, song database)                 │    ║
║  │  • Owns queue and playlist management                         │    ║
║  │  • Owns library scanning and search                           │    ║
║  │  • Owns audio playback (rodio)                                │    ║
║  │  • Owns CDG/KAR/MPEG decoding                                 │    ║
║  │  • Owns file watching (notify)                                │    ║
║  │  • Produces view models for frontend consumption               │    ║
║  │  • Emits events via EngineEventBus trait                      │    ║
║  │                                                               │    ║
║  │  Does NOT contain:                                            │    ║
║  │  • Tauri IPC or event system dependency                       │    ║
║  │  • Frontend-specific logic                                    │    ║
║  │  • Serialization format decisions for IPC                     │    ║
║  └──────────────────────────────────────────────────────────────┘    ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

### Dependency Direction

```
Frontend (JS) ───invoke()/listen()──► Tauri Shell ───Engine trait──► Engine
                                          │                            │
                                          │                            │
                                          ◄───EngineEventBus────────────┘
```

- **Dependencies flow INWARD**: Frontend → Tauri Shell → Engine
- **Events flow OUTWARD**: Engine → Tauri Shell → Frontend
- **No circular dependencies**: Engine knows nothing about Tauri or the frontend
- **Testability**: Each layer is testable in isolation (see Section 6)

---

## 2. Current Architecture (Problems)

### Current State

```
Frontend (JS)                     Tauri Shell                     Engine
    │                                  │                             │
    ├── invoke('send_command',         │                             │
    │     {action:"play", params:{}})───►                            │
    │                                  ├── CommandRequest {           │
    │                                  │     action: "play",         │
    │                                  │     params: {}              │
    │                                  │   }                         │
    │                                  ├──► Backend.handle_command()─►│
    │                                  │                             ├── match "play"
    │                                  │                             │   → handle_play()
    │                                  │◄── CommandResponse ─────────┤
    │                                  ├── CommandResponseWrapper     │
    │◄── JSON response ────────────────┤                             │
    │                                  │                             │
    │  (every 1 second)               │                             │
    ├── invoke('send_command',         │                             │
    │     {action:"get_state"})────────►                             │
    │◄── BackendFullState (JSON) ──────┤                             │
```

### Identified Problems

| # | Problem | Impact |
|---|---------|--------|
| 1 | **Single generic command channel** — all actions go through `send_command(action: String, params: Value)`. Action string is a protocol leak; no compile-time validation. | Typos cause silent failures. Frontend and engine must stay synchronized on action names. |
| 2 | **Engine domain types are IPC schema** — `SongStruct`, `BackendFullState`, `Settings` are serialized directly to the frontend. Changing any field breaks the frontend. | No versioning. No filtering. Schema changes are breaking changes. |
| 3 | **No event system** — `BackendEvent` enum exists but is never emitted. Frontend polls `get_state` every 1 second. | Wasted IPC, higher latency, state transition misses. |
| 4 | **Tauri shell manages engine internals** — `main.rs` creates `Persistence`, calls `load_settings()` and `load_database()` directly. | Ownership boundary blurred. If engine changes initialization, main.rs must change. |
| 5 | **`stop_backend` never called** — `send_command` is the only command used. Settings/database not persisted on exit. | Data loss on unexpected shutdown. |
| 6 | **Frontend has business logic** — double-click debounce, hold-to-seek, search debounce, keyboard shortcuts, retry logic. Should be in the engine. | Frontend cannot be replaced without reimplementing logic. |
| 7 | **Protocol mismatch in `update_settings`** — frontend sends flat `{fullscreen, zoom_mode}`, engine expects nested `{settings: {...}}`. `zoom_mode` doesn't exist in Rust. | Settings saving is broken. |
| 8 | **Engine is not independently testable from its interface** — tests go through `CommandRequest`/`CommandResponse`, not a typed API. | Integration-style tests; can't mock or stub individual capabilities. |

---

## 3. Target Architecture

### Interface Layers

```
Frontend View Models     ←── Engine produces, Frontend consumes
(DTOs designed for UI)       These are versioned, filtered, frontend-friendly

Domain Commands           ──► Frontend emits, Engine consumes
(typed intentions)            These are high-level operations, not implementation details

Engine Trait              ──► Tauri Shell calls Engine through this trait
(interface boundary)          Engine can be swapped, mocked, tested independently

Events (push)             ◄── Engine emits events via EventBus trait
(typed notifications)        Tauri Shell relays to frontend via Tauri event system
```

### Engine Trait (Public API)

```rust
/// The public interface of the karaoke engine.
/// The Tauri shell calls this trait; the frontend never sees it directly.
pub trait Engine: Send {
    // ── Lifecycle ──────────────────────────────────────────────
    fn start(&mut self) -> Result<(), EngineError>;
    fn stop(&mut self) -> Result<(), EngineError>;
    fn status(&self) -> EngineStatus;

    // ── Playback ───────────────────────────────────────────────
    fn play(&mut self, song_id: Option<SongId>) -> Result<PlaybackState, EngineError>;
    fn pause(&mut self) -> Result<PlaybackState, EngineError>;
    fn stop_playback(&mut self) -> Result<PlaybackState, EngineError>;
    fn next(&mut self) -> Result<PlaybackState, EngineError>;
    fn previous(&mut self) -> Result<PlaybackState, EngineError>;
    fn seek(&mut self, position_ms: u64) -> Result<PlaybackState, EngineError>;
    fn set_volume(&mut self, volume: NormalizedF64) -> Result<PlaybackState, EngineError>;

    // ── Queue ───────────────────────────────────────────────────
    fn enqueue(&mut self, filepath: &str) -> Result<QueueView, EngineError>;
    fn remove_from_queue(&mut self, index: usize) -> Result<QueueView, EngineError>;
    fn clear_queue(&mut self) -> Result<QueueView, EngineError>;
    fn move_in_queue(&mut self, from: usize, to: usize) -> Result<QueueView, EngineError>;
    fn queue(&self) -> QueueView;

    // ── Library ─────────────────────────────────────────────────
    fn scan_library(&mut self) -> Result<LibraryScanProgress, EngineError>;
    fn add_library_folder(&mut self, path: &str) -> Result<(), EngineError>;
    fn remove_library_folder(&mut self, path: &str) -> Result<(), EngineError>;
    fn library_folders(&self) -> Vec<String>;

    // ── Search ──────────────────────────────────────────────────
    fn search(&self, query: &str) -> SearchResultsView;

    // ── Settings ────────────────────────────────────────────────
    fn settings(&self) -> SettingsView;
    fn update_settings(&mut self, delta: SettingsDelta) -> Result<SettingsView, EngineError>;
}
```

### EventBus Trait (Engine → UI notification)

```rust
/// Implemented by the Tauri shell to relay engine events to the frontend.
/// The engine calls these methods when state changes occur.
pub trait EventBus: Send + Sync {
    fn emit_playback_changed(&self, state: PlaybackState);
    fn emit_queue_changed(&self, queue: QueueView);
    fn emit_library_changed(&self, library: LibraryView);
    fn emit_settings_changed(&self, settings: SettingsView);
    fn emit_scan_progress(&self, progress: LibraryScanProgress);
    fn emit_error(&self, error: EngineErrorInfo);
}
```

### View Types (DTOs — versioned, frontend-friendly)

These are the types the frontend receives. They are explicitly designed for UI consumption:

```rust
/// Lightweight song representation for the frontend.
/// NOT the same as internal SongStruct — filtered fields, stable schema.
pub struct SongView {
    pub id: SongId,
    pub title: String,
    pub artist: String,
    pub filepath: String,
    pub display_name: String,  // "Artist - Title"
    pub duration_seconds: f64,
    pub format: SongFormat,    // "cdg", "kar", "mpg"
}

pub struct PlaybackState {
    pub status: PlaybackStatus,  // "playing", "paused", "stopped", "loading", "idle"
    pub current_song: Option<SongView>,
    pub position_ms: u64,
    pub duration_ms: u64,
    pub volume: f64,
}

pub struct QueueView {
    pub songs: Vec<SongView>,
    pub current_index: Option<usize>,
    pub total_duration_seconds: f64,
}

pub struct SearchResultsView {
    pub query: String,
    pub results: Vec<SongView>,
    pub total_count: usize,
}

pub struct SettingsView {
    pub library_folders: Vec<String>,
    pub display: DisplaySettings,
    pub audio: AudioSettings,
    pub lyrics: LyricsSettings,
}

pub struct DisplaySettings {
    pub fullscreen: bool,
    pub width: u32,
    pub height: u32,
    pub always_on_top: bool,
}

pub struct AudioSettings {
    pub volume: f64,
    pub sync_delay_ms: i64,
}

pub struct LyricsSettings {
    pub show: bool,
    pub font_size: u32,
    pub font_bold: bool,
    pub font_italic: bool,
}

/// Delta for partial settings updates (frontend sends only changed fields).
pub struct SettingsDelta {
    pub fullscreen: Option<bool>,
    pub volume: Option<NormalizedF64>,
    pub sync_delay_ms: Option<i64>,
    pub show_lyrics: Option<bool>,
    // ... other optional fields
}
```

---

## 4. Interface Boundaries

### 4.1 Frontend ↔ Tauri Shell (IPC Boundary)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Tauri Commands (typed #[tauri::command])                            │
│                                                                      │
│  engine_start()  → Result<(), String>                                │
│  engine_stop()   → Result<(), String>                                │
│  engine_status() → EngineStatus                                      │
│                                                                      │
│  playback_play(song_id: Option<SongId>)     → PlaybackState          │
│  playback_pause()                           → PlaybackState          │
│  playback_stop()                            → PlaybackState          │
│  playback_next()                            → PlaybackState          │
│  playback_previous()                        → PlaybackState          │
│  playback_seek(position_ms: u64)            → PlaybackState          │
│  playback_set_volume(volume: f64)           → PlaybackState          │
│                                                                      │
│  queue_enqueue(filepath: String)            → QueueView              │
│  queue_remove(index: usize)                 → QueueView              │
│  queue_clear()                              → QueueView              │
│  queue_move(from: usize, to: usize)         → QueueView              │
│  queue_list()                               → QueueView              │
│                                                                      │
│  library_scan()                             → LibraryScanProgress    │
│  library_add_folder(path: String)           → Result<(), String>     │
│  library_remove_folder(path: String)        → Result<(), String>     │
│  library_folders()                          → Vec<String>            │
│                                                                      │
│  search(query: String)                      → SearchResultsView      │
│                                                                      │
│  settings_get()                             → SettingsView           │
│  settings_update(delta: SettingsDelta)      → SettingsView           │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  Tauri Events (push from engine to frontend)                         │
│                                                                      │
│  "engine:playback_changed"  → PlaybackState                         │
│  "engine:queue_changed"     → QueueView                              │
│  "engine:library_changed"   → LibraryView                            │
│  "engine:settings_changed"  → SettingsView                           │
│  "engine:scan_progress"     → LibraryScanProgress                    │
│  "engine:error"             → EngineErrorInfo                        │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Tauri Shell ↔ Engine (Rust function call boundary)

```rust
// Tauri Shell calls these on an Engine trait object:
trait Engine {
    fn start(&mut self) -> Result<(), EngineError>;
    fn play(&mut self, song_id: Option<SongId>) -> Result<PlaybackState, EngineError>;
    fn enqueue(&mut self, filepath: &str) -> Result<QueueView, EngineError>;
    // ... etc
}

// Engine calls these on an EventBus trait object:
trait EventBus {
    fn emit_playback_changed(&self, state: PlaybackState);
    fn emit_queue_changed(&self, queue: QueueView);
    // ... etc
}
```

### 4.3 Engine Internal Boundaries (within the crate)

```
Engine (trait impl)
    │
    ├──► Backend (state machine orchestrator)
    │       │
    │       ├──► Library (scanning, search, folders)
    │       ├──► Queue (playlist management)
    │       ├──► Player (state machine, timing)
    │       ├──► Persistence (save/load settings + database)
    │       ├──► AudioEngine (rodio-based playback)
    │       ├──► CdgDecoder (CDG pixel rendering)
    │       ├──► KarParser (MIDI parsing + lyric extraction)
    │       ├──► MpegPlayer (external player or GStreamer)
    │       └──► FileWatcher (notify-based filesystem monitoring)
    │
    ├──► View model construction (SongView::from_song_struct, etc.)
    └──► Event emission (via EventBus trait)
```

Internal modules may reference each other freely (they are within the same crate). Only the `Engine` trait and the view model types are the public boundary.

---

## 5. Data Flow Diagrams

### 5.1 Playback Command (e.g., user clicks "Play")

```
Frontend                          Tauri Shell                      Engine
   │                                  │                              │
   │ invoke('playback_play',          │                              │
   │   {song_id: 42}) ───────────────►│                              │
   │                                  ├── engine.play(Some(42)) ────►│
   │                                  │                              ├── validate song_id
   │                                  │                              ├── Queue.select(42)
   │                                  │                              ├── BackendState::Playing
   │                                  │                              ├── AudioEngine.play(file)
   │                                  │                              ├── event_bus.emit_playback_changed()
   │                                  │◄── Ok(PlaybackState) ────────┤
   │◄──  PlaybackState (JSON) ───────┤                              │
   │                                  │                              │
   │  (state change event arrives    │                              │
   │   via Tauri event system)       │                              │
   │◄── "engine:playback_changed" ────┤                              │
   │                                  │                              │
   │ updateUI(playbackState)          │                              │
```

### 5.2 Event-Driven State Update (no polling)

```
Engine                              Tauri Shell                    Frontend
   │                                    │                            │
   ├── (song finishes)                   │                            │
   ├── state = Idle                     │                            │
   ├── queue.advance()                  │                            │
   ├── event_bus.emit_playback_changed()│                            │
   │                                    │                            │
   │◄── EventBus trait call ────────────┤                            │
   │                                    ├── app_handle.emit_all(     │
   │                                    │   "engine:playback_changed",│
   │                                    │   new_playback_state)      │
   │                                    │                            │
   │                                    │◄── Tauri IPC event ────────┤
   │                                    │                            ├── listen callback fires
   │                                    │                            ├── updateUI(state)
```

### 5.3 Search

```
Frontend                          Tauri Shell                      Engine
   │                                  │                              │
   │ invoke('search',                 │                              │
   │   {query: "queen"}) ────────────►│                              │
   │                                  ├── engine.search("queen") ───►│
   │                                  │                              ├── library.search("queen")
   │                                  │                              ├── build SongView vec
   │                                  │◄── Ok(SearchResultsView) ────┤
   │◄──  SearchResultsView (JSON) ────┤                              │
   │                                  │                              │
   │ renderSearchResults(results)     │                              │
```

---

## 6. Testing Strategy

### 6.1 Engine Tests (no Tauri, no frontend)

```rust
// Unit tests in engine crate — direct Engine trait calls
#[test]
fn test_play_song_from_queue() {
    let mut engine = create_test_engine();     // EngineImpl with mock EventBus
    engine.enqueue("/test/song.kar").unwrap();
    let state = engine.play(None).unwrap();
    assert_eq!(state.status, PlaybackStatus::Playing);
    assert!(state.current_song.is_some());
}
```

### 6.2 Tauri Shell Tests (mocked engine)

```rust
// Integration tests for main.rs — mock the Engine trait
struct MockEngine;
impl Engine for MockEngine {
    fn play(&mut self, _: Option<SongId>) -> Result<PlaybackState, EngineError> {
        Ok(PlaybackState { status: PlaybackStatus::Playing, ... })
    }
    // ...
}

#[test]
fn test_play_command_returns_playing_state() {
    let app = tauri::test::mock_app(/*...*/);
    app.manage(Mutex::new(MockEngine));
    // invoke playback_play command
    // assert response matches expected shape
}
```

### 6.3 Frontend Tests (mocked Tauri IPC)

```javascript
// app.test.js — mock invoke responses
const mockInvoke = async (cmd, args) => {
    if (cmd === 'playback_play') {
        return { status: 'playing', current_song: { title: 'Test' } };
    }
    // ...
};
globalThis.__TAURI__ = { tauri: { invoke: mockInvoke } };
// Test UI behavior against known responses
```

---

## 7. Versioning & Stability

### Schema Versioning

View types (`SongView`, `PlaybackState`, `SettingsView`, etc.) have an explicit version field:

```rust
pub struct SongView {
    pub version: u8,   // Currently 1
    pub title: String,
    // ...
}
```

The frontend checks the version and can adapt if needed. Schema changes increment this version:
- **Adding a field**: Minor version bump (frontend ignores unknown fields via serde `deny_unknown_fields`)
- **Removing a field**: Major version bump (frontend must handle both old and new)
- **Changing field semantics**: Major version bump

### Backward Compatibility

The `SettingsDelta` type allows the frontend to send only changed fields. Old frontends talking to a newer engine (or vice versa) work because:
- Unknown fields in delta are ignored (serde default)
- New fields in response have defaults (serde `#[serde(default)]`)

---

## 8. Module Map

```
crates/pykaraoke-engine/
├── Cargo.toml
├── src/
│   ├── lib.rs                    — Re-exports Engine, EventBus, view types
│   ├── engine.rs                 — Engine trait definition
│   ├── event_bus.rs              — EventBus trait definition
│   ├── views/                    — View models (DTOs for frontend)
│   │   ├── mod.rs
│   │   ├── song_view.rs
│   │   ├── playback_view.rs
│   │   ├── queue_view.rs
│   │   ├── library_view.rs
│   │   ├── search_view.rs
│   │   ├── settings_view.rs
│   │   └── error_view.rs
│   ├── engine_impl.rs            — Engine trait implementation (Backend wrapper)
│   ├── backend.rs                — State machine orchestrator (existing)
│   ├── queue.rs                  — Queue management (existing)
│   ├── library.rs                — Library/search (existing)
│   ├── player.rs                 — State machine (existing)
│   ├── database.rs               — Persistence (existing)
│   ├── discovery.rs              — File scanning (existing)
│   ├── song.rs                   — Internal SongStruct (existing)
│   ├── filename_parser.rs        — Filename parsing (existing)
│   └── format/                   — Format handlers (existing)
│       ├── mod.rs
│       ├── cdg.rs
│       ├── kar.rs
│       └── mpg.rs
└── tests/
    └── engine_tests.rs           — Integration tests against Engine trait
```

The existing internal modules (`backend.rs`, `queue.rs`, etc.) remain largely unchanged. The key additions are:
- `engine.rs` — the `Engine` trait
- `event_bus.rs` — the `EventBus` trait  
- `views/` — view model types
- `engine_impl.rs` — adapts existing `Backend` to implement the `Engine` trait
