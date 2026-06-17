# Migration Recommendations

**Date**: 2026-06-16  
**Scope**: Incremental migration from the current `send_command(action, params)` architecture to the typed interface architecture defined in `INTERFACE_SPEC.md`

---

## 1. Current State Summary

The engine already exists and works. The problem is that its **public interface is the implementation** — every internal struct (`SongStruct`, `Settings`, `BackendFullState`) is serialized directly to the frontend. The single `send_command` dispatcher means action strings are a protocol leak.

### What needs to change

| Current | Target | Reason |
|---------|--------|--------|
| Single `send_command(action, params)` | Typed `#[tauri::command]` per capability | Type safety, discoverability, no magic strings |
| `Backend` struct is the public API | `Engine` trait is the public API | Hides implementation, enables mocking |
| Internal types = IPC schema (`SongStruct`, `Settings`, etc.) | View types (`SongView`, `SettingsView`, etc.) are the IPC schema | Schema evolves independently of internals |
| Frontend polls `get_state` every 1s | Backend emits events via `EventBus` → Tauri events | Lower latency, fewer IPC calls |
| Tauri shell manages `Persistence` lifecycle | Engine manages its own persistence | Clear ownership boundary |
| Engine types are `pub` (all fields exposed) | Engine types are `pub(crate)` | Implementation hiding |
| Backend event system exists but unused (`BackendEvent`) | `EventBus` trait actively wired to Tauri | Event-driven architecture |

---

## 2. Recommended Migration Order

### Step 1: Define View Types (Low risk, 1 day)

Create the `views/` module with all view types. These are new files; nothing else changes.

```
crates/pykaraoke-engine/src/views/
├── mod.rs
├── song_view.rs
├── playback_view.rs
├── queue_view.rs
├── library_view.rs
├── search_view.rs
├── settings_view.rs
├── cdg_frame_view.rs
├── lyrics_view.rs
└── error_view.rs
```

**Action**: Write all view types as defined in INTERFACE_SPEC §4. Add `Serialize`/`Deserialize` derives. No other code changes.

**Test**: Write unit tests that construct each view and serialize to JSON. Verify field names use `camelCase`.

---

### Step 2: Define Engine and EventBus Traits (Low risk, 1 day)

Create `engine.rs` and `event_bus.rs` in the engine crate. These are trait definitions only — no implementation yet.

**Action**:
1. Write `Engine` trait in `engine.rs` (from INTERFACE_SPEC §1)
2. Write `EventBus` trait in `event_bus.rs` (from INTERFACE_SPEC §2)
3. Export both from `lib.rs`

**Test**: Compile check only. No runtime tests needed for trait definitions.

---

### Step 3: Add EngineImpl (Low risk, 2 days)

Create `engine_impl.rs` that wraps the existing `Backend` struct and implements the `Engine` trait.

**Action**:
1. Create `EngineImpl` struct holding `Backend` and `Box<dyn EventBus>`
2. Implement each `Engine` method by delegating to `Backend.handle_command()` internally
3. Construct view types from internal domain types in each method
4. Call `event_bus.emit_*()` after state changes

```rust
pub struct EngineImpl {
    backend: Backend,
    event_bus: Box<dyn EventBus>,
    started: bool,
}

impl Engine for EngineImpl {
    fn play(&mut self, song_id: Option<SongId>) -> Result<PlaybackState, EngineError> {
        // Validate engine is started
        if !self.started {
            return Err(EngineError::NotStarted);
        }
        
        // Build internal command
        let params = match song_id {
            Some(id) => json!({"playlist_index": id.0 as u64}),
            None => Value::Null,
        };
        
        // Delegate to existing Backend
        let response = self.backend.handle_command(CommandRequest {
            action: "play".to_string(),
            params,
        });
        
        // Map response to view type
        match response.status.as_str() {
            "ok" => {
                let state = self.build_playback_state();
                self.event_bus.emit_playback_changed(state.clone());
                Ok(state)
            }
            "error" => Err(EngineError::Playback {
                message: response.message.unwrap_or_default(),
            }),
            _ => Err(EngineError::Internal {
                message: "Unexpected response status".to_string(),
            }),
        }
    }
    
    // ... remaining methods follow same pattern
}
```

