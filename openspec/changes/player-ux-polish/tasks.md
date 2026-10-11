# Tasks: Player UX polish

## 1. Pure helpers (test-first, vitest)

- [x] 1.1 `formatCount()` — thousands-separated counts for every number the UI
      shows (status bar, scan summary, results count, queue count).
- [x] 1.2 `describeScanReport()` + `scanCategoryLabel()` — plain-language
      summary, problems separated from skipped files, per-category detail rows
      with a truncation cap.
- [x] 1.3 `describeResults()` — heading/count/hint plus the three empty
      states and the action that resolves each.
- [x] 1.4 `describeQueue()` and `queueBadgeFor()` — queue count, next-up
      label, duplicate counts, playing marker.
- [x] 1.5 `describePlayback()` — state chip label and which transport controls
      can act in each state.
- [x] 1.6 `describeEngine()` and `describePlaybackError()` — runtime jargon
      out, named fixes in.
- [x] 1.7 `needsRescan()` + `RESCAN_KEYS`, `SHORTCUTS` binding list,
      `SongQueue.insert()` for undo.

## 2. UI wiring (`src/web/src/app.js`)

- [x] 2.1 Browse the library when the search box is empty; run queries through
      one `runSearch()` path; cache the browse page until the library changes.
- [x] 2.2 Render the three empty states with their actions (`Add folder`,
      `Clear search`, `Show all formats`).
- [x] 2.3 Song rows: badge, title, filename, play/queue buttons, accessible
      labels, and a queue/playing marker kept in sync outside a re-render.
- [x] 2.4 Queue rows: position, play/remove buttons, selection, `Delete`,
      `Alt`+`↑`/`Alt`+`↓`, `Undo` on remove and on clear, duplicate notice,
      and removal from the queue when a song starts from it.
- [x] 2.5 Transport: `renderTransport()` drives the state chip and the
      disabled/enabled state of every control; failed loads offer `Retry`.
- [x] 2.6 Status and notices: `setStatus()` for the persistent line,
      `notify()` for non-blocking feedback with an action; engine status uses
      application language.
- [x] 2.7 Scan feedback: busy state on the library actions, `Scanning
      library…`/`Library scan complete — N songs`, friendly summary, details
      chip with grouped paths, clear action.
- [x] 2.8 Settings: grouped panel, `rescan` tags and the rescan note with a
      `Rescan library now` button, two-step `Replace library` confirmation
      with its hint, and the rendered shortcut reference.
- [x] 2.9 Keyboard: one handler per binding dispatched in a fixed order, a
      queue-aware arrow/`Esc` model, and shortcuts suppressed while typing
      except `/` and `Ctrl`/`Cmd`+`K`.

## 3. Markup and styles (`src/web/index.html`)

- [x] 3.1 Region layout hooks (library / now playing / queue), notices bar,
      playback-state chip, results count and hint, empty-state container.
- [x] 3.2 Grouped settings panel with the rescan note and the shortcuts list.
- [x] 3.3 `aria-label` on every icon-only control; focus styles; `.btn-danger`
      for the armed replace button; status/notice colour by kind.

## 4. Verification

- [x] 4.1 vitest: helper and wording cases plus the `index.html` wiring
      contract (ids, labels, rescan tags) — 89 tests.
- [x] 4.2 pytest (exit 0), ruff check + format (clean), `build-web.py` asset
      validation (exit 0), `mkdocs build --strict` (exit 0),
      `openspec validate --all --strict` (12/12), `cargo check` (exit 0).
- [x] 4.3 Dev-server smoke test in the real browser at 380 px and 300 px:
      browsing, search, filters, the three empty states, scan details, queue
      operations, transport, settings and the fail-to-play recovery path,
      with hit-testing, overflow and contrast probes.
- [ ] 4.4 Screenshots of each state — blocked: the preview webview produced
      no composited frames in this environment, so the layout evidence is
      DOM geometry (rects, hit-tests, scroll width, canvas ratio).
- [x] 4.5 Docs: user guide (layout, browsing, empty states, queue rules,
      settings groups, shortcuts, status/notices, troubleshooting).
- [x] 4.6 OpenSpec: this change folder (proposal, tasks, delta spec).
