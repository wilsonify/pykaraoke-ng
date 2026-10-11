# Delta for Player UX polish

## MODIFIED Requirements

### Requirement: Search empty states

The application MUST show a distinct empty state for each reason the result
area can be empty, and MUST offer the action that resolves it.

#### Scenario: Library not yet scanned

- **WHEN** the library contains no songs
- **THEN** the result area explains that no songs have been found yet
- **AND** offers a control that opens the folder picker

#### Scenario: Empty query

- **WHEN** the search input is empty and the library contains songs
- **THEN** the result area browses the library instead of prompting for a search
- **AND** no error is shown

#### Scenario: No matches

- **WHEN** a query matches no songs
- **THEN** the result area names the query and suggests checking the spelling,
  trying fewer words, or searching the artist
- **AND** offers a control that clears the search

#### Scenario: Matches hidden by filters

- **WHEN** a query matches songs but every match is hidden by the format filters
- **THEN** the result area reports how many matches are hidden
- **AND** offers a control that re-enables every format filter

### Requirement: Remove from queue

The user MUST be able to remove individual queue items and clear the whole
queue without a confirmation dialog, and SHALL be able to undo either action.

#### Scenario: Remove one item

- **WHEN** the user activates the remove control on a queue row
- **THEN** that song is removed from the queue
- **AND** a non-blocking notice offers to undo the removal

#### Scenario: Delete key

- **WHEN** a queue row is selected and the user presses `Delete`
- **THEN** that song is removed from the queue

#### Scenario: Clear the queue

- **WHEN** the user activates Clear in the queue section
- **THEN** every queued song is removed at once
- **AND** no confirmation dialog is shown
- **AND** a non-blocking notice offers to undo the clear

### Requirement: Reorder the queue

The application MUST let the user change the running order of queued songs
from the keyboard, operating on the selected entry.

#### Scenario: Move a queued song

- **WHEN** a queue row is selected and the user presses `Alt`+`↑` or `Alt`+`↓`
- **THEN** that entry moves one position earlier or later
- **AND** the changed order is persisted

#### Scenario: Queue selection owns the arrow keys

- **WHEN** a queue row is selected
- **THEN** `↑` and `↓` move the selection within the queue
- **AND** `Esc` clears that selection so the arrow keys return to the song list

#### Scenario: Reorder without a selection

- **WHEN** the user presses `Alt`+`↑` or `Alt`+`↓` with no queue row selected
- **THEN** a notice explains that a queued song must be selected first
- **AND** the queue order is unchanged

### Requirement: Transport controls

Now Playing SHALL expose previous, rewind, play/pause, stop, forward, and next
controls, each usable with a single activation, and SHALL disable any control
that cannot act in the current state.

#### Scenario: Toggle play and pause

- **WHEN** the user activates Play/Pause, or presses Space outside a text input
- **THEN** playback pauses if it is playing and resumes if it is paused

#### Scenario: Seek within the song

- **WHEN** the user activates rewind or forward
- **THEN** the position moves five seconds earlier or later
- **AND** the move is clamped to the start and end of the song

#### Scenario: Skip to the next song

- **WHEN** the user activates Next, or presses `Ctrl`+`→` or `Ctrl`+`↓`
- **THEN** the next queued song starts playing

#### Scenario: Previous versus restart

- **WHEN** the user activates Previous, or presses `Ctrl`+`↑`, while more than
  five seconds have elapsed
- **THEN** the current song restarts from the beginning
- **AND** when less than five seconds have elapsed, the previously queued song
  is loaded instead

#### Scenario: Unavailable controls are disabled

- **WHEN** no song is loaded, the queue is empty, or a song failed to load
- **THEN** the controls that cannot act are disabled rather than failing on
  activation

#### Scenario: Playback state is visible

- **WHEN** the playback state changes
- **THEN** a state chip reports Nothing loaded, Playing, Paused, or Playback
  failed
- **AND** Play relabels itself Pause while playing and Retry after a failed load

#### Scenario: Retry a failed song

- **WHEN** a song failed to load and the user activates Retry (or Play)
- **THEN** the application attempts to load that song again

### Requirement: Keyboard-first interaction

Every primary action — focus search, browse results, queue a song, play or
pause, skip, reorder, and remove — MUST be reachable from the keyboard.

#### Scenario: Focus search from anywhere

- **WHEN** the user presses `/` or `Ctrl`/`Cmd`+`K`
- **THEN** the search input receives focus

#### Scenario: Clear the search

- **WHEN** the search input is focused and the user presses `Esc`
- **THEN** the query is cleared and the result area returns to browsing the
  library

#### Scenario: Leave the queue

- **WHEN** a queue row is selected and the user presses `Esc` outside a text
  input
- **THEN** the selection is cleared
- **AND** the arrow keys act on the song list again

#### Scenario: Navigate and select results

- **WHEN** the user presses `↓` or `↑` outside a text input
- **THEN** the highlighted result moves down or up
- **AND** the selection wraps around the ends of the list

#### Scenario: Queue the highlighted song