**Test**: Write integration tests that create `EngineImpl` with a `MockEventBus` and verify:
- Each command returns the correct view type
- Events are emitted on state changes
- Read-only methods (search, settings) do NOT emit events
- Error conditions return `Err(EngineError)`

---

### Step 4: Restrict Internal Type Visibility (Medium risk, 1 day)

Change existing `pub` fields and types to `pub(crate)` so they are no longer part of the public API.

**Action**: For each module, audit what can be restricted:

| Module | Current visibility | Target visibility | Impact |
|--------|------------------|-------------------|--------|
| `song::SongStruct` | `pub struct` + all fields `pub` | `pub(crate)` | CLI binary needs it → keep pub for now, or add adapter |
| `song::SupportedExtensions` | `pub struct` + all fields `pub` | `pub(crate)` | Only used internally |
| `song::TitleStruct` | `pub struct` + fields `pub` | `pub(crate)` | Only used internally |
| `song::SongData` | `pub struct` + fields `pub` | `pub(crate)` | Only used internally |
| `backend::Backend` | `pub struct` + fields `pub` | `pub(crate)` | EngineImpl wraps it, no external access needed |
| `backend::CommandRequest` | `pub struct` + fields `pub` | Keep `pub` for now | CLI binary and compat tests use it |
| `backend::CommandResponse` | `pub struct` + fields `pub` | Keep `pub` for now | CLI binary and compat tests use it |
| `backend::BackendEvent` | `pub enum` | `pub(crate)` | Replaced by EventBus trait |
| `backend::BackendFullState` | `pub struct` + fields `pub` | `pub(crate)` | Replaced by PlaybackState view |
| `player::PlayerState` | `pub enum` | `pub(crate)` | Internal implementation detail |
| `player::PlaybackTiming` | `pub struct` + fields `pub` | `pub(crate)` | Internal implementation detail |
| `player::Player` | `pub struct` + fields `pub` | `pub(crate)` | Internal implementation detail |
| `queue::QueueEvent` | `pub enum` | `pub(crate)` | Replaced by EventBus trait |
| `queue::PlaylistUpdatedData` | `pub struct` | `pub(crate)` | Replaced by QueueView |
| `library::Library` | `pub struct` + fields `pub` | `pub(crate)` | Internal implementation detail |
| `database::Settings` | `pub struct` + fields `pub` | `pub(crate)` | Replaced by SettingsView |
| `database::Database` | `pub struct` + fields `pub` | `pub(crate)` | Internal implementation detail |

**Important**: Keep `CommandRequest`/`CommandResponse` public for now because:
1. The CLI binary (`pykaraoke-engine-cli.rs`) uses them directly
2. The Python compat test suite calls the CLI binary with JSON commands
3. These can be restricted later when the compat tests are updated

---

### Step 5: Refactor Tauri Shell (Medium risk, 2-3 days)

Extract typed commands from `main.rs` into a new `commands.rs` module.

**Action**:
1. Create `src/runtimes/tauri/src-tauri/src/commands.rs`
2. Move each command into its own function with proper typing
3. Replace `AppBackend { backend: Mutex<Option<Backend>> }` with `AppEngine { engine: Mutex<Option<EngineImpl>> }`
4. Wire up `TauriEventBus` that implements `EventBus` using `app_handle.emit_all()`
5. Remove `send_command`, `start_backend`, `stop_backend` from `main.rs`
6. Remove `CommandResponseWrapper` struct

**TauriEventBus implementation**:

```rust
struct TauriEventBus {
    app_handle: Mutex<tauri::AppHandle>,
}

impl EventBus for TauriEventBus {
    fn emit_playback_changed(&self, state: PlaybackState) {
        let handle = self.app_handle.lock().unwrap();
        handle.emit_all("engine:playback_changed", state).ok();
    }
    // ... other events
}
```

**Test**:
- Create mock `AppHandle` and `TauriEventBus` unit tests
- Verify each command produces correct output
- Verify events are emitted with correct payloads

