# Proposal: Playback pitch, tempo, and countdown controls

> Status: proposed — not implemented.
> Capabilities: `playback`, `ux-slim-sidebar`
> Legacy issues: kelvinlawson/pykaraoke#2 (pitch-shifting), #4 (tempo-shifting),
> #9 (key change facility, countdown time).

## Intent

A working KJ must be able to match a song to the singer's range (key change)
and to the singer's speed (tempo change), and needs to know how much time is
left in the current song. None of these exist in PyKaraoke-NG today: the
transport shows elapsed/total only, MIDI synthesis has no transposition or
rate parameter, and media elements play at their natural rate and pitch.

The legacy implementation backed pitch and tempo with GStreamer's `pitch`
element, which the rewrite removed along with all of GStreamer. This change
implements the capabilities on the mechanisms the rewrite actually has:

* **MIDI/KAR** — the `MidiSynth` scheduler owns note times and frequencies, so
  key is a semitone offset applied when the note timeline is built and tempo
  is a rate that scales every scheduled time and the position clock.
* **Audio/video media** (CD+G companion audio, LRC audio, MPG video) — tempo
  uses the platform's native `HTMLMediaElement.playbackRate` with
  `preservesPitch` enabled, so speed changes keep the pitch. Independent key
  shifting needs signal processing, so the media element is routed through a
  small, dependency-free Web Audio granular pitch shifter that is only engaged
  when a non-zero key is requested.

Lyric and CD+G synchronisation follow the media position (element
`currentTime` or the synthesizer's rate-scaled clock), so both controls keep
lyrics aligned by construction.

## Scope

In scope:

* Key transposition (semitones −12…+12) for MIDI/KAR synthesis and for
  audio/video media, with reset controls.
* Tempo/rate control (×0.5…×2.0, default ×1.0) for every playback path, with
  reset, applied natively for media and by the scheduler for MIDI/KAR.
* A remaining-time (countdown) readout next to the elapsed/total display that
  stays correct across pause, resume, seek, tempo change, and end of song.
* Transport UI: key −/+, tempo −/+, and reset buttons with accessible labels,
  plus `[`/`]` key shortcuts for key changes outside text inputs.
* Deterministic unit tests (vitest) for the transposition, rate-scaling,
  countdown, and granular pitch-shifter DSP using synthetic signals — no audio
  hardware or network.

Out of scope:

* Time-stretching the MIDI synth independently of pitch (the synth already
  changes tempo without changing pitch because notes are scheduled, not
  played back from a buffer).
* Karaoke-format support beyond the existing CDG/KAR/MID/LRC/MPG set.
* Persisting key/tempo per singer (covered by the `singer-management` change).
* New Python engine surface — the engine already exposes everything the
  transport needs; pitch and tempo are presentation-time concerns in the page.

## Approach

`computeNoteTimeline()` gains an optional semitone offset (drum channels are
never transposed). `MidiSynth` gains `setTempo(rate)` and `setSemitones(n)`:
both stop currently sounding voices, rebase the context-clock origin so the
media-time position is continuous, rebuild the timeline where needed, and
reschedule from the current position. A pure `timeToCtx`/`ctxToMedia` mapping
keeps pause/resume/seek/end-of-song exact under any rate.

Media elements get `applyPlaybackRate(el, rate)` (sets `playbackRate` and
forces `preservesPitch`/`webkitPreservesPitch` true) and, for key shifts, an
on-demand Web Audio graph `MediaElementSource → GranularPitchShifter
(ScriptProcessor) → gain → destination`. `GranularPitchShifter` is a pure
per-block DSP class (Hann-windowed overlap-add grains read from a circular
buffer at a ratio-controlled rate) exported for offline tests with synthetic
sine waves. If the runtime cannot build the graph, the key controls report
that pitch shift is unavailable and revert to zero; tempo and everything else
keep working.

The countdown readout is `formatTime(max(0, total − elapsed))`, updated in
the same `updateTransport()` path as the elapsed readout so it inherits the
existing pause/seek/end behaviour.
