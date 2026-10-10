# Delta for Slim Sidebar UX

> Proposed change: `playback-pitch-tempo-countdown`. The `## ADDED`
> requirement describes new controls; the `## MODIFIED` requirement extends
> the existing time display.

## MODIFIED Requirements

### Requirement: Progress slider

Now Playing MUST show a progress slider bound to the current position and
duration, an elapsed/total time readout, and a remaining-time (countdown)
readout.

#### Scenario: Seek by dragging

- **WHEN** the user drags the progress slider
- **THEN** playback seeks to the corresponding position
- **AND** the current-time display updates to match

#### Scenario: Time display

- **WHEN** a song is loaded
- **THEN** the elapsed time, total duration, and a negative remaining-time
  readout are shown beside the slider

#### Scenario: Countdown accuracy

- **WHEN** playback is paused, resumed, or sought
- **THEN** the remaining-time readout tracks `total − elapsed` exactly and
  holds steady while paused

## ADDED Requirements

### Requirement: Key and tempo controls

Now Playing SHALL expose key (semitone) and tempo (rate) controls as compact
buttons that show the current value, step it by fixed increments, clamp it
to its supported range, and reset it to the default with a single
activation. Every control SHALL carry an accessible label, SHALL live inside
the existing slim column without introducing horizontal overflow, and SHALL
apply its change to the current song immediately.

#### Scenario: Visible current value

- **WHEN** the key offset is −2 and the tempo is ×1.1
- **THEN** the key control shows `-2` and the tempo control shows `110%`

#### Scenario: Accessible and compact

- **WHEN** the key and tempo controls are rendered
- **THEN** each is a button with a descriptive `title`/`aria-label` and the
  Now Playing column still fits the 300–450 px width range

#### Scenario: No song loaded

- **WHEN** no song is loaded
- **THEN** the key and tempo controls remain visible and adjust the stored
  offsets, which apply to the next song played
