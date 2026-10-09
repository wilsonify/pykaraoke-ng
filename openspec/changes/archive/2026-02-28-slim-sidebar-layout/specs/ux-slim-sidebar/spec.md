# Delta for Slim Sidebar UX

## ADDED Requirements

### Requirement: Single vertical column layout

The application SHALL present all primary UI in a single vertical column, with
no horizontal panel split in the default layout.

#### Scenario: Default layout is one column

- **WHEN** the application loads
- **THEN** the root container (`#app`) is a vertical flex column
- **AND** no `.left-panel` or `.right-panel` split exists

#### Scenario: One scroll container

- **WHEN** the user scrolls the main content
- **THEN** only the main column (`.main-column`) scrolls
- **AND** the header and status bar remain fixed
- **AND** no horizontal scrollbar appears

### Requirement: Slim sidebar window

The application window SHALL default to a slim sidebar width and SHALL be
constrained to the 300–450 px range.

#### Scenario: Default window size

- **WHEN** the desktop application launches
- **THEN** the window is 380 px wide and 800 px tall
- **AND** the window declares a minimum width of 300 px, a maximum width of
  450 px, and a minimum height of 500 px

#### Scenario: Maximum width fallback

- **WHEN** the window manager ignores the maximum-width hint
- **THEN** the CSS `max-width` of 450 px on the root container still prevents
  the layout from widening beyond the sidebar range

### Requirement: Fixed chrome and flowing content

The application SHALL keep the header and status bar fixed while the main
content flows and scrolls between them.

#### Scenario: Header and status stay visible

- **WHEN** the main content is scrolled to any position
- **THEN** the app header (search controls and library actions) stays at the top
- **AND** the status bar (engine status and messages) stays at the bottom

### Requirement: Compact visual density

The application SHALL prioritise information density over whitespace so the
results and queue remain readable in a narrow window.

#### Scenario: Long titles truncate

- **WHEN** a song title or artist is wider than its row
- **THEN** the text truncates with an ellipsis
- **AND** no horizontal overflow or scrollbar appears

#### Scenario: Icon-only transport controls

- **WHEN** the Now Playing section is shown
- **THEN** the transport controls appear as compact icon-only buttons
- **AND** the progress and volume sliders are shown inline

### Requirement: Keyboard-first navigation

Every primary DJ action SHALL be reachable from the keyboard without using a
mouse.

#### Scenario: Focus and clear search

- **WHEN** the user presses `/` or `Ctrl`/`Cmd`+`K`
- **THEN** the search input receives focus
- **AND** pressing `Escape` while focused clears the search input

#### Scenario: Navigate and queue a result

- **WHEN** search results are shown
- **THEN** `ArrowDown` and `ArrowUp` move the selection
- **AND** `Enter` adds the selected result to the queue

#### Scenario: Playback and queue shortcuts

- **WHEN** focus is outside a text input
- **THEN** `Space` toggles play/pause
- **AND** `Ctrl`+`ArrowRight` skips to the next song
- **AND** `Delete` removes the selected queue item
- **AND** `Ctrl`+`ArrowUp` / `Ctrl`+`ArrowDown` reorder the selected queue item

### Requirement: Instant incremental search

Search SHALL filter incrementally as the user types, with debouncing to avoid
excessive re-renders.

#### Scenario: Results update while typing

- **WHEN** the user types in the search input
- **THEN** results update without a submit button
- **AND** rapid keystrokes are debounced

### Requirement: No blocking overlays in the primary workflow

The primary workflow SHALL NOT be blocked by modal dialogs, full-screen
overlays, confirmation dialogs, or multi-step wizards.

#### Scenario: Settings do not block the workflow

- **WHEN** the user opens settings
- **THEN** the settings panel appears inline
- **AND** the search, queue and playback controls remain usable

#### Scenario: Queue changes need no confirmation

- **WHEN** the user adds or removes a queue item
- **THEN** the change applies immediately with no confirmation dialog
