# Delta for UX — slim sidebar

> Change: `lyrics-timing-resilience`. `## MODIFIED Requirements` replaces the
> requirement of the same name in `openspec/specs/ux-slim-sidebar/spec.md`.

## MODIFIED Requirements

### Requirement: Lyrics display

With timed lyrics, the application SHALL display the current line, the
completed line above it, and the upcoming line below it, distinguished by
class. The current line SHALL highlight syllables as their timestamps pass and
SHALL stay in view. Activating a line SHALL seek to its timestamp when seeking
is available, and do nothing otherwise. A persisted small/medium/large lyric
size SHALL apply to LRC and MIDI lyrics alike, without modal, overlay, or
automatic wide-mode expansion.

#### Scenario: Highlighting the current line

- **WHEN** playback reaches a lyric line's timestamp
- **THEN** that line is highlighted
- **AND** the following line is shown dimmed beneath it
- **AND** the line just sung is shown dimmed above it

#### Scenario: Duet parts are labelled

- **WHEN** a lyric line is tagged with a duet part
- **THEN** the line is coloured for that part
- **AND** a small chip names the singer, or the generic part id when the song
  does not name one

#### Scenario: Click to seek

- **WHEN** the operator activates the upcoming lyric line during playback
- **THEN** playback continues from the start of that line

#### Scenario: Click to seek is unavailable

- **WHEN** the song cannot be seeked (MIDI synthesis in a paused state, or no
  song loaded)
- **THEN** activating a lyric line changes nothing

#### Scenario: Lyric size

- **WHEN** the operator chooses a different lyric size
- **THEN** the stage lyrics change size immediately
- **AND** the choice survives a restart

> Note: the lyric display is centred (`text-align: center`), which is a
> deliberate exception to the left-alignment requirement above.
