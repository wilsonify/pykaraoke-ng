# Proposal: Slim Sidebar Layout

## Intent

The frontend used a two-panel horizontal flexbox (`.left-panel` / `.right-panel`)
inside a 1024 × 768 default window. For the primary user — a working DJ running
karaoke alongside their main DJ software — that layout failed on three counts:

- **It consumed most of the screen.** A 1024 px-wide karaoke window cannot sit
  beside primary DJ software on a typical 1366–1920 px laptop.
- **It split attention horizontally.** Correlating search results with playback
  state required scanning left to right, an unnatural flow during a live set.
- **It violated the project's constitutional design posture** (constitution §2.2),
  which requires a slim, vertically-stacked utility panel rather than a
  screen-dominating media player.

## Scope

In scope:

- A single-column, vertically-stacked layout for the whole application.
- A slim default window (380 px wide, clamped to 300–450 px).
- Compact visual density and text truncation instead of horizontal overflow.
- Keyboard-first navigation covering the primary DJ workflow.
- Replacement of the settings modal with an inline, non-blocking panel.

Out of scope:

- Wide mode (opt-in) defined in the UX design specification §10.2.
- A light theme — dark is the default and only theme for this change.
- Touch/mobile support.
- Drag-to-reorder queue items (keyboard reorder shipped instead).
- Any framework migration — the app stays vanilla JS + HTML + CSS.

## Approach

Replace the horizontal panel split with one vertical flex column (`#app`) that
contains a fixed header, a single scrollable main column
(`.main-column`), and a fixed status footer. Clamp the window width with both
Tauri window settings and a CSS `max-width`. Move the transport, progress and
volume controls into a compact "Now Playing" section between results and queue,
and convert the settings overlay into an inline collapsible panel. No new
runtime dependencies were introduced.
