# Tasks: Playback pitch, tempo, and countdown

> Order: test-first. Pure helpers first, then the synth and media wiring,
> then the UI row.

## 1. Pure helpers and tests (vitest)

- [ ] 1.1 Export `semitoneToRatio(n)` and extend `computeNoteTimeline(notes,
      programs, semitones)` with transposition (clamped, drums untouched);
      add tests for +/− offsets, clamping, and drum channels.
- [ ] 1.2 Export `remainingMs(totalMs, elapsedMs)` and
      `clampKeyOffset(n)` / `clampTempo(r)`; add tests including boundary
      clamps and the countdown readout format.
- [ ] 1.3 Export the MIDI rate mapping (`mediaTimeToCtx`, `ctxToMediaTime`,
      schedule-time scaling) as pure functions; test continuity across a
      rate change and seek-at-rate.
- [ ] 1.4 Implement `GranularPitchShifter` as a pure per-block DSP class;
      test offline with a synthetic sine: output frequency tracks
      `f × ratio` within 5 % for ratios 2^(±k/12), and ratio 1
      approximately reproduces the input.

## 2. Synth and media wiring (index.html)

- [ ] 2.1 `MidiSynth`: accept `{semitones, tempo}`; implement `setTempo`
      and `setSemitones` (stop voices, rebase `t0`, rebuild timeline,
      reschedule); keep pause/resume/seek/end-of-song exact at any rate.
- [ ] 2.2 Media path: `applyPlaybackRate(el, rate)` with
      `preservesPitch`/`webkitPreservesPitch` enforcement; on-demand
      Web Audio graph (source → shifter → gain) with graceful failure.
- [ ] 2.3 Transport: apply key/tempo to the active playback path on change;
      reset key/tempo when a new song starts? (No — offsets persist across
      songs within the session; singer prefs may overwrite — see
      singer-management.)

## 3. UI

- [ ] 3.1 Add the key/tempo control row under the transport with value
      labels, reset buttons, accessible names, and `[`/`]` shortcuts.
- [ ] 3.2 Add the `-M:SS` countdown readout to the progress row; update it
      in `updateTransport()` and reset it in `stopPlayback()`.

## 4. Verification

- [ ] 4.1 `npm test` (vitest) green; full `pytest` still green.
- [ ] 4.2 Manual smoke via `serve-web.py` if available: KAR tempo/key,
      CDG tempo/key, countdown across pause/seek/stop.