---

### Step 6: Update Frontend IPC Calls (Medium risk, 2-3 days)

Update `app.js` to use the new typed commands and event system.

**Action**:
1. Replace `sendCommand(action, params)` helper with individual function calls
2. Add `listen()` handlers for all engine events
3. Remove polling interval (`setInterval` for `get_state`)
4. Replace all `invoke('send_command', { action: 'play', params: {...} })` with `invoke('playback_play', {...})`

**Before**:
```javascript
async sendCommand(action, params) {
    return invoke('send_command', { action, params: params || {} });
}

// Play button click
await this.sendCommand('play', { playlist_index: 2 });

// State polling
setInterval(async () => {
    let r = await this.sendCommand('get_state');
    if (r.status === 'ok') this.updateUIFromState(r.data);
}, 1000);
```

**After**:
```javascript
// No more sendCommand helper

// Play button click
let state = await invoke('playback_play', { song_id: 42 });

// Event-driven state updates
await listen('engine:playback_changed', (event) => {
    this.updateUIFromState(event.payload);
});
```

**Test**: Update `app.test.js` mocks to return new command shapes. Verify event handlers update UI correctly. Remove polling tests.

---

### Step 7: Remove the Old send_command Backend Handler (High risk, 1 day)

After the frontend is fully migrated to typed commands, remove the `send_command` handler from `backend.rs`.

**Action**:
1. Remove `Backend::handle_command()` and all private `handle_*` methods
2. Keep the internal methods that `EngineImpl` delegates to (or refactor them into the `EngineImpl`)
3. Remove `CommandRequest`/`CommandResponse` if no longer used by CLI or compat tests

**Wait conditions**:
- Frontend sends zero calls to `send_command`
- CLI binary has been updated to use new command format
- Compat tests have been updated

---

## 3. Concrete Interface Changes (Before/After)

### 3.1 Tauri Shell State Management

**Before** (`main.rs`):
```rust
struct AppBackend {
    backend: Mutex<Option<Backend>>,  // Direct engine reference
}

fn main() {
    tauri::Builder::default()
        .manage(AppBackend { backend: Mutex::new(None) })
        .invoke_handler(tauri::generate_handler![
            start_backend,
            send_command,
            stop_backend,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

**After** (`main.rs`):
```rust
struct AppEngine {
    engine: Mutex<Option<EngineImpl>>,  // Wrapped behind Engine trait
}

