# Slim Sidebar UX Specification

## Purpose

Defines the user-interface posture, layout, interaction, and visual constraints
for PyKaraoke-NG: a slim, keyboard-driven utility panel that a working DJ keeps
docked beside their primary DJ software during a live set. These requirements
carry the same governance weight as the architectural constraints in the
project-governance specification and are treated as defects when violated.

> Source: migrated from `specs/ux-design.md`; every statement below was verified
> against the shipped UI in `src/web/index.html` and the window configuration in
> `src/runtimes/tauri/src-tauri/tauri.conf.json`.

> Note: the shipped implementation diverges from the original design document in
> several places (sticky Now Playing, virtual scrolling, drag-to-reorder, the
> colour palette, and Stop behaviour). Divergences are recorded as `> Note:`
> lines on the affected requirement rather than silently resolved.

## Requirements

### Requirement: Utility-panel posture

PyKaraoke-NG SHALL present itself as a professional utility panel for a live
DJ, not as a full-screen media consumption application.

#### Scenario: Sitting beside primary DJ software

- **WHEN** a DJ runs PyKaraoke-NG alongside their primary DJ application on a
  single laptop screen
- **THEN** the karaoke panel occupies only a narrow strip of the screen
- **AND** the DJ can search, queue, and control playback without switching away
  from the primary application

### Requirement: Primary persona

The product MUST optimise for a working DJ who runs karaoke as part of a
broader live set and operates under real-time pressure.

#### Scenario: Rapid request handling

- **WHEN** a patron makes a song request between two songs
- **THEN** the DJ can find and queue the song in a small number of keystrokes
- **AND** no confirmation dialog, wizard, or page transition is required

### Requirement: Single-column vertical flow

The main content region MUST be a single vertical column; horizontal panel
splits MUST NOT exist in the default layout.

#### Scenario: Default layout is one column

- **WHEN** the application starts
- **THEN** the primary regions are stacked vertically in the order: library
  actions, search, search results, Now Playing, and queue
- **AND** no horizontally split left/right panel is rendered

### Requirement: Slim window dimensions

The desktop window SHALL default to a slim width and MUST remain usable across
the supported 300–450 px width range.

#### Scenario: Default window size

- **WHEN** the desktop application is launched for the first time
- **THEN** the window opens at 380 px wide
- **AND** the width can be resized between 300 px and 450 px
- **AND** the window enforces a minimum height of 500 px

#### Scenario: Functional at minimum width

- **WHEN** the window is resized to 300 px wide
- **THEN** search, results, Now Playing, and the queue all remain usable
- **AND** no horizontal scrollbar appears

> Note: `src/runtimes/tauri/src-tauri/tauri.conf.json` sets `width` 380,
> `minWidth` 300, `maxWidth` 450, `minHeight` 500, and `height` 800. Some window
> managers may not honour the maximum width hint when snapping; the root
> element's CSS `max-width` is the reliable fallback.

### Requirement: No screen dominance

The application MUST NOT expand to fill the available screen width unless the
user explicitly requests a wider layout.

#### Scenario: Wider viewport does not widen the layout

- **WHEN** the viewport is wider than 450 px
- **THEN** the content column stays constrained to a maximum width of 450 px

> Note: the root element is centred within a wider viewport with `margin: 0
> auto`. The original design document prohibited `margin: 0 auto` on
> containers; the shipped behaviour centres the panel but keeps every primary
> control inside it left-aligned.

### Requirement: Left-aligned primary controls

Primary controls — the search input, result rows, the Now Playing text, and
queue rows — SHALL be left-aligned.

#### Scenario: Titles and labels start at the left edge

- **WHEN** a result row or queue row is rendered
- **THEN** its title and secondary text begin at the left edge of the row
- **AND** no primary control is centred

> Note: two non-primary elements are intentionally centred in the shipped UI —
> the karaoke lyric display (`.lyrics`) and the transport button group
> (`.player-controls`). These are display elements, not text controls, and are
> recorded here so the requirement does not contradict the implementation.

### Requirement: Fixed top and bottom regions

The application SHALL keep the header/search area at the top and the status bar
at the bottom, each outside the scrollable region.

#### Scenario: Scrolling does not move the status bar

- **WHEN** the user scrolls a long list of search results or queue items
- **THEN** the header stays at the top of the window
- **AND** the status bar stays at the bottom of the window

### Requirement: Scrollable content region

The middle content region MUST scroll vertically and MUST NOT scroll
horizontally.

