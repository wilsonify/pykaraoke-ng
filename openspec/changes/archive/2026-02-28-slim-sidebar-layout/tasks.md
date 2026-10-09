# Tasks

> Archived change — every item below is complete.

## 1. Test Scaffolding (Red)

- [x] 1.1 Add DOM-structure tests asserting the single-column vertical flow (header → search → results → player → queue → status) in `src/web/index.html`.
- [x] 1.2 Add CSS-constraint tests asserting `#app` is a flex column with `max-width: 450px` and that no horizontal panel split remains.
- [x] 1.3 Add keyboard-shortcut tests for `/` (focus search), `Escape` (clear), `ArrowUp`/`ArrowDown` (navigate), `Enter` (queue), and `Space` (play/pause).
- [x] 1.4 Add a Tauri-config test asserting the window dimensions (`width: 380`, `height: 800`, `minWidth: 300`, `maxWidth: 450`, `minHeight: 500`).

## 2. Implementation (Green)

- [x] 2.1 Replace the two-panel DOM with the single-column structure (`#app`, `.app-header`, `.main-column`, `.status-bar`) in `src/web/index.html`.
- [x] 2.2 Rewrite the layout CSS: remove `.left-panel`/`.right-panel`/`#main-content` rules; add the `#app` vertical flex column, `.main-column` `overflow-y: auto`, compact spacing, and text-truncation rules; keep the colour custom properties.
- [x] 2.3 Update the UI selectors and update methods for the new markup; remove all references to `.left-panel` and `.right-panel`.
- [x] 2.4 Add the `document` `keydown` handler dispatching `/`, `Escape`, `ArrowUp`/`ArrowDown`, `Enter`, `Space`, `Delete`, and the `Ctrl`-modified reorder/skip bindings.
- [x] 2.5 Update the Tauri window configuration (`width: 380`, `height: 800`, `minWidth: 300`, `maxWidth: 450`, `minHeight: 500`).
- [x] 2.6 Replace the settings modal with the inline collapsible `#settings-panel` toggled from the header button.
- [x] 2.7 Introduce the compact Now Playing section (stage, transport buttons, progress slider, volume slider) between results and queue.

## 3. Refactor

- [x] 3.1 Delete dead CSS referencing the removed elements (`.left-panel`, `.right-panel`, `#main-content`, `.settings-modal`, `.modal-overlay`).
- [x] 3.2 Delete dead JS referencing removed DOM elements and the old two-panel layout logic.
- [x] 3.3 Lint and format all modified files; ensure no warnings.
- [x] 3.4 Confirm the full test suite passes.

## 4. Integration

- [x] 4.1 Cross-platform window check: window opens at the configured size and satisfies the 300–450 px width clamp on Linux, macOS, and Windows (CSS `max-width` as fallback where the window manager ignores hints).
- [x] 4.2 Content-overflow check: with many search results and a long queue, `.main-column` scrolls vertically with no horizontal scrollbar.
- [x] 4.3 Keyboard end-to-end walkthrough: focus search → type query → select with `ArrowDown` → queue with `Enter` → clear with `Escape` → play with `Space` → skip with `Ctrl+ArrowRight`, all without a mouse.

## 5. Layout Compliance (constitution §2.3 / UX design §4)

- [x] 5.1 Single vertical column layout — no horizontal splits.
- [x] 5.2 Strict left alignment for primary controls — no centered primary controls. (Lyric text inside the stage is centered intentionally; it is not a primary control.)
- [x] 5.3 Slim default window — 380 px wide, clamped to 300–450 px.
- [x] 5.4 No full-screen takeovers — the settings modal was replaced by an inline panel.
- [x] 5.5 Keyboard-first — all primary actions reachable from the keyboard.
- [x] 5.6 Instant search — incremental, debounced filtering on keypress.
- [x] 5.7 Zero mode switching — search, queue and playback live in one view.
- [x] 5.8 Compact visual density per the UX design specification §6.
- [x] 5.9 No screen dominance — `max-width` enforced in CSS and Tauri config.
- [x] 5.10 Dockable workflow — functional when the window is snapped to a screen edge.

## 6. Documentation, Validation and Cross-Platform

- [x] 6.1 Update `src/runtimes/tauri/README.md` to describe the new layout.
- [x] 6.2 Update `docs/architecture/overview.md` where it referenced the old layout.
- [x] 6.3 Complete the feature completion checklist (all items verified).
- [x] 6.4 SonarQube quality gate passes with zero new issues.
- [x] 6.5 All unit and integration tests pass; coverage ≥ 95% for new/modified code.
- [x] 6.6 No new lint warnings.
- [x] 6.7 CI pipeline passes on Linux, Windows, and macOS.
- [x] 6.8 No shell-specific commands introduced into cross-platform build configuration.
- [x] 6.9 Window dimensions verified on Linux, macOS, and Windows; CSS `max-width` fallback works on all platforms.
- [x] 6.10 Code reviewed and approved; PR description referenced the spec artifacts.
