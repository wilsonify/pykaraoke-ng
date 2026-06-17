# Feature Specification: Slim Sidebar Layout

> **Feature ID:** 002
> **Branch:** `002-slim-sidebar-layout`
> **Status:** Specified
> **Author:** —
> **Date:** 2026-02-28
> **Governance:** [constitution.md](../../constitution.md) §2, [ux-design.md](../../ux-design.md)

---

## 1. Problem Statement

### What problem does this solve?

The current PyKaraoke-NG frontend uses a **two-panel horizontal flexbox**
layout (`.left-panel` / `.right-panel`) inside a 1024 × 768 default window.
This layout:

1. **Consumes most of the screen.** A DJ cannot run primary DJ software
   alongside a 1024 px-wide karaoke window on a typical 1366–1920 px laptop.
2. **Splits attention horizontally.** The DJ must scan left-to-right to
   correlate search results with playback state — an unnatural flow during
   live performance.
3. **Violates the project's constitutional design posture** (§2.2), which
   requires a slim, vertically-stacked utility panel.

### Who is affected?

Working DJs who run PyKaraoke-NG alongside other software during live events.
This is the project's **primary persona** (constitution §2.1).

### What is the desired outcome?

A single-column, vertically-stacked layout that:

- Defaults to 380 px wide (configurable 300–450 px).
- Stacks all controls top → bottom in the order defined in
  [ux-design.md](../../ux-design.md) §4.
- Leaves the remaining screen for the DJ's primary software.
- Is fully functional without horizontal scrolling.

---

## 2. Acceptance Criteria

### Layout

- [ ] The root layout container enforces `flex-direction: column`.
- [ ] No horizontal panel splits exist in the default layout.
- [ ] The Tauri window defaults to 380 × 768 px.
- [ ] The window has `minWidth: 300`, `maxWidth: 450`, `minHeight: 500`.
- [ ] All primary controls are left-aligned.
- [ ] No element has `text-align: center` or `margin: 0 auto`.

### Vertical Flow

- [ ] Elements appear in this order: Search → Filters → Results →
      Now Playing → Queue → Status.
- [ ] Search bar is fixed at the top (does not scroll).
- [ ] Status bar is fixed at the bottom (does not scroll).
- [ ] Now Playing section uses `position: sticky`.
- [ ] Results and Queue scroll vertically within the remaining space.

### Dimensional Behaviour

- [ ] The app is fully functional at 300 px width.
- [ ] The app does not expand beyond 450 px unless the user explicitly
      overrides `maxWidth`.
- [ ] Song titles truncate with ellipsis (no horizontal overflow).
- [ ] No horizontal scrollbar appears at any supported width.

### Visual Density

- [ ] List item height ≤ 32 px.
- [ ] Section gap ≤ 4 px.
- [ ] Search bar height ≤ 36 px.
- [ ] No element has padding > 8 px on any side.

### Keyboard Navigation

- [ ] `/` or `Ctrl+K` focuses the search bar from anywhere.
- [ ] `↑` / `↓` navigate search results.
- [ ] `Enter` adds the selected result to the queue.
- [ ] `Esc` clears the search input.
- [ ] `Space` toggles play/pause.
- [ ] `Tab` cycles focus between sections.

### Prohibited Patterns

- [ ] No modal dialogs exist in the primary workflow.
- [ ] No full-screen overlays exist.
- [ ] No confirmation dialogs for queue add/remove.
- [ ] No horizontal `flex-direction: row` on the root container.
- [ ] No `width: 100%` without a corresponding `max-width`.

---

## 3. Edge Cases

| Case | Expected behaviour |
|------|--------------------|
| Empty search query | Show "Type to search" placeholder |
| No search results | Show "No songs found" message inline |
| Empty queue | Show "Queue empty" hint inline |
| Queue with 50+ songs | Queue scrolls; Now Playing stays sticky |
| Song title > 40 chars | Truncate with ellipsis |
| Window resized to 300 px | All elements remain functional; text truncates |
| Window resized to 450 px | Slightly more text visible; layout unchanged |
| Window resized > 450 px | Stops at 450 px (maxWidth enforced) |
| Backend disconnected | Status bar shows "Disconnected" — rest of UI remains usable |
| Rapid keystrokes in search | Debounce prevents excessive updates (100–150 ms) |

---

## 4. Failure Modes

| Failure | Mitigation |
|---------|-----------|
| CSS specificity conflict overrides max-width | Integration test asserts computed max-width |
| Sticky now-playing overlaps content | Test scroll position with populated results + queue |
| Keyboard shortcuts conflict with OS/Tauri shortcuts | Map of reserved keys; test each binding |
| Virtual scroll breaks with < 5 results | Ensure plain rendering below threshold |
| Window manager ignores Tauri minWidth/maxWidth | Document as known platform limitation |

---

## 5. Out of Scope

- **Wide mode toggle.** Defined in [ux-design.md](../../ux-design.md) §10.2
  but deferred to a future feature.
- **Light theme.** Dark theme is the default and only theme for this feature.
- **Touch/mobile support.** Desktop-only.
- **Drag-to-reorder queue.** Keyboard reorder is in scope; drag-and-drop is
  a separate feature.
- **React/framework migration.** This feature refactors the existing vanilla
  JS + HTML. Framework migration is a separate decision.

---

## 6. References

- [Constitution §2 — Target Audience and Design Posture](../../constitution.md)
- [UX Design Specification](../../ux-design.md)
- Current layout: `src/runtimes/tauri/src/index.html` (two-panel flexbox)
- Current CSS: `src/runtimes/tauri/src/styles.css` (422 lines, horizontal layout)
- Current app logic: `src/runtimes/tauri/src/app.js` (monolithic class)
- Tauri window config: `src/runtimes/tauri/src-tauri/tauri.conf.json`
