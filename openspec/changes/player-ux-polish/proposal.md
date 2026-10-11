# Proposal: Player UX polish — find, play, and manage the queue

> Status: implemented — verified locally, awaiting archive.
> Capabilities: `ux-slim-sidebar`
> Related: `scan-diagnostics-and-filters` (archived) shipped the scan report
> the UI now presents; this change adds no engine surface.

## Intent

The engine and the state handling were in good shape, but the page talked
about itself instead of about the songs. A first-time user met
`PyScript: ready` in the status bar, an empty result area whose only content
was the prompt "Type to search your library", and a scan summary that read
`2382 unsupported`. Nothing in the window said what the library contained,
which song was playing, or why a file had been skipped, and several
documented bindings did not do what the spec said (`Delete` looked for a
selected queue row that the UI never marked; `Ctrl`+`↑`/`Ctrl`+`↓` moved the
first or last queue entry instead of the selected one; `Esc` emptied the
result list rather than returning to browsing).

This change makes the window answer four questions without configuration:
what is in the library, what is playing, what comes next, and what to do when
something fails.

## Scope

In scope:

* **Browsable library.** An empty search box browses the library (first 300
  songs, with a hint that typing searches the rest) instead of prompting.
* **Three distinct empty states.** Library not scanned yet (with an
  `Add folder` action), no search matches (with `Clear search`), and matches
  hidden by the format filters (with `Show all formats`).
* **Song rows that show state.** Format badge, title, filename, explicit
  `Play now` / `Add to queue` buttons, and a `queued`, `queued ×N`, or
  `playing` marker that stays in sync as the queue changes.
* **Queue control.** One-based positions, an `Up next: …` hint, per-row play
  and remove, row selection (so `Delete` and `Alt`+`↑`/`Alt`+`↓` act on the
  selected entry), `Undo` for removals and for clearing, and duplicate-aware
  queueing. A song played from the queue leaves the queue.
* **Transport availability and state.** A state chip (`Nothing loaded`,
  `Playing`, `Paused`, `Playback failed`), controls that cannot act disabled
  rather than failing on click, `Play` relabelling to `Pause`/`Retry`, and a
  plain-language playback error with a `Retry` action.
* **Human scan diagnostics.** A plain-language summary (thousands separators,
  singular/plural labels, problems separated from files that were simply
  skipped) plus a `Scan details (N)` chip that expands the grouped file list
  and survives dismissal of the notice.
* **Status and notices.** Application-level status text (`Ready`,
  `Scanning library…`, `Library scan complete — 272 songs`, `Playback error`)
  and a non-blocking notice bar for routine results with `Undo`/`Retry`/`See
  details` actions.
* **Grouped settings.** Library and scanning, Song names, Playback and
  display, Advanced file filters, and Keyboard shortcuts; a `rescan` tag on
  the settings that only apply at the next scan with a note offering to
  rescan now; and a two-step confirmation for the destructive `Replace
  library`.
* **Shortcut reference** rendered from a single list of bindings, unit-tested
  against the handlers.

Out of scope:

* Any change to scanning, filename parsing, CD+G/MIDI/LRC decoding, the
  `window.pykaraoke_api` contract, or offline operation.
* Playing songs that live inside a ZIP archive (still listed but unplayable,
  now reported in plain language).
* Reworking the `Playback` capability (pitch, tempo, countdown) — that is the
  `playback-pitch-tempo-countdown` change.

## Approach

All presentation logic stays in the page; the Python engine is untouched. New
pure helpers (`formatCount`, `describeScanReport`, `describeResults`,
`describeQueue`, `describePlayback`, `describeEngine`, `describePlaybackError`,
`needsRescan`, `queueBadgeFor`, `SHORTCUTS`) live in `src/web/src/helpers.js`
and are unit-tested, so wording and control-availability rules are testable
without a DOM; `app.js` only places their results into elements it creates
with `textContent`, which also removes the last `innerHTML` interpolation of
song metadata. Song removal/restore uses the queue's own `insert()` so the
`SongQueue` contract stays the only way the queue is mutated.

`index.html` gains the three-region layout hooks, the notice bar, the grouped
settings panel with the rescan note, and `aria-label`s on every icon-only
control. A vitest case reads both files and asserts the DOM contract
(every id `app.js` looks up exists, icon controls are labelled, rescan-tagged
setting rows say so), so a rename that breaks the wiring fails the suite
instead of silently disabling a control.

Three stale `> Note:` divergences in the current `ux-slim-sidebar` spec are
retired by the delta: the ineffective `Delete` binding, the first/last-only
`Ctrl`-arrow reorder, and the empty-query prompt.