#### Scenario: Long results list scrolls

- **WHEN** the result or queue list is taller than the available space
- **THEN** the middle region scrolls vertically
- **AND** long song titles are truncated with an ellipsis rather than causing
  horizontal overflow

> Note: the original design document specified a `position: sticky` Now Playing
> section. The shipped UI does not use sticky positioning; Now Playing scrolls
> with the rest of the content column (`src/web/index.html`, `.main-column`).

### Requirement: Incremental search

Search MUST filter results incrementally as the user types, without a submit
button, and MUST debounce input to avoid excessive work.

#### Scenario: Typing filters results

- **WHEN** the user types into the search input
- **THEN** matching results appear as the query changes
- **AND** no Search button or Enter key is required

#### Scenario: Debounced input

- **WHEN** the user types several characters in quick succession
- **THEN** the query is issued once after a short debounce interval
- **AND** the result list is not re-rendered for every individual keystroke

> Note: the shipped debounce interval is 150 ms and the result limit is 500
> (`src/web/index.html`). The original document said 100–150 ms; 150 ms is
> within that range.

### Requirement: Search kind filters

Search results SHALL be filterable by media kind.

#### Scenario: Filtering by kind

- **WHEN** the user unchecks the CDG, KAR/MID, MPG, or LRC filter
- **THEN** results of that kind are hidden from the result list
- **AND** unchanged filters continue to show their results

### Requirement: Search empty states

The application MUST show an explicit hint when there is nothing to display.

#### Scenario: Empty query

- **WHEN** the search input is empty
- **THEN** the result list shows a prompt to type a search
- **AND** no error is shown

#### Scenario: No matches

- **WHEN** a query matches no songs, or all matches are excluded by filters
- **THEN** the result list shows an inline "no results" message

### Requirement: Add to queue

The user SHALL be able to add a search result to the queue from the keyboard or
the mouse.

#### Scenario: Keyboard add

- **WHEN** a result is highlighted with the arrow keys and the user presses Enter
- **THEN** that song is appended to the queue

#### Scenario: Pointer add

- **WHEN** the user clicks a result row
- **THEN** that song is appended to the queue
- **AND** when the user double-clicks the row or presses its play button, the
  song starts playing immediately

### Requirement: Remove from queue

The user MUST be able to remove individual queue items and clear the whole
queue without a confirmation dialog.

#### Scenario: Remove one item

- **WHEN** the user clicks the ✕ control on a queue row
- **THEN** that song is removed from the queue

#### Scenario: Clear the queue

- **WHEN** the user activates Clear in the queue section
- **THEN** every queued song is removed at once
- **AND** no confirmation dialog is shown

> Note: the original design document specified pressing Delete to remove the
> selected queue item. The shipped key handler looks for a selected queue row,
> but queue rows are never marked selected, so that binding is currently
> ineffective (`src/web/index.html` keydown handler).

### Requirement: Reorder the queue

The application MUST let the user change the running order of queued songs
from the keyboard.

#### Scenario: Move a queued song

- **WHEN** the user presses a reorder shortcut with the queue focused
- **THEN** the affected queue entry changes position
- **AND** the changed order is persisted

> Note: the shipped reorder bindings (`Ctrl`+`↑` / `Ctrl`+`↓`) move only the
> first or last queue entry, not an arbitrary selected entry, and the same
> keystrokes also move the result selection. Drag-to-reorder is not
> implemented. The original document described per-item reorder for both.

### Requirement: Queue auto-advance

When a song finishes, the application SHALL automatically start the next
queued song.

#### Scenario: End of song advances the queue

- **WHEN** the currently playing song reaches its end
- **THEN** the next queued song is removed from the queue and starts playing

#### Scenario: Queue exhausted

- **WHEN** the final queued song finishes
- **THEN** playback stops
- **AND** the status bar reports that the queue is finished

### Requirement: Empty queue hint

The queue area MUST show a hint when no songs are queued.

#### Scenario: Queue is empty

- **WHEN** the queue contains no songs
- **THEN** the queue area displays an inline hint explaining how to add songs

### Requirement: Transport controls

Now Playing SHALL expose previous, rewind, play/pause, stop, forward, and next
controls, each usable with a single activation.

#### Scenario: Toggle play and pause

- **WHEN** the user activates Play/Pause, or presses Space outside a text input
- **THEN** playback pauses if it is playing and resumes if it is paused

#### Scenario: Seek within the song

