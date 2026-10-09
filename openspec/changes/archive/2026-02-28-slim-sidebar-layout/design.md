# Design: Slim Sidebar Layout

## Technical Approach

The shipped application is a **single self-contained file**, `src/web/index.html`,
holding the markup, the inline `<style>`, the vanilla-JS module, and the
PyScript bridge. There is no separate `styles.css` or `app.js`.

## Architecture Decisions

### Decision: Single vertical column in `#app`

`#app` is a flex column at `height: 100vh`, `width: 100%`, `max-width: 450px`.
The page is split into three regions:

| Region | Selector | Behaviour |
|--------|----------|-----------|
| Fixed top | `.app-header` | Title, **＋ Folder**, settings button — never scrolls |
| Scrollable middle | `.main-column` | `flex: 1 1 auto; overflow-y: auto` — the only scroll container |
| Fixed bottom | `.status-bar` | `#status-message`, `#engine-status` — never scrolls |

Everything the DJ works with lives inside `.main-column`, top to bottom:
`#library-filters` (collapsible `<details>`), `.search-section`
(`#search-input` plus CDG/KAR/MPG/LRC kind filters), `.results-section`
(`#results-list`), `.player-section` (the `#stage` canvas/lyrics/video,
`#current-song-title`/`#current-song-artist`, `.player-controls`,
`.progress-row`, `.volume-row`), and `.queue-section` (`#queue-list`).

- **Rationale:** one scroll container means no nested scrollbars, no horizontal
  split, and a predictable top-to-bottom reading order during a live set.

### Decision: Compact density over whitespace

Section labels are 11 px uppercase, song rows use ellipsis truncation, and
transport controls are icon-only buttons. Long titles truncate rather than
widening the layout.

- **Rationale:** information density is the DJ's priority; the window is only
  300–450 px wide.

### Decision: Settings as an inline panel, not a modal

`#settings-panel` is a sibling of `#app`, toggled with the `hidden` attribute
from the header's settings button. It contains sort order, CDG zoom, and the
scan-related toggles.

- **Rationale:** the constitution bans modal dialogs in the primary workflow;
  settings must never block search, queue, or playback.

### Decision: Width clamped in two places

`tauri.conf.json` sets `width: 380, minWidth: 300, maxWidth: 450, minHeight: 500`,
and the CSS independently sets `#app { max-width: 450px }`.

- **Rationale:** some window managers ignore min/max hints; the CSS constraint
  is the reliable fallback.

### Decision: Keyboard-first workflow

A single `keydown` listener on `document` implements the primary shortcuts:
`/` or `Ctrl/Cmd+K` focus search, `Escape` clear search, `Space` play/pause,
`Enter` queue the selected result, `ArrowUp`/`ArrowDown` navigate,
`Ctrl+ArrowUp`/`Ctrl+ArrowDown` reorder the queue, `Ctrl+ArrowRight` next,
`Delete` remove. Search input is debounced.

- **Rationale:** the DJ must search, queue, and play without a mouse.

## Migration Note

The original plan targeted a three-file frontend (`src/runtimes/tauri/src/index.html`,
`src/runtimes/tauri/src/styles.css`, `src/runtimes/tauri/src/app.js`) and
specific element ids (`#search-section`, `#content-scroll`, `#now-playing`,
`#queue-section`, `#status-bar`) plus a `position: sticky` Now Playing section.

> Note: those paths and ids were superseded when the frontend was consolidated
> into the single file `src/web/index.html`. The shipped markup uses
> `.app-header` / `.main-column` / `.player-section` / `.queue-section` /
> `.status-bar` and class-based sections instead of those ids. The shipped Now
> Playing section scrolls with `.main-column` rather than being sticky, and the
> shipped default window height is **800** px (the plan said 768). The
> single-column, slim-width, keyboard-first and no-modal requirements all hold
> as specified.

Removed from the old layout: the horizontal `#main-content` flex container, the
`.left-panel` / `.right-panel` split, and the `#settings-modal` overlay.
