# Proposal: Presenter / stage output window

> Status: proposed — not implemented.
> Capability: `presenter-display` (new)
> Legacy issues: kelvinlawson/pykaraoke#14 (separate presenter/DJ output
> window).

## Intent

A KJ needs two views: the DJ console (song browser, queue, controls) and a
clean stage screen showing only the current song's lyrics/graphics for the
singer. Today PyKaraoke-NG renders everything in one window, so the
operator's controls are visible on the projector. This change adds a
separate presenter window that mirrors lyric state to the stage while the
main window keeps its slim-sidebar DJ layout unchanged.

## Scope

In scope:

* A standalone `stage.html` page (`src/web/stage.html` + `stage.js`) that
  renders the current/next lyric lines, sung-highlight syllables where the
  main view does, the song title/artist, the active singer, elapsed /
  remaining / total time, and the CD+G graphic area when relevant.
* A state channel from the main page to the stage window: `BroadcastChannel`
  when available with `postMessage` fallback, carrying a small serialisable
  snapshot of what the stage needs (not the whole store).
* Window lifecycle from the DJ console: open, focus-if-open, close; browser
  `window.open` path and Tauri `WebviewWindow` path behind the existing
  `__TAURI__` feature detection; a status message when the runtime refuses
  the window (popup blocked).
* Stage-side "nothing playing" idle state and teardown on refresh.
* Deterministic tests (vitest) for the snapshot builder and the channel
  logic (mocked), plus the existing e2e suite untouched.

Out of scope:

* Changing the main window's layout (the slim-sidebar invariant holds — the
  stage is an *additional* window, not a mode).
* Multi-screen/`Presentation API` integration beyond the two mechanisms
  above; second-display assignment is left to the OS window manager.
* Video overlay/PIP control of the projector output.

## Approach

`buildStageSnapshot(showState, playbackState)` returns a plain object:
`{song: {id, title, artist, mime, lyrics?...}, lineIdx, syllableIdx,
singerName, elapsedMs, totalMs, semitones, tempo, cdg: {tileData?...}}`.
The main page posts it on lyric-line changes, syllable ticks, transport
updates (throttled ~250 ms), and song start/stop. `stage.js` listens,
diffs the last snapshot, and re-renders only changed fields; it re-sends an
`hello` on load so the main window replies with the current snapshot
immediately (covers stage reload while a song plays).

CD+G graphics mirror by forwarding periodic tile snapshots — the main
window already repaints the CDG canvas; the stage receives a downscaled
`ImageData`-style rect list on the same 250 ms cadence while a CDG song
plays (cheap enough for the local-only channel).
