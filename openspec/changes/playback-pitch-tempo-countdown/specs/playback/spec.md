# Delta for Playback

> Proposed change: `playback-pitch-tempo-countdown`. Everything under
> `## ADDED Requirements` describes behaviour the shipped player does **not**
> have yet.

## ADDED Requirements

### Requirement: MIDI/KAR key transposition

The player SHALL transpose MIDI/KAR note events by a user-selected number of
semitones in the range −12 to +12 before synthesis, SHALL leave drum-channel
notes untransposed, SHALL clamp transposed notes to the MIDI range, and SHALL
NOT alter lyric timing when the key changes. Changing the key during
playback SHALL affect the notes scheduled after the change.

#### Scenario: Positive transposition raises every note

- **WHEN** a KAR song plays with a key offset of +2 semitones
- **THEN** every non-drum note is synthesized two semitones higher than its
  parsed pitch
- **AND** the lyric timeline is unchanged

#### Scenario: Negative transposition and clamping

- **WHEN** the key offset is −12 and a parsed note is MIDI 60
- **THEN** the synthesized note is MIDI 48
- **AND** a parsed note of MIDI 5 with an offset of −12 is clamped to MIDI 0

#### Scenario: Drums are not transposed

- **WHEN** a song has notes on channel 9 and any non-zero key offset
- **THEN** the drum events are unchanged

#### Scenario: Key change mid-song affects new notes

- **WHEN** the key offset changes from 0 to +3 while a song is playing
- **THEN** notes scheduled after the change sound three semitones higher

### Requirement: MIDI/KAR tempo control

The player SHALL play MIDI/KAR songs at a user-selected rate in the range
×0.5 to ×2.0 by scaling every scheduled note time, sounding duration, the
position clock, and the end-of-song boundary, so that pause, resume, seek,
the countdown readout, and lyric highlighting all remain consistent with the
scaled position. A tempo change during playback SHALL keep the current
position continuous.

#### Scenario: Faster playback shortens the song

- **WHEN** a KAR song of duration 180 s plays at rate ×1.5
- **THEN** the end-of-song handling runs after roughly 120 s of wall time

#### Scenario: Lyric sync is preserved at any rate

- **WHEN** a KAR song plays at rate ×0.75
- **THEN** the displayed lyric line at media position *t* is the same line
  that would display at *t* on a normal-rate playback

#### Scenario: Tempo change keeps the position continuous

- **WHEN** the rate changes from ×1.0 to ×1.25 while the position clock
  reads 60 s
- **THEN** the position clock continues from 60 s and does not jump

#### Scenario: Seek under a non-default rate

- **WHEN** the user seeks to media position *t* during ×1.5 playback
- **THEN** subsequent note scheduling and the position clock both resume
  from *t*

### Requirement: Media tempo control

The player SHALL play audio and video media (CD+G companion audio, LRC
audio, and MPG video) at the selected tempo using the media element's
playback rate with pitch preservation enabled (`preservesPitch`, or the
`webkitPreservesPitch` alias where required), so that CD+G graphics, LRC
lyrics, and the transport clock stay aligned because they all follow the
element's media position.

#### Scenario: Tempo does not change media pitch

- **WHEN** a CD+G song's audio plays at rate ×1.25
- **THEN** the element's pitch-preservation flag is enabled and the audio
  plays faster without a pitch change

#### Scenario: Video honours tempo

- **WHEN** an MPG video plays at rate ×0.8
- **THEN** the video element's playback rate is ×0.8 and the transport
  clock follows its media position

### Requirement: Media key transposition

The player SHALL transpose the audio of media elements by routing them
through a Web Audio pitch-shifting graph when a non-zero key offset is
selected, SHALL keep the media clock (and therefore lyrics, CD+G graphics,
and the progress display) on the element's own media position, and SHALL
degrade gracefully — reporting a status message and reverting the key
offset to zero — when the runtime cannot build the graph. With the key at
zero the player SHALL NOT require the graph.

#### Scenario: Key shift on CD+G audio

- **WHEN** the key offset is set to +1 during CD+G playback
- **THEN** the companion audio is pitch-shifted up one semitone while its
  media position, and therefore the CD+G graphics, advance at the normal
  media rate

#### Scenario: Unsupported runtime

- **WHEN** the runtime cannot create the audio graph (for example no Web
  Audio API)
- **THEN** a status message explains that key shift is unavailable
- **AND** the key offset returns to 0 without interrupting playback

#### Scenario: Key shift on video audio

- **WHEN** the key offset is set during MPG video playback
- **THEN** the video's audio is pitch-shifted while the picture keeps
  playing at the media element's normal rate

### Requirement: Countdown readout

The transport SHALL display the remaining time as `total − elapsed` in media
time, counting down during playback, freezing while paused, updating
immediately on seek, following the tempo-scaled elapsed position, and
resetting to zero when playback stops or the song completes.

#### Scenario: Countdown during playback

- **WHEN** a song of total 3:00 has elapsed 0:45
- **THEN** the readout shows `-2:15`

#### Scenario: Paused countdown holds

- **WHEN** playback is paused
- **THEN** the remaining readout does not change

#### Scenario: Seek updates the countdown

- **WHEN** the user seeks forward by 30 s
- **THEN** the remaining readout decreases by 30 s immediately

#### Scenario: Completed or stopped song

- **WHEN** the song ends or playback is stopped
- **THEN** the remaining readout resets to `-0:00` alongside the other
  position displays

### Requirement: Key and tempo controls

The transport SHALL expose key and tempo controls that step the offset and
rate by fixed increments, clamp them to their supported ranges, reset to
the defaults (0 semitones, ×1.0) with a single activation, apply changes to
the current playback immediately, and are labelled for assistive
technology. The `[` and `]` keys outside text inputs SHALL decrement and
increment the key offset.

#### Scenario: Stepping and clamping

- **WHEN** the key control is incremented past +12, or decremented past −12
- **THEN** the offset stays at +12 or −12 respectively

#### Scenario: Reset

- **WHEN** the user activates the key or tempo reset control
- **THEN** the offset returns to 0 semitones and the rate to ×1.0 and the
  current playback reflects both immediately

#### Scenario: Keyboard key change

- **WHEN** the user presses `]` while focus is not in a text input and a
  song is loaded
- **THEN** the key offset increases by one semitone