fn main() {
    tauri::Builder::default()
        .manage(AppEngine { engine: Mutex::new(None) })
        .invoke_handler(tauri::generate_handler![
            engine_start,
            engine_stop,
            engine_status,
            playback_play,
            playback_pause,
            playback_stop,
            playback_next,
            playback_previous,
            playback_seek,
            playback_set_volume,
            queue_enqueue,
            queue_remove,
            queue_clear,
            queue_move,
            queue_list,
            library_scan,
            library_add_folder,
            library_remove_folder,
            library_folders,
            search,
            settings_get,
            settings_update,
        ])
        .setup(|app| {
            // Create TauriEventBus with AppHandle
            let event_bus = TauriEventBus::new(app.handle());
            app.manage(Mutex::new(event_bus));
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### 3.2 Frontend IPC

**Before** (`app.js`):
```javascript
async sendCommand(action, params) {
    if (!globalThis.__TAURI__?.tauri?.invoke) {
        throw new Error('Tauri bridge unavailable');
    }
    return invoke('send_command', {
        action: action,
        params: params || {},
    });
}

// Usage: this.sendCommand('play', { playlist_index: 2 })
//        this.sendCommand('get_state', {})
//        this.sendCommand('search_songs', { query: 'queen' })
```

**After** (`app.js`):
```javascript
// No generic sendCommand — each command is explicit

async play(songId) {
    return invoke('playback_play', { song_id: songId });
}

async pause() {
    return invoke('playback_pause');
}

async search(query) {
    return invoke('search', { query });
}

// ... one function per command
```

### 3.3 State Updates

**Before** (`app.js`):
```javascript
// In constructor:
this.startStatePolling();

startStatePolling() {
    setInterval(async () => {
        try {
            let r = await this.sendCommand('get_state');
            if (r.status === 'ok' && r.data) {
                this.updateUIFromState(r.data);
            }
        } catch (e) {
            console.error('State polling error:', e);
        }
    }, 1000);
}
```

**After** (`app.js`):
```javascript
// In constructor:
this.setupEventListeners();

setupEventListeners() {
    listen('engine:playback_changed', (event) => {
        this.updateUIFromState(event.payload);
    });
    listen('engine:queue_changed', (event) => {
        this.renderPlaylist(event.payload);
    });
    listen('engine:error', (event) => {
        this.updateStatus('Error: ' + event.payload.message);
    });
    // ... other event listeners
}
```

---

## 4. Testing Strategy

### 4.1 Engine Tests (Rust unit tests)

```rust
// Tests against Engine trait — not Backend directly
#[cfg(test)]
mod engine_tests {
    use super::*;
    
    struct MockEventBus;
    impl EventBus for MockEventBus {
        fn emit_playback_changed(&self, _: PlaybackState) {
            // Record call for assertion
        }
        // ... other methods
    }
    
    fn create_test_engine() -> EngineImpl {
        let dir = std::env::temp_dir().join("pykaraoke_test_engine");
        let _ = std::fs::remove_dir_all(&dir);
        let persistence = Persistence::new(Some(dir));
        let backend = Backend::new(persistence);
        EngineImpl::new(backend, Box::new(MockEventBus))
    }
    
    #[test]
    fn play_returns_playing_state() {
        let mut engine = create_test_engine();
        engine.start().unwrap();
        engine.enqueue("/tmp/test.kar").unwrap();
        let state = engine.play(None).unwrap();
        assert_eq!(state.status, PlaybackStatus::Playing);
    }
    
    #[test]
    fn play_emits_event() {
        // Arrange
        let event_bus = MockEventBus::new();
        let mut engine = create_test_engine_with(event_bus.clone());
        engine.start().unwrap();
        engine.enqueue("/tmp/test.kar").unwrap();
        
        // Act
        let _ = engine.play(None);
        
        // Assert
        assert!(event_bus.playback_changed_called());
    }
    
    #[test]
    fn search_does_not_emit_event() {
        let event_bus = MockEventBus::new();
        let mut engine = create_test_engine_with(event_bus.clone());
        engine.start().unwrap();
        
        let _ = engine.search("queen");
        
        // Read-only — no events
        assert!(!event_bus.any_event_called());
    }
}
```

### 4.2 Tauri Shell Tests (integration with mock engine)

```rust
// Test against Tauri commands with mock engine
#[cfg(test)]
mod command_tests {
    use super::*;
    
    struct MockEngine;
    impl Engine for MockEngine {
        fn play(&mut self, _: Option<SongId>) -> Result<PlaybackState, EngineError> {
            Ok(PlaybackState {
                status: PlaybackStatus::Playing,
                current_song: Some(SongView {
                    id: SongId(1),
                    title: "Test Song".into(),
                    artist: "Test Artist".into(),
                    filepath: "/tmp/test.kar".into(),
                    display_name: "Test Artist - Test Song".into(),
                    duration_seconds: 180.0,
                    format: SongFormat::Kar,
                    disc: String::new(),
                    track: String::new(),
                    filename: "test.kar".into(),
                    version: 1,
                }),
                position_ms: 0,
                duration_ms: 180000,
                volume: 0.8,
            })
        }
        // ... other methods
    }
    
    #[test]
    fn playback_play_command_returns_state() {
        let app = tauri::test::mock_builder()
            .manage(Mutex::new(MockEngine))
            .invoke_handler(tauri::generate_handler![playback_play])
            .build();
        
        let result = tauri::test::call_command::<PlaybackState>(
            &app,
            "playback_play",
            serde_json::json!({"song_id": null}),
        ).unwrap();
        
        assert_eq!(result.status, PlaybackStatus::Playing);
    }
}
```

### 4.3 Frontend Tests (with mocked Tauri IPC)

```javascript
// app.test.js — mock the typed commands
const mockInvoke = async (cmd, args) => {
    const handlers = {
        'playback_play': () => ({
            status: 'playing',
            currentSong: { title: 'Test Song', artist: 'Test Artist' },
            positionMs: 0,
            durationMs: 180000,
            volume: 0.8,
        }),
        'search': () => ({
            query: 'queen',
            results: [],
            totalCount: 0,
        }),
    };
    
    if (handlers[cmd]) {
        return handlers[cmd]();
    }
    throw new Error(`Unknown command: ${cmd}`);
};

// Set up mock Tauri API
globalThis.__TAURI__ = {
    tauri: { invoke: mockInvoke },
    event: {
        listen: (event, callback) => {
            // Store callback for later triggering in tests
            eventHandlers[event] = callback;
            return () => {}; // unlisten
        },
    },
};
```

---

## 5. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Breaking existing frontend** while refactoring IPC | High | High | Add new commands alongside old `send_command` during transition; remove old only when frontend fully migrated |
| **BackendEvent → EventBus trait misses** some events | Low | Medium | Both systems can coexist; route all current `BackendEvent` variants through `EventBus` |
| **View types serialize differently** than current `SongStruct` JSON | Medium | Medium | Write explicit JSON roundtrip tests comparing old vs new serialization for the same data |
| **Performance regression** from view type construction | Low | Low | View construction is O(1) field-by-field copy; measure and optimize only if needed |
| **CLI binary breaks** when internal types become `pub(crate)` | Medium | Medium | Keep CLI binary working by moving it into the engine crate or providing a compatibility module |
| **Mock engine diverges** from real engine behavior | Medium | Low | Run integration tests with real engine alongside mock-based unit tests; use contract tests |

---

## 6. Migration Schedule

| Week | Phase | Deliverable | Dependencies |
|------|-------|-------------|-------------|
| 1 | **Interface Design** | `views/`, `engine.rs`, `event_bus.rs` completed and reviewed | None |
| 2 | **Engine Trait Impl** | `EngineImpl` + unit tests; `Backend` visibility changes | Week 1 |
| 3 | **Tauri Shell Refactor** | `commands.rs`, `TauriEventBus`, typed IPC commands, remove old dispatcher | Week 2 |
| 4 | **Frontend Migration** | JS updated to typed commands, event listeners; polling removed | Week 3 |
| 5 | **Cleanup & Testing** | Remove old `send_command`, `BackendEvent`, `CommandResponseWrapper`; update all tests; compat suite passes | Week 4 |
| 5+ | **Future Work** | CDG decoder, KAR parser, rodio audio - all use Engine trait from day one | Week 5 |

**Total**: 5 weeks for the complete interface migration. After this, all future engine work (CDG, KAR, MPEG, audio) naturally uses the clean interface.

---

## 7. Migration Checkpoints

At each checkpoint, the application must still build and all existing tests must pass.

**Checkpoint 1** (end of Week 1):
- New view types exist and serialize correctly
- Engine and EventBus traits are defined
- Existing Backend is unchanged — `send_command` still works
- **Cargo test: 126+ tests pass**

**Checkpoint 2** (end of Week 2):
- `EngineImpl` wraps Backend, implements Engine trait
- Internal types restricted to `pub(crate)` where possible
- Old `send_command` still functional for backward compat
- **Cargo test: 130+ tests pass** (new Engine tests)

**Checkpoint 3** (end of Week 3):
- Tauri shell uses typed commands
- TauriEventBus emits events for all state changes
- Old `send_command` can be removed
- **Cargo test: all pass; CLI binary functional**

**Checkpoint 4** (end of Week 4):
- Frontend uses typed invoke() calls
- Frontend listens for events instead of polling
- `send_command` removed from backend
- All compat tests updated
- **Full test suite: Rust + JS + Python compat all pass**

**Final** (end of Week 5):
- All deprecated code removed
- Documentation updated (ARCHITECTURE.md, INTERFACE_SPEC.md are source of truth)
- Clean architecture is validated: frontend dev and backend dev can work independently