- **WHEN** a result is highlighted and the user presses Enter
- **THEN** that song is appended to the queue

#### Scenario: Typing is never hijacked

- **WHEN** a text input or select control has focus
- **THEN** single-key shortcuts such as Space and the arrow keys perform their
  normal text-editing behaviour instead of transport or navigation actions
- **AND** only `/` and `Ctrl`/`Cmd`+`K` still focus the search input

## ADDED Requirements

### Requirement: Browsable library list

The result area SHALL present the library's contents for browsing before the
user types a query, so the library can be explored without guessing a title.

#### Scenario: Browse on launch

- **WHEN** the search input is empty and the library contains songs
- **THEN** the result area lists the library's songs
- **AND** the heading and count describe the whole library

#### Scenario: Large library

- **WHEN** the library holds more songs than the browse page limit
- **THEN** the first page of the library is listed
- **AND** a hint explains that typing searches the remaining songs

#### Scenario: Narrowing by typing

- **WHEN** the user types a query
- **THEN** the list is replaced by the matches
- **AND** the count reports how many songs are shown

### Requirement: Queue position and duplicate feedback

Each queued song SHALL show its place in the running order, and queueing a song
that is already queued SHALL be allowed and reported rather than silently
duplicated or refused.

#### Scenario: Queue positions

- **WHEN** the queue contains songs
- **THEN** each row shows its one-based position
- **AND** the queue area names the song that plays next

#### Scenario: Queueing a song twice

- **WHEN** the user queues a song that is already in the queue
- **THEN** the song is appended again
- **AND** the notice reports that it was already queued and how many copies are
  queued
- **AND** the song's result row shows how many copies are queued

#### Scenario: Playing a queued song

- **WHEN** a queued song starts from the queue
- **THEN** it is removed from the queue so that it cannot play a second time

### Requirement: Scan diagnostics presentation

The outcome of a scan MUST be described in plain language, MUST distinguish
files that could not be used from files that were simply skipped, and MUST
stay reachable after the transient notice is dismissed.

#### Scenario: Human summary

- **WHEN** a scan finishes
- **THEN** the summary reports the library size
- **AND** any skipped or unusable files are named by category with
  thousands-separated counts and human labels

#### Scenario: Problems versus skips

- **WHEN** the scan could not use files that looked like karaoke
- **THEN** those are reported first as problems
- **AND** files that are simply not karaoke, or that the user filtered out, are
  reported as skipped and are never described as errors

#### Scenario: Inspecting the details

- **WHEN** the user activates the scan-details control
- **THEN** the skipped and unusable paths are listed grouped by category
- **AND** the details remain available after the notice is dismissed
- **AND** the user can clear them

#### Scenario: Nothing to report

- **WHEN** every file in the scan was usable
- **THEN** no details control is shown

### Requirement: Status language and notices

User-facing status MUST describe the application state rather than the runtime
that provides it, and routine feedback MUST NOT block the workflow.

#### Scenario: Readiness

- **WHEN** the engine finishes loading
- **THEN** the status line reports readiness and the number of songs in the
  library
- **AND** the engine indicator reports a state (Starting, Ready, or Engine
  unavailable) instead of naming the runtime

#### Scenario: Routine feedback

- **WHEN** a routine action succeeds or warns — queueing, removing, clearing,
  importing, exporting, or scanning
- **THEN** it is reported in a notice that does not block interaction
- **AND** the notice can be dismissed
- **AND** where an action is available (Undo, Retry, See details) it is offered
  on the notice

#### Scenario: Playback failure

- **WHEN** a song fails to load
- **THEN** the failure is stated in plain language with the reason
- **AND** the transport reports Playback failed
- **AND** a Retry action is offered

### Requirement: Settings organisation and rescan indication

The settings panel SHALL group its controls by concern and SHALL make clear
which settings apply immediately and which apply at the next scan.

#### Scenario: Grouped settings

- **WHEN** the settings panel is open
- **THEN** the controls are grouped as Library and scanning, Song names,
  Playback and display, Advanced file filters, and Keyboard shortcuts
- **AND** the advanced pattern inputs are behind a disclosure

#### Scenario: Rescan tagging

- **WHEN** a setting takes effect only at the next scan
- **THEN** its label carries a rescan tag
- **AND** changing it reveals a note offering to rescan the library now

#### Scenario: Immediate settings

- **WHEN** the user changes a setting that is applied immediately — sorting,
  CD+G zoom, or volume
- **THEN** the change takes effect without a rescan

#### Scenario: Destructive library replacement

- **WHEN** the user activates Replace library
- **THEN** the effect is explained and a confirmation step is required before
  the current song list is replaced

### Requirement: Keyboard shortcut reference

The keyboard bindings SHALL be discoverable from within the application.

#### Scenario: Reference list

- **WHEN** the user opens the settings panel
- **THEN** the keyboard shortcuts section lists the stated keys for each
  binding and what the binding does

#### Scenario: Reference matches the implementation

- **WHEN** a binding changes
- **THEN** the reference lists the bindings the UI actually implements
