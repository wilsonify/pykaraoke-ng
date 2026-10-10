# Design: Playback pitch, tempo, and countdown

## Mechanisms per playback path

| Path | Key shift | Tempo | Sync source |
|------|-----------|-------|-------------|
| KAR/MID (`MidiSynth`) | semitone offset on the note timeline | rate scales scheduled note times and the position clock | `currentMs()` = `(ctx.currentTime − t0) × 1000 × rate` |
| CD+G (audio + canvas) | Web Audio granular shifter on the audio element | `playbackRate` with `preservesPitch = true` | `audio.currentTime` (unchanged semantics) |
| LRC (audio + lyrics) | same media graph | same | `audio.currentTime` |
| MPG (video) | same media graph on the video element | same | `video.currentTime` |

## Rate math (MIDI)

The synth keeps its timeline in *media time* (the song's own milliseconds).
For a rate `r`:

* context-time of a note = `t0 + (startMs / 1000) / r`
* sounding duration = `(endMs − startMs) / 1000 / r`
* `currentMs()` = `(ctx.currentTime − t0) × 1000 × r`

A rate change mid-song rebases `t0 = ctx.currentTime − currentMs()/1000/r`
before the change, stops sounding voices (only ≤200 ms look-ahead was
scheduled, so this is a negligible glitch), recomputes `nextIndex` from the
current media time, and reschedules. End-of-song still fires at
`currentMs() ≥ durationMs` because `durationMs` is media time.

## Pitch shifter for media

`GranularPitchShifter` is a pure DSP class:

* a circular input buffer per channel (R = 32768 samples ≈ 0.7 s at 44.1 kHz);
* every H = 512 output samples a grain of G = 1024 samples is read at
  `(ratio × w − G) mod R` (never ahead of the write head), Hann-windowed,
  and overlap-added into the output queue;
* `ratio = 2 ** (semitones / 12)`; ratio 1 is a ~G-sample delayed near-copy.

The shifter is wired through the deprecated-but-universal
`ScriptProcessorNode` (supported in Chromium, WebKit, and Gecko webviews
including Tauri's) because it needs no external module file and no
`AudioWorklet` bootstrap. It is only created the first time a non-zero key
is requested for an element; from then on the element permanently outputs
through the graph, with volume applied by the graph's output gain (element
volume pinned to 1). Graph creation failure is caught and surfaced as a
status message; the key control resets to 0 and the element keeps its normal
output.

Verification: vitest drives `process()` offline with a synthetic sine wave
and asserts the output's zero-crossing frequency tracks `f × ratio` within
5 % after a warm-up period, and that ratio 1 approximately reproduces the
input.

## Countdown

`remainingMs(totalMs, elapsedMs) = max(0, totalMs − elapsedMs)` — both in
media time, consistent with the progress slider. It is displayed as
`-M:SS`; it freezes while paused, jumps on seek, scales with tempo exactly
like the elapsed readout, and resets on stop and at end of song.

## Controls and keyboard

A compact row under the transport: `Key −` / `Key 0` / `Key +` (labelled
with the current semitone offset, e.g. `−2`), `Tempo −` / `Tempo 100%` /
`Tempo +`. Range: semitones −12…+12, tempo 0.5…2.0 in 0.05 steps clamped and
rounded. `[` and `]` outside text inputs decrement/increment the key (a
common karaoke convention); all controls carry `title`/`aria-label` text.