- **WHEN** the user activates rewind or forward
- **THEN** the position moves five seconds earlier or later
- **AND** the move is clamped to the start and end of the song

#### Scenario: Skip to the next song

- **WHEN** the user activates Next, or presses `Ctrl`+`→`
- **THEN** the next queued song starts playing

#### Scenario: Previous versus restart

- **WHEN** the user activates Previous while more than five seconds have elapsed
- **THEN** the current song restarts from the beginning
- **AND** when less than five seconds have elapsed, the previously queued song
  is loaded instead

> Note: the shipped Stop control resets the player and clears the Now Playing
> display (`stopPlayback()` followed by `setPlaying(null)`), so pressing Play
> afterwards has no effect until a song is selected again. The older user guide
> described Stop as keeping the current song loaded; that description is
> outdated.

### Requirement: Progress slider

Now Playing MUST show a progress slider bound to the current position and
duration.

#### Scenario: Seek by dragging

- **WHEN** the user drags the progress slider
- **THEN** playback seeks to the corresponding position
- **AND** the current-time display updates to match

#### Scenario: Time display

- **WHEN** a song is loaded
- **THEN** the elapsed time and total duration are shown beside the slider

### Requirement: Volume control

The application SHALL provide a volume control that applies to the current
playback immediately.

#### Scenario: Adjust volume

- **WHEN** the user moves the volume slider
- **THEN** the active audio, video, or synthesised playback changes volume
- **AND** the chosen level is shown as a percentage

### Requirement: Keyboard-first interaction

Every primary action — focus search, navigate results, queue a song, play or
pause, skip, and remove — MUST be reachable from the keyboard.

#### Scenario: Focus search from anywhere

- **WHEN** the user presses `/` or `Ctrl`/`Cmd`+`K`
- **THEN** the search input receives focus

#### Scenario: Clear the search

- **WHEN** the search input is focused and the user presses `Esc`
- **THEN** the query is cleared and the result list is emptied

#### Scenario: Navigate and select results

- **WHEN** the user presses `↓` or `↑` outside a text input
- **THEN** the highlighted result moves down or up
- **AND** the selection wraps around the ends of the list

#### Scenario: Typing is never hijacked

- **WHEN** a text input or select control has focus
- **THEN** single-key shortcuts such as Space and the arrow keys perform their
  normal text-editing behaviour instead of transport or navigation actions

### Requirement: Inline settings, not a modal

Settings MUST be presented as an inline, collapsible panel; they MUST NOT open
as a modal overlay.

#### Scenario: Open and close settings

- **WHEN** the user activates the settings control
- **THEN** an inline settings panel is revealed within the window
- **AND** activating the control again hides it

### Requirement: Configurable behaviour

The application SHALL expose settings for library ordering, CDG zoom, archive
scanning, artist filtering, and filename-derived metadata.

#### Scenario: Adjust library ordering

- **WHEN** the user changes the library sort setting
- **THEN** the library is ordered by filename, title, or artist accordingly

#### Scenario: Adjust CDG zoom

- **WHEN** the user changes the CDG zoom setting
- **THEN** the CD+G canvas is scaled to the selected level (0.75×, 1×, 1.5×, or
  2×)

#### Scenario: Archive and metadata options

- **WHEN** the user toggles looking inside zip files, hiding songs without an
  artist, or deriving song information from filenames
- **THEN** the corresponding behaviour applies to scanning and results

### Requirement: Persistence across restarts

The library, queue, and settings MUST persist locally and be restored on the
next launch.

#### Scenario: Restore state

- **WHEN** the application is closed and reopened
- **THEN** the previously scanned library, the queue order, and the settings are
  restored
- **AND** the queue entries that still exist in the library reappear in order

### Requirement: Status bar feedback

The application SHALL keep a status bar visible that reports engine readiness
and the result of the user's last action.

#### Scenario: Engine ready

- **WHEN** the WebAssembly engine and its wheel have finished loading
- **THEN** the status bar reports that the engine is ready

#### Scenario: Action feedback

- **WHEN** the user scans a folder, queues a song, or encounters an error
- **THEN** the status bar shows a brief message describing the outcome

### Requirement: Dark theme by default

The interface SHALL use a dark theme by default, suitable for low-light venues,
and MUST remain legible on both dark and light system settings.

#### Scenario: Default appearance

- **WHEN** the application starts
- **THEN** the interface renders with the dark palette
- **AND** text and controls meet a contrast ratio of at least 4.5:1 for text and
  3:1 for interface elements

