# Playback Controls Not Working (Seek, Progress, Queue, Stop)

| Field | Value |
|-------|-------|
| **Reported** | 2026-06-04 |
| **Affected version** | v0.7.5 |
| **Platform** | Windows 10+, Tauri desktop |
| **Status** | Fixed |

---

## Symptom

After launching the application and double-clicking a `.kar` song to queue
it, then clicking Play, four things go wrong:

1. **Double-click adds 3 queue entries** instead of 1.
2. **Progress bar shows 91 %** immediately, even at the start of a song.
3. **Dragging the progress slider does nothing** — position never changes.
4. **Stop throws a Python traceback** (though the song does stop).

The backend traceback on stop is:

```
NameError: name 'STATE_CAPTURING' is not defined. Did you mean: 'STATE_CLOSING'?
  File "pykaraoke/core/backend.py", line 563, in poll
  File "pykaraoke/core/manager.py", line 420, in poll
  File "pykaraoke/players/kar.py", line 1337, in do_stuff
```

## Root Cause

Four independent bugs combined to produce the observed behaviour.

### 1. Double-click fires `enqueue()` three times

In `app.js`, the search-results rendering attached **both** a `click` and
a `dblclick` event listener to each `.song-item`, and both called the
`enqueue()` wrapper.  When the user double-clicks, the browser fires:

```
click → click → dblclick
```

Each event calls `enqueue()`, so the song is added to the queue **3 times**.

**Fix:** Replace the bare `click` listener with a 250 ms timer pattern.
The first `click` starts a timer; the second `click` (part of the
double-click) cancels the timer.  The `dblclick` handler then fires
exactly once (after also clearing any pending timer).  Single-click
still works — the timer fires 250 ms after the last click.

### 2. `_start_playback()` does not reset `position_ms` / `duration_ms`

When the backend's `_start_playback()` creates a new player and starts
playback, it never touches `self.position_ms` or `self.duration_ms`.
These fields retain the stale values from the **previous** song.  The
frontend renders whatever ratio `position_ms / duration_ms` gives — so
if the previous song was at 91 %, the new song starts at 91 % too.

**Fix:** Reset `self.position_ms = 0` and set `self.duration_ms` from
`player.get_length()` immediately after calling `player.play()` and
before emitting the state change.

### 3. `poll()` silently crashes → `get_state()` returns stale data

The `poll()` method calls `manager.poll()`, which in turn calls the
active player's `do_stuff()`.  The `MidPlayer.do_stuff()` in `kar.py`
contains the check:

```python
if self.state == STATE_PLAYING or self.state == STATE_CAPTURING:
```

`STATE_CAPTURING` was **not imported** in `kar.py`.  During playback the
short-circuit `or` shields the NameError because `STATE_PLAYING` is
`True`.  But on **stop** (or any non-PLAYING state), Python evaluates
the second operand, hits the undefined name, and raises `NameError`.

This error propagates up through `manager.poll()` → `poll()` →
`get_state()` → `_emit_state_change()`.  Because `handle_command()` did
not include `NameError` in its except clause, the error either crashed
the backend or returned an unhelpful generic error to the frontend.

The consequence: **`poll()` never successfully returned** after any
interaction that changed the player state.  `position_ms` was frozen at
whatever stale value it held.  The slider appeared unresponsive because
every poll round-trip failed, so the frontend never received an updated
position.

**Fix (three parts):**

1. Import `STATE_CAPTURING` in `pykaraoke/players/kar.py` so the
   reference is always valid, regardless of short-circuit evaluation.
2. Wrap `manager.poll()` in `poll()` with `try/except BaseException` so
   that unexpected errors from player `do_stuff()` do not corrupt the
   state snapshot.
3. Add `NameError` to the `handle_command()` except clause so that
   command handlers that trigger `poll()` failures return a clean error
   response instead of crashing.

### 4. Stop triggers `STATE_CAPTURING` NameError

When `_handle_stop()` calls `self.current_player.stop()`, the player's
internal state transitions to `STATE_NOT_PLAYING`.  The subsequent
`_emit_state_change()` → `get_state()` → `poll()` then hits the
unshielded `STATE_CAPTURING` name in `do_stuff()`.  The same NameError
as above, but the symptom is more visible because stop explicitly
triggers a state change.

The traceback the user sees is the unhandled `NameError` propagating
from `_handle_stop()` → `handle_command()` → the event loop.

