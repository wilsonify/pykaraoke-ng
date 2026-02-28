# Clarification: Slim Sidebar Layout

> **Feature ID:** 002
> **Branch:** `002-slim-sidebar-layout`
> **Date:** 2026-02-28

---

## Security

- **No new attack surface.** This feature is pure layout/CSS/DOM restructuring.
  No new IPC commands, no new file I/O, no new user input paths.
- **CSP unchanged.** No new script sources or inline styles required.

## Performance

- **Fewer DOM nodes.** Removing the two-panel split reduces DOM complexity.
- **Virtual scrolling concern.** Large search result sets (10,000+ songs)
  need virtual scrolling. This is noted in the spec but the initial
  implementation may use a simple capped list (show top 100 results).
  Virtual scrolling can be added as a follow-up.
- **Sticky positioning.** `position: sticky` is well-supported and
  performant in modern Chromium (Tauri's webview). No polyfill needed.

## Cross-Platform

- **Tauri `maxWidth` on Windows.** Windows may not enforce `maxWidth` in
  all window managers (e.g., when snapping to screen edge). Document as
  known limitation; enforce max-width via CSS as a fallback.
- **Tauri `maxWidth` on macOS.** Tested and supported in Tauri v1 on macOS.
- **Tauri `maxWidth` on Linux.** Depends on window manager. X11/Wayland
  handle hints differently. CSS enforcement is the reliable fallback.
- **Font rendering.** System font stack (`system-ui`) renders differently
  across platforms. Acceptable — we don't require pixel-identical rendering.

## Backward Compatibility

- **Breaking layout change.** Users familiar with the two-panel layout will
  see a fundamentally different UI. This is intentional and motivated by
  the constitutional design posture.
- **No data migration.** Settings, playlists, and library data are unaffected.
- **No API changes.** Tauri IPC commands remain identical.
- **CSS class names.** `.left-panel` and `.right-panel` will be removed.
  Any external tooling that references these class names (unlikely) will break.

## Dependencies

- **No new dependencies.** This feature uses existing vanilla JS, CSS, and
  HTML. No libraries, frameworks, or build tools are added.
- **Tauri v1 window API.** The `minWidth`/`maxWidth`/`minHeight` fields are
  supported in Tauri v1 `tauri.conf.json`. Verified in Tauri docs.

## Ambiguities Resolved

| Question | Resolution |
|----------|-----------|
| Should the settings modal be removed entirely? | No — collapsed into an inline expandable section at the bottom (above status bar). Not a modal overlay. |
| Should the "Add Folder" and "Scan Library" buttons remain? | Yes — moved below search filters as compact icon+text buttons. |
| What happens to the right panel's "Now Playing" display? | Merged into the vertical flow between results and queue. |
| Should the progress bar be visible? | Yes — compact single-line progress bar inside Now Playing. |
| Should volume control be visible? | Yes — small slider or icon-only toggle inside Now Playing. |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Users dislike the layout change | Medium | Low | Constitutional mandate; the design serves the primary persona |
| Tauri window hints ignored by WM | Low | Low | CSS max-width as fallback |
| Sticky positioning breaks in Tauri webview | Low | Medium | Test on all 3 platforms; fall back to fixed positioning |
| Long song titles cause layout overflow | Medium | Low | Text truncation with ellipsis is specified |
