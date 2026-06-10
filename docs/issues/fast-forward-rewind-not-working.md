# Fast Forward / Rewind Does Nothing

| Field | Value |
|-------|-------|
| **Reported** | 2026-06-09 |
| **Affected version** | 0.7.5 |
| **Platform** | All (Tauri desktop app) |
| **Status** | Fixed |

---

## Symptom

After queueing a song and starting playback, clicking the Fast Forward (or
Rewind) button has no effect. The progress bar does not move and the song
continues playing at normal speed regardless of how many times the user
clicks or holds the button.

## Root Cause

Fast Forward and Rewind were **never implemented** in PyKaraoke-NG. Three
layers were missing:

### 1. No UI buttons

`src/runtimes/tauri/src/index.html` only defined transport buttons for
Previous (⏮), Play (▶️), Pause (⏸), Stop (⏹), and Next (⏭). There were
no ⏪ (Rewind) or ⏩ (Fast Forward) buttons.

### 2. No frontend event handlers

`src/runtimes/tauri/src/app.js` had no event listeners for Fast Forward
or Rewind. No `mousedown`/`mouseup`/`click` handlers existed for these
actions.

### 3. No backend commands

`src/pykaraoke/core/backend.py` had no `fast_forward` or `rewind` entries
in the `_command_handlers` dispatch table, so even if the frontend sent
such commands, the backend would return `{"status": "error", "message":
"Unknown action: fast_forward"}`.

### 4. No player seek-increment support

The base `PykPlayer` class and all format-specific players (`MidPlayer`,
`CdgPlayer`, `MpgPlayer`) supported absolute seeking via `seek(position_ms)`,
but there was no method for incremental seeking (e.g., "skip forward 10
seconds").

## Fix

Four files were changed to implement Fast Forward and Rewind:

| File | Changes |
|------|---------|
| `src/pykaraoke/core/backend.py` | Added `_handle_fast_forward` and `_handle_rewind` handlers; registered them in `_command_handlers` dispatch table |
| `src/runtimes/tauri/src/index.html` | Added `#rewind-btn` and `#ff-btn` buttons to the player controls row |
| `src/runtimes/tauri/src/app.js` | Added `_setupSeekButton()` method; wired FF/RW buttons with `mousedown`/`mouseup`/`mouseleave` for single-click step and continuous hold-to-repeat |
| `tests/pykaraoke/core/test_backend_progress.py` | Added `TestFastForwardRewind` class with 14 regression tests |

### Backend design

The `_handle_fast_forward` and `_handle_rewind` methods work by:

1. Accepting an optional `amount_seconds` parameter (default: 10 seconds,
   minimum: 1 second)
2. Computing the new position: `current + increment` (FF) or
   `current - increment` (RW)
3. Clamping to valid range `[0, duration_ms]`
4. Delegating to the existing `_handle_seek` method which handles the
   player `seek()` call and state-change event emission

This approach works around the limitation that `pygame.mixer.music` cannot
change playback rate — instead of speeding up audio, we periodically
re-seek to an advanced position.

### Frontend design

The `_setupSeekButton()` helper uses `mousedown` to start seeking and
`mouseup`/`mouseleave` to stop:

1. **Single click:** `mousedown` fires `doSeek()` immediately, seeking by
   the configured step (10 seconds)
2. **Hold:** After the initial seek, a 500ms interval repeatedly calls
   `doSeek()` for continuous seeking while the button is held
3. The `click` event is suppressed with `preventDefault()` to avoid
   double-firing

## How to verify

```bash
# Unit tests
cd /path/to/pykaraoke-ng
.venv313/Scripts/python -m pytest tests/pykaraoke/core/test_backend_progress.py -v

# Build Tauri desktop app
cd src/runtimes/tauri
npx tauri build

# Install and test the packaged app:
# 1. Queue a song
# 2. Start playback
# 3. Click ⏩ (Fast Forward) → song advances ~10 seconds
# 4. Click ⏪ (Rewind) → song goes back ~10 seconds
# 5. Hold ⏩ → song continuously fast-forwards every 500ms
# 6. Release → seeking stops
# 7. Hold ⏪ → song continuously rewinds every 500ms
# 8. Verify position never drops below 0 or exceeds duration
```

## Test coverage

14 new tests in `TestFastForwardRewind`:

| Test | What it verifies |
|------|------------------|
| `test_fast_forward_calls_seek_with_increased_position` | FF seeks forward by default 10s |
| `test_fast_forward_custom_increment` | FF respects `amount_seconds: 5` |
| `test_fast_forward_clamps_to_duration` | FF does not exceed song duration |
| `test_rewind_calls_seek_with_decreased_position` | RW seeks backward by default 10s |
| `test_rewind_custom_increment` | RW respects `amount_seconds: 5` |
| `test_rewind_clamps_to_zero` | RW does not go below position 0 |
| `test_fast_forward_without_player_does_not_crash` | Graceful when no player active |
| `test_rewind_without_player_does_not_crash` | Graceful when no player active |
| `test_fast_forward_emits_state_change` | FF emits state_changed event |
| `test_fast_forward_custom_30s` | FF supports 30-second increment |
| `test_rewind_custom_30s` | RW supports 30-second decrement |
| `test_command_dispatch_has_fast_forward` | Dispatch table has `fast_forward` key |
| `test_command_dispatch_has_rewind` | Dispatch table has `rewind` key |
| `test_fast_forward_handles_player_seek_error` | FF handles player.seek() exception |
| `test_rewind_handles_player_seek_error` | RW handles player.seek() exception |
| `test_fast_forward_minimum_amount_is_one_second` | FF floor-clamps to 1s |
| `test_rewind_minimum_amount_is_one_second` | RW floor-clamps to 1s |

All 757 tests pass (37 skipped due to environment constraints).