**Fix:** Same as root-cause fix 3a — import `STATE_CAPTURING` in
`kar.py`.

## Files Changed

| File | Change |
|------|--------|
| `src/pykaraoke/players/kar.py` | Added `STATE_CAPTURING` to imports from `pykaraoke.config.constants` |
| `src/pykaraoke/core/backend.py` | Reset `position_ms`/`duration_ms` in `_start_playback()` |
| `src/pykaraoke/core/backend.py` | Wrapped `manager.poll()` in `try/except` in `poll()` |
| `src/pykaraoke/core/backend.py` | Added `NameError` to `handle_command()` except clause |
| `src/runtimes/tauri/src/app.js` | Replaced `click` + `dblclick` with click-timer pattern |
| `src/runtimes/tauri/src/app.js` | Made slider `change` handler async with error feedback |
| `tests/pykaraoke/core/test_backend_progress.py` | 15 new regression tests (position reset, seek, poll exception, stop crash) |
| `tests/pykaraoke/core/test_backend_newcode.py` | 1 new test (`NameError` caught by `handle_command`) |
| `tests/pykaraoke/players/test_kar_player.py` | 1 new test (`STATE_CAPTURING` importable) |
| `tests/pykaraoke/core/test_queue_enqueue.py` | 1 new test (3× same filepath → 3 entries, not deduped) |
| `src/runtimes/tauri/src/app.test.js` | 6 new regression tests (click-timer pattern) |

## Regression Tests

| Test | What it prevents |
|------|------------------|
| `test_enqueue_same_filepath_three_times_three_entries` | Frontend must not send duplicate `add_to_playlist` commands |
| `test_start_playback_resets_position` | `position_ms` must reset to 0 on playback start |
| `test_start_playback_sets_duration` | `duration_ms` must be set from `get_length()` |
| `test_get_state_after_start_playback_returns_zero_position` | State snapshot must show 0 position after start |
| `test_seek_sets_backend_position` | `_handle_seek` must update `self.position_ms` |
| `test_seek_calls_player_seek` | Seek must forward to `player.seek()` |
| `test_seek_handles_player_seek_error` | Player errors must be surfaced |
| `test_seek_emits_state_change` | Seek must emit event |
| `test_poll_handles_manager_poll_exception` | `poll()` must survive `NameError` from `do_stuff()` |
| `test_stop_does_not_crash_when_poll_raises` | Stop must work even when poll raises |
| `test_get_state_does_not_crash_when_poll_raises` | `get_state()` must survive poll errors |
| `test_dispatch_handler_raises_name_error` | `handle_command` must catch `NameError` |
| `test_state_capturing_imported` | `kar.py` must have `STATE_CAPTURING` |
| 6 click-timer tests in `app.test.js` | Double-click must fire `enqueueSong` exactly once |

## Lessons Learned

1. **Short-circuit `or` can hide import bugs.** When `STATE_CAPTURING`
   was undefined, it never crashed during playback because `STATE_PLAYING`
   was always `True`.  The bug only surfaced on stop/pause — the exact
   moment when users are likely to report a crash.  Always test every
   code path that references a name, not just the "hot" path.

2. **`poll()` must be bulletproof.** The backend `poll()` method is
   called from `get_state()`, which is called from every state-change
   emission.  Any exception in `poll()` corrupts the entire state
   machine.  Wrap third-party / player callbacks in try/except.

3. **`handle_command()` should catch `BaseException` or a wide net.**
   The original except clause caught `RuntimeError, OSError, ValueError,
   TypeError, AttributeError` but not `NameError`.  Missing exception
   types cause unhelpful crashes that are hard to diagnose from the
   frontend.  Consider logging the full traceback and returning a clean
   error response for anything that isn't `SystemExit` or `KeyboardInterrupt`.

4. **Reset all derived state when starting a new song.** Fields like
   `position_ms` and `duration_ms` are implicitly tied to the current
   player.  When the player changes, every cached value derived from it
   must be invalidated.  A single reset point in `_start_playback()`
   prevents stale-data bugs.

5. **Frontend event coordination matters for UI correctness.** The
   `click` / `dblclick` event sequence is well-known browser behaviour,
   but easy to get wrong.  A simple timer-based debounce pattern is more
   maintainable than trying to prevent default behaviour or using
   `event.detail`.  Test the pattern with a static analysis test that
   verifies the source code structure.
