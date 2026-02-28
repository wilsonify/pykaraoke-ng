# Task Breakdown: Slim Sidebar Layout

> **Feature ID:** 002
> **Branch:** `002-slim-sidebar-layout`
> **Date:** 2026-02-28

---

## Phase 1: Test Scaffolding (Red)

### Task 1.1 — DOM structure tests
Write tests asserting the target vertical flow element order:
`#search-section` → `#search-filters` → `#content-scroll` →
(`#search-results`, `#now-playing`, `#queue-section`) → `#status-bar`.

**File:** `src/runtimes/tauri/src/index.test.js`

### Task 1.2 — CSS constraint tests
Write tests asserting:
- `#app` has `flex-direction: column`
- `#app` has `max-width` ≤ 450 px
- No element has `text-align: center`
- `#now-playing` has `position: sticky`

**File:** `src/runtimes/tauri/src/index.test.js`

### Task 1.3 — Keyboard shortcut tests
Write tests for each keyboard binding:
- `/` focuses search
- `Esc` clears search
- `↑/↓` navigate results
- `Enter` queues selected result
- `Space` toggles play/pause

**File:** `src/runtimes/tauri/src/app.test.js`

### Task 1.4 — Tauri config tests
Write integration test asserting `tauri.conf.json` window dimensions:
`width: 380`, `height: 768`, `minWidth: 300`, `maxWidth: 450`, `minHeight: 500`.

**File:** `tests/integration/` (existing integration test location)

---

## Phase 2: Implementation (Green)

### Task 2.1 — Rewrite `index.html` DOM structure
Replace the two-panel horizontal layout with the single-column vertical
structure defined in `plan.md` §2.1.

**File:** `src/runtimes/tauri/src/index.html`

### Task 2.2 — Rewrite `styles.css` layout rules
- Remove `.left-panel`, `.right-panel`, `#main-content` styles.
- Add `#app` vertical flex column with max-width.
- Add `#content-scroll` overflow-y.
- Add `#now-playing` sticky positioning.
- Add compact spacing per `ux-design.md` §6.2.
- Add text truncation rules.
- Preserve colour custom properties.

**File:** `src/runtimes/tauri/src/styles.css`

### Task 2.3 — Update `app.js` DOM selectors
- Update all `querySelector` / `getElementById` calls for renamed/moved
  elements.
- Remove references to `.left-panel` / `.right-panel`.
- Ensure all UI update methods target the new DOM IDs.

**File:** `src/runtimes/tauri/src/app.js`

### Task 2.4 — Add keyboard shortcut handlers
- Add `keydown` event listener on `document`.
- Implement shortcut dispatch: `/`, `Esc`, `↑`, `↓`, `Enter`, `Space`.
- Add focus management between sections via `Tab`.

**File:** `src/runtimes/tauri/src/app.js`

### Task 2.5 — Update Tauri window configuration
Change `tauri.conf.json` window settings:
```json
"width": 380, "height": 768,
"minWidth": 300, "maxWidth": 450, "minHeight": 500
```

**File:** `src/runtimes/tauri/src-tauri/tauri.conf.json`

### Task 2.6 — Replace settings modal with inline section
- Remove the overlay modal from `index.html`.
- Add a collapsible `#settings-section` above `#status-bar`.
- Update `app.js` to toggle visibility instead of show/hide modal.

**File:** `src/runtimes/tauri/src/index.html`, `app.js`, `styles.css`

---

## Phase 3: Refactor

### Task 3.1 — Remove dead CSS
Delete all styles that reference removed elements (`.left-panel`,
`.right-panel`, `#main-content`, `.settings-modal`, `.modal-overlay`).

**File:** `src/runtimes/tauri/src/styles.css`

### Task 3.2 — Remove dead JS
Delete all code in `app.js` that references removed DOM elements or the
old two-panel layout logic.

**File:** `src/runtimes/tauri/src/app.js`

### Task 3.3 — Lint and format
Run linting on all modified files. Ensure no warnings.

### Task 3.4 — Verify all tests pass
Run full test suite. All Phase 1 tests must be green.

---

## Phase 4: Integration

### Task 4.1 — Cross-platform window test
Build and launch on Linux, macOS, Windows. Verify:
- Window opens at 380 × 768.
- Window cannot be resized wider than 450 px.
- Window cannot be resized narrower than 300 px.

### Task 4.2 — Content overflow test
- Add 100+ search results.
- Add 20+ queue items.
- Verify vertical scroll works.
- Verify Now Playing stays visible (sticky).
- Verify no horizontal scrollbar.

### Task 4.3 — Keyboard navigation end-to-end
Walk through the full DJ workflow:
1. Launch → search bar focused.
2. Type query → results appear.
3. `↓` to select → `Enter` to queue.
4. `Esc` to clear search.
5. `Space` to play.
6. `Ctrl+→` to skip.
Verify all steps work without mouse.

---

## Phase 5: Documentation & Validation

### Task 5.1 — Update README
Update `src/runtimes/tauri/README.md` to describe the new layout.

### Task 5.2 — Update architecture docs
Update `docs/architecture/overview.md` if it references the old layout.

### Task 5.3 — Completion checklist
Fill out `checklist.md` with all items verified.

### Task 5.4 — SonarQube
Verify quality gate passes with zero new issues.
