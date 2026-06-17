# Technical Plan: Slim Sidebar Layout

> **Feature ID:** 002
> **Branch:** `002-slim-sidebar-layout`
> **Date:** 2026-02-28

---

## 1. Technology Stack

| Concern     | Choice                    | Rationale                               |
|-------------|---------------------------|-----------------------------------------|
| Language    | Vanilla JavaScript (ES6+) | Matches existing codebase; no framework migration |
| Markup      | HTML5                     | Existing approach; served directly by Tauri |
| Styling     | CSS custom properties     | Existing approach; no Tailwind or preprocessor |
| Testing     | Node built-in test runner | Matches existing `app.test.js` pattern |
| Window      | Tauri v1 `tauri.conf.json`| Existing configuration mechanism |

No new dependencies are introduced.

## 2. Architecture

### 2.1 DOM Structure (target)

Replace the current two-panel flexbox with a single vertical column:

```html
<div id="app">
  <!-- Fixed top -->
  <header id="search-section">
    <input id="search-input" type="text" placeholder="Search songs..." />
    <button id="toggle-filters" aria-label="Toggle filters">▼</button>
  </header>

  <!-- Collapsible -->
  <section id="search-filters" class="collapsed">
    <!-- Filter chips: format, artist, etc. -->
  </section>

  <!-- Scrollable content -->
  <main id="content-scroll">
    <section id="search-results">
      <ul id="results-list" role="listbox"></ul>
    </section>

    <!-- Sticky within scroll -->
    <section id="now-playing" class="sticky-section">
      <div id="song-info"><!-- title, artist --></div>
      <div id="transport"><!-- play/pause, skip, progress, volume --></div>
    </section>

    <section id="queue-section">
      <h2 class="section-label">Queue</h2>
      <ul id="queue-list" role="listbox"></ul>
    </section>
  </main>

  <!-- Fixed bottom -->
  <footer id="status-bar">
    <span id="status-message"></span>
    <span id="connection-indicator"></span>
  </footer>
</div>
```

### 2.2 CSS Layout Strategy

```
#app                    → flex column, 100vh, max-width 450px
  #search-section       → flex-shrink: 0 (fixed height)
  #search-filters       → flex-shrink: 0, display: none when collapsed
  #content-scroll       → flex: 1, overflow-y: auto
    #search-results     → natural flow
    #now-playing        → position: sticky, top: 0
    #queue-section      → natural flow
  #status-bar           → flex-shrink: 0 (fixed height)
```

### 2.3 Key CSS Rules

```css
:root {
  --sidebar-min-width: 300px;
  --sidebar-max-width: 450px;
  --sidebar-default-width: 380px;
}

#app {
  display: flex;
  flex-direction: column;
  width: 100vw;
  max-width: var(--sidebar-max-width);
  min-width: var(--sidebar-min-width);
  height: 100vh;
  overflow: hidden;
}

#content-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

#now-playing {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg-surface);
}

/* Left-alignment enforcement */
#app * {
  text-align: left;
}

/* Ellipsis for long text */
.song-title, .song-artist {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

## 3. Files to Modify

| File | Change |
|------|--------|
| `src/runtimes/tauri/src/index.html` | Replace two-panel DOM with single-column structure |
| `src/runtimes/tauri/src/styles.css` | Rewrite layout CSS; keep color variables; remove `.left-panel`/`.right-panel` |
| `src/runtimes/tauri/src/app.js` | Update DOM selectors; add keyboard shortcut handlers; refactor UI update methods for new DOM structure |
| `src/runtimes/tauri/src-tauri/tauri.conf.json` | Change window dimensions: width 380, add minWidth/maxWidth/minHeight |

| File | Change |
|------|--------|
| `src/runtimes/tauri/src/app.test.js` | Update tests for new DOM structure and element IDs |
| `src/runtimes/tauri/src/index.test.js` | Update element presence tests |

## 4. Data Structures

No data structure changes. The application state (songs, queue, playback)
remains identical. Only the DOM representation changes.

## 5. Testing Strategy

### 5.1 Unit Tests

- **DOM structure tests:** Assert element order matches the vertical flow.
- **CSS constraint tests:** Assert `max-width`, `flex-direction`, alignment.
- **Keyboard handler tests:** Assert each shortcut triggers the correct action.
- **Truncation tests:** Assert long titles show ellipsis, no overflow.

### 5.2 Integration Tests

- **Window dimension test:** Launch Tauri app, assert window dimensions
  match config (380 × 768, min/max enforced).
- **Scroll behaviour test:** Populate results + queue, assert scroll
  container scrolls vertically, Now Playing stays visible.
- **Cross-platform layout test:** Screenshot comparison on Linux, macOS,
  Windows (manual or CI visual regression).

### 5.3 Coverage Target

- **95%** for new/modified code.
- **Branch coverage** for keyboard shortcut conditional logic.

## 6. Error Handling

- **Keyboard shortcuts:** Fail silently if the target element doesn't exist
  (defensive `querySelector` checks).
- **Sticky positioning:** If `position: sticky` is unsupported (unlikely in
  Tauri's Chromium), fall back to `position: relative` — Now Playing will
  scroll with content. Acceptable degradation.
- **Window hints ignored:** CSS `max-width` is the primary enforcement;
  Tauri `maxWidth` is supplementary. Both must be set.

## 7. Migration Notes

### Removed DOM Elements

| Old Element | Disposition |
|-------------|------------|
| `#main-content` (horizontal flex container) | Removed entirely |
| `.left-panel` | Removed; contents moved to `#search-section` + `#search-results` |
| `.right-panel` | Removed; contents split into `#now-playing` + `#queue-section` |
| `#settings-modal` (overlay) | Replaced with collapsible inline section |

### Preserved DOM Elements

| Element | Notes |
|---------|-------|
| `#search-input` | Same ID, moved to `#search-section` |
| `#results-list` | Same ID, moved to `#search-results` |
| `#queue-list` | Same ID, moved to `#queue-section` |
| `#status-message` | Same ID, moved to `#status-bar` |
| Transport controls | Same IDs, moved to `#now-playing > #transport` |