> Note: the shipped palette is defined as CSS custom properties on `:root` in
> `src/web/index.html` — background `#14151a`, elevated surface `#1c1e25`,
> border `#2c2f3a`, text `#e8e9ed`, dimmed text `#9aa0ae`, accent `#e8b64c`,
> danger `#e06c75`, and success `#7ec699`. This supersedes the illustrative
> palette in the original design document.

### Requirement: Compact visual density

Typography, spacing, and control sizes SHALL favour information density over
whitespace so that results, Now Playing, and the queue all fit in a slim
window.

#### Scenario: Dense lists

- **WHEN** the result and queue lists are rendered at the default width
- **THEN** row padding and font sizes stay compact
- **AND** section labels use a smaller, uppercase style

### Requirement: Lyrics display

When a song supplies timed lyrics, the application SHALL display the current
line and the upcoming line in the stage area.

#### Scenario: Highlighting the current line

- **WHEN** playback reaches a lyric line's timestamp
- **THEN** that line is highlighted
- **AND** the following line is shown dimmed beneath it

#### Scenario: Duet parts are labelled

- **WHEN** a lyric line is tagged with a duet part
- **THEN** the line is coloured for that part
- **AND** a small chip names the singer, or the generic part id when the song
  does not name one

> Note: the lyric display is centred (`text-align: center`), which is a
> deliberate exception to the left-alignment requirement above.

### Requirement: Responsive behaviour within the supported range

The layout MUST remain functional throughout the 300–450 px width range.

#### Scenario: Long titles at narrow width

- **WHEN** the window is at the narrow end of the supported range
- **THEN** long titles truncate with an ellipsis
- **AND** all primary controls remain reachable

### Requirement: Opt-in wide mode

The application MAY offer an explicit wide mode; when it does, that mode MUST
never activate automatically.

#### Scenario: Wide mode is only user-initiated

- **WHEN** the application is running at its default width
- **THEN** no automatic expansion beyond the maximum width occurs

> Note: an explicit wide-mode toggle is not implemented today. This
> requirement records the intended behaviour for a future change and does not
> claim current support.

### Requirement: Prohibited interaction patterns

The product MUST NOT use interaction patterns that break the live DJ workflow.

#### Scenario: Banned patterns

- **WHEN** any new UI is added
- **THEN** it MUST NOT introduce modal dialogs, full-screen overlays,
  confirmation dialogs for queue actions, multi-step wizards, splash screens,
  mandatory settings screens, automatic full-width expansion, or horizontal
  tab bars

### Requirement: Three-second add workflow

The search-to-queue workflow MUST be completable in under three seconds of
interaction.

#### Scenario: Quick queue

- **WHEN** a DJ hears a request and types the first few characters of a title
- **THEN** matching songs appear immediately
- **AND** pressing Enter queues the intended song without further interaction

### Requirement: Glanceable state

For a queue of five or fewer songs, the current song, its progress, the queue
size, and the next song MUST be visible without scrolling.

#### Scenario: At-a-glance status

- **WHEN** the queue holds five or fewer songs
- **THEN** the current song title and progress, the queue count, and the next
  song are all visible in the panel without scrolling

### Requirement: Emergency skip

Stopping or skipping playback MUST be achievable with a single activation that
is visible without scrolling.

#### Scenario: Stop the wrong song immediately

- **WHEN** the wrong song is playing or a technical problem occurs
- **THEN** the DJ can stop or skip it with one activation of a visible control
- **AND** no confirmation dialog intervenes

### Requirement: Accessibility

Interactive elements MUST be keyboard reachable and carry accessible labels.

#### Scenario: Keyboard reachability

- **WHEN** the user moves focus with Tab
- **THEN** every interactive control receives focus in a sensible order
- **AND** the focused control has a visible focus indicator

#### Scenario: Labelling icon-only controls

- **WHEN** a control shows only an icon
- **THEN** it carries a title or accessible label describing its action
- **AND** the result and queue lists expose list and option roles

### Requirement: Performance budgets

The panel MUST meet the following interaction budgets.

#### Scenario: Launch and search responsiveness

- **WHEN** the application launches or the user types a query
- **THEN** the panel becomes usable within roughly 500 ms of launch
- **AND** a search result set of up to 100 items renders within roughly 50 ms of
  the query completing

> Note: these budgets are design targets carried over from the original
> document. They are not yet covered by an automated performance test.
