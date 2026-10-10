# Delta for Presenter Display

> Proposed change: `presenter-display`. This change creates a new capability;
> every requirement below is new behaviour.

## Purpose

A separate stage-facing output that shows only what the singer and audience
need — lyrics, graphics, song and singer identification, and timing — while
the operator keeps using the main DJ window. Legacy issues addressed:
kelvinlawson/pykaraoke#14 (separate presenter output window).

> Source: `src/web/stage.html`, `src/web/stage.js`, and the stage bridge in
> `src/web/index.html`.

## ADDED Requirements

### Requirement: Stage window lifecycle

The DJ console SHALL provide a control that opens a dedicated stage window,
re-focuses it when already open, and reports — without disrupting the main
window — when the runtime refuses to create it (for example a blocked
popup). The stage window SHALL run as an independent browser/Tauri window
loadable at `stage.html`, SHALL survive main-window layout changes, and
SHALL close cleanly on its own.

#### Scenario: Open in the browser

- **WHEN** the user activates the stage-output control in a browser
- **THEN** a separate window loads `stage.html`
- **AND** activating the control again focuses the existing window instead
  of opening a second one

#### Scenario: Popup blocked

- **WHEN** the runtime refuses to open the window
- **THEN** a status message explains that popups must be allowed for this
  origin
- **AND** the main window continues to work unchanged

#### Scenario: Desktop runtime

- **WHEN** the app runs inside the Tauri desktop runtime
- **THEN** the stage window opens as a native secondary window via the
  webview window API

### Requirement: Lyric mirroring

The stage window SHALL display the current lyric line with the same
sung/un-sung syllable progress as the main view, plus the previous and next
lines, and SHALL update within one displayed beat of the main view for line
and syllable changes. The main window SHALL push state over a local
`BroadcastChannel` (with `postMessage` fallback) and SHALL answer a
stage-load handshake so a stage window opened or reloaded mid-song shows
the correct state immediately.

#### Scenario: Line advance mirrors

- **WHEN** the main view advances to the next lyric line
- **THEN** the stage view advances to the same line

#### Scenario: Handshake after stage reload

- **WHEN** the stage window is reloaded while a song plays
- **THEN** it announces itself and receives the current snapshot
- **AND** renders the current line without waiting for the next line change

### Requirement: Stage metadata and timing

The stage window SHALL show the current song's title and artist, the active
singer's name when one is selected, and elapsed, remaining, and total time
that track the playback position (freezing while paused and updating on
seek) consistent with the transport clock.

#### Scenario: Identification

- **WHEN** a song with a singer active is playing
- **THEN** the stage header shows title, artist, and the singer's name

#### Scenario: Timing matches the transport

- **WHEN** playback is paused and then resumed
- **THEN** the stage elapsed and remaining readouts behave like the main
  transport's, including the remaining-time countdown

### Requirement: CD+G graphic mirroring

While a CD+G song plays, the stage window SHALL render the mirrored
graphics area using tile snapshots forwarded from the main window's CD+G
canvas, refreshed on the same cadence as the transport mirror updates.

#### Scenario: Graphics appear on the stage

- **WHEN** a CD+G song is playing with tile data being rendered
- **THEN** the stage window displays the mirrored graphics rather than
  lyric text

#### Scenario: Non-CDG song

- **WHEN** a KAR, LRC, or MPG song is playing
- **THEN** the stage shows lyric/metadata content instead of the graphics
  area

### Requirement: Idle and failure states

The stage SHALL display a clear idle state ("nothing playing") when no song
is loaded, SHALL tolerate snapshots arriving out of order or in an
unrecognised format without crashing, and SHALL revert to the idle state
when playback stops.

#### Scenario: Nothing playing

- **WHEN** the stage opens while no song is loaded
- **THEN** it shows the idle state

#### Scenario: Unknown snapshot version

- **WHEN** a snapshot payload declares a version the stage does not
  understand
- **THEN** the stage ignores it and keeps its last valid rendering
