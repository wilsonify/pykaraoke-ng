# Interface Specification

**Date**: 2026-06-16  
**Status**: Draft — proposed interfaces for the pykaraoke-engine ↔ Tauri boundary  
**Version**: 1  

This document defines every public interface between the Rust engine and the Tauri desktop application. These interfaces form the contract that both sides must implement.

---

## Table of Contents

1. [Engine Trait](#1-engine-trait) — Rust public API
2. [EventBus Trait](#2-eventbus-trait) — Engine → UI notification
3. [Tauri Commands](#3-tauri-commands) — IPC surface for the frontend
4. [View Types](#4-view-types) — Data transfer objects for the frontend
5. [Internal Domain Types](#5-internal-domain-types) — Engine-internal (not exposed)
6. [Error Handling](#6-error-handling)
7. [Enum Reference](#7-enum-reference)
8. [Migration Path](#8-migration-path)

---

## 1. Engine Trait

**File**: `crates/pykaraoke-engine/src/engine.rs`  
**Purpose**: The public API of the karaoke engine. The Tauri shell implements the `EventBus` trait and calls the `Engine` trait. The frontend never sees this trait directly.

```rust
/// The public interface of the pykaraoke engine.
/// Every method is synchronous (no async) — the Tauri shell wraps these in
/// async commands.  All methods return Result with a domain-specific error type.
///
/// Implementations must be Send (for Mutex wrapping in Tauri managed state).
pub trait Engine: Send {
    // ── Lifecycle ──────────────────────────────────────────────

    /// Start the engine. Loads persisted state (settings, database).
    /// Returns an error if already running or if data directory is inaccessible.
    fn start(&mut self) -> Result<(), EngineError>;

    /// Stop the engine. Persists state (settings, database) to disk.
    /// Safe to call multiple times; subsequent calls are no-ops.
    fn stop(&mut self) -> Result<(), EngineError>;

    /// Returns the current engine status without side effects.
    fn status(&self) -> EngineStatus;


    // ── Playback ───────────────────────────────────────────────

    /// Play a song from the queue.  If `song_id` is `None`, resumes playback
    /// or plays the first queued song.  If `song_id` is `Some(id)`, selects
    /// that song in the queue before playing.
    fn play(&mut self, song_id: Option<SongId>) -> Result<PlaybackState, EngineError>;

    /// Toggle pause.  If playing → paused.  If paused → playing.
    /// Returns an error if in any other state (stopped, idle).
    fn pause(&mut self) -> Result<PlaybackState, EngineError>;

    /// Stop playback.  Rewinds to the beginning.
    fn stop_playback(&mut self) -> Result<PlaybackState, EngineError>;

    /// Advance to the next song in the queue.
    /// Returns an error if already at the last song.
    fn next(&mut self) -> Result<PlaybackState, EngineError>;

    /// Go back to the previous song in the queue.
    /// Returns an error if already at the first song.
    fn previous(&mut self) -> Result<PlaybackState, EngineError>;

    /// Seek to a position in the current song, in milliseconds.
    fn seek(&mut self, position_ms: u64) -> Result<PlaybackState, EngineError>;

    /// Set the volume.  `volume` is clamped to [0.0, 1.0].
    fn set_volume(&mut self, volume: f64) -> Result<PlaybackState, EngineError>;


    // ── Queue ──────────────────────────────────────────────────

    /// Add a song to the end of the playback queue by file path.
    /// Parses the filename to extract artist/title.
    fn enqueue(&mut self, filepath: &str) -> Result<QueueView, EngineError>;

    /// Remove a song from the queue by index.
    fn remove_from_queue(&mut self, index: usize) -> Result<QueueView, EngineError>;

    /// Remove all songs from the queue.
    fn clear_queue(&mut self) -> Result<QueueView, EngineError>;

    /// Move a song within the queue (reorder).
    fn move_in_queue(&mut self, from: usize, to: usize) -> Result<QueueView, EngineError>;

    /// Get the current queue state without side effects.
    fn queue(&self) -> QueueView;


    // ── Library ────────────────────────────────────────────────

    /// Scan all configured library folders for karaoke files.
    /// Progress is reported via the EventBus trait.
    fn scan_library(&mut self) -> Result<LibraryScanProgress, EngineError>;

    /// Add a folder to the library scan list.
    fn add_library_folder(&mut self, path: &str) -> Result<(), EngineError>;

    /// Remove a folder from the library scan list.
    fn remove_library_folder(&mut self, path: &str) -> Result<(), EngineError>;

    /// Get the list of configured library folders.
    fn library_folders(&self) -> Vec<String>;


    // ── Search ─────────────────────────────────────────────────

    /// Search the song library.  Empty query returns all songs.
    /// Search is case-insensitive and matches across title, artist, filename.
    fn search(&self, query: &str) -> SearchResultsView;


    // ── Settings ───────────────────────────────────────────────

    /// Get all current settings.
    fn settings(&self) -> SettingsView;

    /// Apply a partial settings update.  Only the fields present in `delta`
    /// are changed; all other fields retain their current values.
    fn update_settings(&mut self, delta: SettingsDelta) -> Result<SettingsView, EngineError>;
}
```

### Contractual Guarantees

| Method | Idempotent | Pure (no side effects) | Thread-safe |
|--------|-----------|----------------------|-------------|
| `start` | Yes (second call returns error) | No | Caller must serialize |
| `stop` | Yes (second call is no-op) | No | Caller must serialize |
| `status` | Yes | Yes | Read-only, safe |
| `play` | No | No | Caller must serialize |
| `pause` | No | No | Caller must serialize |
| `stop_playback` | Yes | No | Caller must serialize |
| `next` | No | No | Caller must serialize |
| `previous` | No | No | Caller must serialize |
| `seek` | No | No | Caller must serialize |
| `set_volume` | Yes | No | Caller must serialize |
| `enqueue` | No | No | Caller must serialize |
| `remove_from_queue` | No | No | Caller must serialize |
| `clear_queue` | Yes | No | Caller must serialize |
| `move_in_queue` | No | No | Caller must serialize |
| `queue` | Yes | Yes | Read-only (snapshot) |
| `scan_library` | No | No | Caller must serialize |
| `add_library_folder` | No | No | Caller must serialize |
| `remove_library_folder` | No | No | Caller must serialize |
| `library_folders` | Yes | Yes | Read-only (snapshot) |
| `search` | Yes | Yes | Read-only (snapshot) |
| `settings` | Yes | Yes | Read-only (snapshot) |
| `update_settings` | Yes (per-field) | No | Caller must serialize |

---

## 2. EventBus Trait

**File**: `crates/pykaraoke-engine/src/event_bus.rs`  
**Purpose**: The mechanism by which the engine pushes state change notifications to the UI layer. The Tauri shell implements this trait and relays events to the frontend via Tauri's event system.

```rust
/// Implemented by the Tauri shell to receive push notifications from the engine.
/// All methods must be non-blocking and return quickly.
pub trait EventBus: Send + Sync {
    /// Called whenever playback state changes (play, pause, stop, seek, song finish).
    fn emit_playback_changed(&self, state: PlaybackState);

    /// Called whenever the queue is modified (enqueue, remove, clear, reorder).
    fn emit_queue_changed(&self, queue: QueueView);

    /// Called whenever the library is modified (scan complete, folder changed).
    fn emit_library_changed(&self, library: LibraryView);

    /// Called whenever settings are updated.
    fn emit_settings_changed(&self, settings: SettingsView);

    /// Called during library scan to report progress.
    fn emit_scan_progress(&self, progress: LibraryScanProgress);

    /// Called when a non-recoverable error occurs.
    fn emit_error(&self, error: EngineErrorInfo);

    /// Called when the CDG renderer produces a new frame.
    fn emit_cdg_frame(&self, frame: CdgFrameView);

    /// Called when the KAR player has new lyric data.
    fn emit_lyrics_changed(&self, lyrics: LyricsView);
}
```

### Event Emission Guarantees

| Event | Frequency | Latency Budget | Droppable? |
|-------|-----------|---------------|------------|
| `playback_changed` | On any state transition | < 5ms | No |
| `queue_changed` | On any queue mutation | < 5ms | No |
| `library_changed` | On scan completion | < 50ms | No |
| `settings_changed` | On settings update | < 5ms | No |
| `scan_progress` | Every ~1% of scan | < 10ms | Yes (throttled) |
| `error` | On error conditions | < 5ms | No |
| `cdg_frame` | ~25 fps (every 40ms) | < 16ms | Yes (frame skip) |
| `lyrics_changed` | On new lyric line | < 5ms | No |

---

## 3. Tauri Commands

**File**: `src/runtimes/tauri/src-tauri/src/commands.rs` (new file; extracted from `main.rs`)  
**Purpose**: Typed IPC surface that the JavaScript frontend calls via `window.__TAURI__.tauri.invoke()`.

Each command is a separate `#[tauri::command]` function. This replaces the single `send_command(action, params)` dispatcher.

```rust
// ── Lifecycle ──────────────────────────────────────────────────────────

#[tauri::command]
fn engine_start(state: State<'_, AppEngine>) -> Result<(), String>;
//   invoke('engine_start') → void
//   Initializes engine, loads persistence.

#[tauri::command]
fn engine_stop(state: State<'_, AppEngine>) -> Result<(), String>;
//   invoke('engine_stop') → void
//   Persists state, shuts down playback.

#[tauri::command]
fn engine_status(state: State<'_, AppEngine>) -> Result<EngineStatus, String>;
//   invoke('engine_status') → EngineStatus
//   Returns "starting" | "running" | "stopped" | "error"


// ── Playback ───────────────────────────────────────────────────────────

#[tauri::command]
fn playback_play(
    state: State<'_, AppEngine>,
    song_id: Option<SongId>,
) -> Result<PlaybackState, String>;
//   invoke('playback_play', { song_id: 42 })
//   invoke('playback_play', {})


#[tauri::command]
fn playback_pause(state: State<'_, AppEngine>) -> Result<PlaybackState, String>;
//   invoke('playback_pause') → PlaybackState

#[tauri::command]
fn playback_stop(state: State<'_, AppEngine>) -> Result<PlaybackState, String>;
//   invoke('playback_stop') → PlaybackState

#[tauri::command]
fn playback_next(state: State<'_, AppEngine>) -> Result<PlaybackState, String>;
//   invoke('playback_next') → PlaybackState

#[tauri::command]
fn playback_previous(state: State<'_, AppEngine>) -> Result<PlaybackState, String>;
//   invoke('playback_previous') → PlaybackState

#[tauri::command]
fn playback_seek(
    state: State<'_, AppEngine>,
    position_ms: u64,
) -> Result<PlaybackState, String>;
//   invoke('playback_seek', { position_ms: 120000 }) → PlaybackState

#[tauri::command]
fn playback_set_volume(
    state: State<'_, AppEngine>,
    volume: f64,
) -> Result<PlaybackState, String>;
//   invoke('playback_set_volume', { volume: 0.75 }) → PlaybackState


// ── Queue ──────────────────────────────────────────────────────────────

#[tauri::command]
fn queue_enqueue(
    state: State<'_, AppEngine>,
    filepath: String,
) -> Result<QueueView, String>;
//   invoke('queue_enqueue', { filepath: "C:\\songs\\test.kar" }) → QueueView

#[tauri::command]
fn queue_remove(
    state: State<'_, AppEngine>,
    index: usize,
) -> Result<QueueView, String>;
//   invoke('queue_remove', { index: 2 }) → QueueView

#[tauri::command]
fn queue_clear(state: State<'_, AppEngine>) -> Result<QueueView, String>;
//   invoke('queue_clear') → QueueView

#[tauri::command]
fn queue_move(
    state: State<'_, AppEngine>,
    from: usize,
    to: usize,
) -> Result<QueueView, String>;
//   invoke('queue_move', { from: 0, to: 3 }) → QueueView

#[tauri::command]
fn queue_list(state: State<'_, AppEngine>) -> Result<QueueView, String>;
//   invoke('queue_list') → QueueView


// ── Library ────────────────────────────────────────────────────────────

#[tauri::command]
fn library_scan(state: State<'_, AppEngine>) -> Result<LibraryScanProgress, String>;
//   invoke('library_scan') → LibraryScanProgress

#[tauri::command]
fn library_add_folder(
    state: State<'_, AppEngine>,
    path: String,
) -> Result<(), String>;
//   invoke('library_add_folder', { path: "C:\\music\\karaoke" }) → void

#[tauri::command]
fn library_remove_folder(
    state: State<'_, AppEngine>,
    path: String,
) -> Result<(), String>;
//   invoke('library_remove_folder', { path: "C:\\music\\karaoke" }) → void

#[tauri::command]
fn library_folders(state: State<'_, AppEngine>) -> Result<Vec<String>, String>;
//   invoke('library_folders') → ["C:\\music\\karaoke"]


// ── Search ─────────────────────────────────────────────────────────────

#[tauri::command]
fn search(
    state: State<'_, AppEngine>,
    query: String,
) -> Result<SearchResultsView, String>;
//   invoke('search', { query: "queen" }) → SearchResultsView
//   invoke('search', { query: "" }) → all songs


// ── Settings ───────────────────────────────────────────────────────────

#[tauri::command]
fn settings_get(state: State<'_, AppEngine>) -> Result<SettingsView, String>;
//   invoke('settings_get') → SettingsView

#[tauri::command]
fn settings_update(
    state: State<'_, AppEngine>,
    delta: SettingsDelta,
) -> Result<SettingsView, String>;
//   invoke('settings_update', { delta: { fullscreen: true } }) → SettingsView
```

### Frontend Call Patterns

Each command maps to a single frontend function. The frontend calls:

```javascript
// All commands follow this pattern:
const state = await invoke('playback_play', { song_id: 42 });
//                        │              │
//                        │              └── parameters (camelCase JSON)
//                        └── command name (kebab-case)

// Error handling — all commands throw on error:
try {
    const view = await invoke('playback_play', {});
} catch (err) {
    console.error('Play failed:', err);
}
```

---

## 4. View Types

**Directory**: `crates/pykaraoke-engine/src/views/`  
**Purpose**: Data transfer objects designed explicitly for frontend consumption. These are NOT the engine's internal domain types. They are versioned, filtered, and stable.

### 4.1 SongView

```rust
/// Lightweight song representation for the frontend.
/// Serialized as JSON for IPC.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SongView {
    /// Schema version (currently 1). Frontend can use this to adapt.
    pub version: u8,

    /// Unique identifier for this song in the current library session.
    pub id: SongId,

    /// Song title (parsed from filename or titles.txt).
    pub title: String,

    /// Artist name (parsed from filename or titles.txt).
    pub artist: String,

    /// Absolute file path.
    pub filepath: String,

    /// Display name — "Artist - Title" if both present, else title only.
    pub display_name: String,

    /// Song duration in seconds (0 if unknown).
    #[serde(default)]
    pub duration_seconds: f64,

    /// Karaoke format.
    pub format: SongFormat,

    /// Disc identifier (for CD+G discs). Empty string if unknown.
    #[serde(default)]
    pub disc: String,

    /// Track number (for CD+G discs). Empty string if unknown.
    #[serde(default)]
    pub track: String,

    /// Filename displayed to the user.
    pub filename: String,
}
```

### 4.2 PlaybackState

```rust
/// Full playback state snapshot for the frontend.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PlaybackState {
    /// Current playback status.
    pub status: PlaybackStatus,

    /// Currently playing song, or None if idle/stopped.
    pub current_song: Option<SongView>,

    /// Current playback position in milliseconds.
    pub position_ms: u64,

    /// Total duration of the current song in milliseconds (0 if unknown).
    pub duration_ms: u64,

    /// Current volume (0.0 – 1.0).
    pub volume: f64,
}
```

### 4.3 QueueView

```rust
/// Queue/playlist state snapshot for the frontend.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct QueueView {
    /// Ordered list of songs in the queue.
    pub songs: Vec<SongView>,

    /// Index of the currently playing song in the songs vec.
    /// None if nothing is selected.
    pub current_index: Option<usize>,

    /// Total duration of all songs in the queue (seconds).
    pub total_duration_seconds: f64,
}
```

### 4.4 SearchResultsView

```rust
/// Search results for the frontend.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SearchResultsView {
    /// The search query.
    pub query: String,

    /// Matching songs.
    pub results: Vec<SongView>,

    /// Total number of matching songs (may be > results.len() if paginated).
    pub total_count: usize,
}
```

### 4.5 SettingsView

```rust
/// All user-configurable settings, presented to the frontend.
/// Grouped by category for clarity.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SettingsView {
    /// Schema version (currently 1).
    pub version: u8,

    /// Display settings.
    pub display: DisplaySettings,

    /// Audio settings.
    pub audio: AudioSettings,

    /// Lyrics display settings.
    pub lyrics: LyricsSettings,

    /// Library folders.
    pub library_folders: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DisplaySettings {
    pub fullscreen: bool,
    pub width: u32,
    pub height: u32,
    pub always_on_top: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AudioSettings {
    pub volume: f64,         // 0.0 – 1.0
    pub sync_delay_ms: i64,  // Lyric sync adjustment
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LyricsSettings {
    pub show: bool,
    pub font_size: u32,
    pub font_bold: bool,
    pub font_italic: bool,
    pub color: String,              // Hex e.g. "#FF0000"
    pub outline_color: String,      // Hex e.g. "#000000"
    pub sweep_color: String,        // Hex e.g. "#FFFFFF"
}

/// Partial settings update. Only Some(fields) are applied; None fields are ignored.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SettingsDelta {
    pub fullscreen: Option<bool>,
    pub width: Option<u32>,
    pub height: Option<u32>,
    pub always_on_top: Option<bool>,
    pub volume: Option<f64>,
    pub sync_delay_ms: Option<i64>,
    pub show_lyrics: Option<bool>,
    pub font_size: Option<u32>,
    pub font_bold: Option<bool>,
    pub font_italic: Option<bool>,
    pub lyrics_color: Option<String>,
    pub lyrics_outline_color: Option<String>,
    pub lyrics_sweep_color: Option<String>,
}
```

### 4.6 LibraryView

```rust
/// Library state snapshot for the frontend.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LibraryView {
    pub song_count: usize,
    pub folder_count: usize,
}
```

### 4.7 LibraryScanProgress

```rust
/// Progress of an ongoing library scan.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LibraryScanProgress {
    pub status: ScanStatus,   // "scanning" | "complete" | "error"
    pub folders_scanned: u32,
    pub songs_found: u32,
    pub errors: Vec<String>,  // Non-fatal scan errors
    pub percent: u8,          // 0-100
}
```

### 4.8 CdgFrameView

```rust
/// A single CDG frame for canvas rendering in the frontend.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CdgFrameView {
    /// RGBA pixel data, row-major, 300×216 = 259,200 bytes.
    pub pixels: Vec<u8>,

    /// Width in pixels (always 300 for full frame, may be less for zoom).
    pub width: u16,

    /// Height in pixels (always 216 for full frame, may be less for zoom).
    pub height: u16,

    /// Timestamp in ms (for synchronization with audio).
    pub timestamp_ms: u64,
}
```

### 4.9 LyricsView

```rust
/// Current lyric line for KAR/MIDI playback.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LyricsView {
    pub current_line: String,
    pub next_line: String,
    pub current_line_progress: f64,  // 0.0 – 1.0 (for colour sweep)
    pub lines: Vec<LyricLine>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LyricLine {
    pub text: String,
    pub start_ms: u64,
    pub duration_ms: u64,
}
```

### 4.10 EngineErrorInfo

```rust
/// Structured error information sent to the frontend via events.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct EngineErrorInfo {
    pub code: ErrorCode,
    pub message: String,
    pub details: Option<String>,
    pub recoverable: bool,
}
```

---

## 5. Internal Domain Types

These types exist **inside the engine crate** and are **not exposed** to the frontend or the Tauri shell. They are part of the implementation, not the interface.

```rust
// NOT exported from lib.rs — implementation detail

pub(crate) struct Backend {
    pub(crate) state: BackendState,
    pub(crate) queue: Queue,
    pub(crate) library: Library,
    pub(crate) persistence: Persistence,
    pub(crate) volume: f64,
    pub(crate) current_time_ms: u64,
}

pub(crate) struct Queue {
    pub(crate) playlist: Vec<SongStruct>,
    pub(crate) playlist_index: Option<usize>,
    pub(crate) current_song: Option<SongStruct>,
}

pub(crate) struct SongStruct {
    pub(crate) display_filename: String,
    pub(crate) filepath: String,
    pub(crate) zip_stored_name: Option<String>,
    pub(crate) title: String,
    pub(crate) artist: String,
    pub(crate) disc: String,
    pub(crate) track: String,
    pub(crate) extension: String,
    pub(crate) audio_filepath: Option<String>,
    pub(crate) length: f64,
    pub(crate) file_hash: Option<String>,
}

pub(crate) struct Settings {
    // 26 fields — see database.rs
}

pub(crate) struct Player {
    pub(crate) state: PlayerState,
    pub(crate) timing: PlaybackTiming,
    // ...
}

pub(crate) enum BackendState {
    Idle, Playing, Paused, Stopped, Loading, Error,
}

pub(crate) enum PlayerState {
    Init, Playing, Paused, NotPlaying, Closing, Closed, Capturing,
}
```

The migration path is:
1. Add `pub(crate)` visibility restrictions on existing public types
2. Create view types in `views/` as the new external interface
3. Keep internal types for engine implementation

---

## 6. Error Handling

### 6.1 EngineError

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EngineError {
    #[serde(rename = "not_started")]
    NotStarted,

    #[serde(rename = "already_started")]
    AlreadyStarted,

    #[serde(rename = "io_error")]
    Io { message: String },

    #[serde(rename = "invalid_file")]
    InvalidFile { path: String, message: String },

    #[serde(rename = "playback_error")]
    Playback { message: String },

    #[serde(rename = "queue_error")]
    Queue { message: String },

    #[serde(rename = "settings_error")]
    Settings { message: String },

    #[serde(rename = "internal")]
    Internal { message: String },
}
```

### 6.2 Error Code Enum

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ErrorCode {
    IoError,
    FileNotFound,
    InvalidFileFormat,
    PlaybackFailed,
    QueueEmpty,
    QueueIndexOutOfRange,
    SettingsValidationFailed,
    BackendNotRunning,
    BackendAlreadyRunning,
    InternalError,
}
```

---

## 7. Enum Reference

### 7.1 EngineStatus

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EngineStatus {
    Starting,
    Running,
    Stopped,
    Error,
}
```

### 7.2 PlaybackStatus

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PlaybackStatus {
    Idle,
    Playing,
    Paused,
    Stopped,
    Loading,
}
```

### 7.3 SongFormat

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SongFormat {
    Cdg,
    Kar,
    Mpeg,
    Unknown,
}
```

### 7.4 ScanStatus

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ScanStatus {
    Scanning,
    Complete,
    Error,
}
```

### 7.5 SongId

```rust
/// Opaque song identifier.  Frontend receives this from SongView and passes
/// it back to identify songs.  Internally, it may be a hash of the filepath
/// or a sequential index.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SongId(pub u64);
```

---

## 8. Migration Path

### Phase 1: Interface Extraction (Week 1)

| Step | Change | Files affected | Risk |
|------|--------|----------------|------|
| 1 | Create `views/` module with all view types | New files in engine crate | Low |
| 2 | Create `engine.rs` with `Engine` trait | New file in engine crate | Low |
| 3 | Create `event_bus.rs` with `EventBus` trait | New file in engine crate | Low |
| 4 | Make existing `Backend` fields `pub(crate)` instead of `pub` | `backend.rs` | Low |
| 5 | Make existing `SongStruct` fields `pub(crate)` | `song.rs` | Low |
| 6 | Add `Engine` trait impl that wraps `Backend` | `engine_impl.rs` | Low |
| 7 | Remove `CommandRequest`/`CommandResponse` from public API | `backend.rs` | Medium — existing consumers |

### Phase 2: Tauri Shell Refactor (Week 2)

| Step | Change | Files affected | Risk |
|------|--------|----------------|------|
| 8 | Create `commands.rs` with typed commands | New file in Tauri src | Low |
| 9 | Replace `send_command` in `main.rs` with individual command calls | `main.rs` | Medium |
| 10 | Implement `EventBus` trait for Tauri event emission | New file in Tauri src | Low |
| 11 | Wire `EventBus` into `Engine` impl | `main.rs` | Low |
| 12 | Remove `CommandResponseWrapper` (no longer needed) | `main.rs` | Low |
| 13 | Update `app.js` — replace `sendCommand(action, params)` with direct `invoke('playback_play', ...)` | `app.js` | Medium |
| 14 | Remove polling interval; add `listen()` for events | `app.js` | Medium |
| 15 | Move frontend business logic (debounce, timers) to engine | `app.js` → engine | Low |

### Phase 3: Test Updates (Week 2-3)

| Step | Change | Risk |
|------|--------|------|
| 16 | Update engine unit tests to use `Engine` trait | Low |
| 17 | Create mock `Engine` for Tauri shell tests | Low |
| 18 | Update `app.test.js` — command names changed, no more polling | Low |
| 19 | Update validation tests (`test_artifact_backend.py`) — new command protocol | Medium |
| 20 | Verify compat tests still pass against new interface | Low |
