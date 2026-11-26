# Tasks: Lyrics timing resilience

## 1. Spec delta

- [x] 1.1 Restate LRC parsing with the tolerated timestamp forms and counted
      warnings.
- [x] 1.2 Add requirements for ELRC line-header inference and for `.elrc`
      matching warnings.
- [x] 1.3 Restate the lyrics display requirement: past/current/next, click to
      seek, lyric size, active line kept in view.

## 2. Engine (`src/pykaraoke/lrc.py`)

- [x] 2.1 One `_TIMESTAMP` pattern for line tags, `.elrc` entries and word
      tags; fraction optional, `.` or `:` separator, 1–3 digit minutes.
- [x] 2.2 `_tag_ms()` accepts a missing fraction.
- [x] 2.3 `parse_lrc()` reports `warnings` for timed-looking lines it skipped.
- [x] 2.4 `parse_elrc()` accepts an optional `warnings` list for unmatched
      entries; headers are never counted.
- [x] 2.5 `parse_elrc_lines()` — infer display lines from an `.elrc` alone.

## 3. Boundary (`src/pykaraoke/webapp.py`)

- [x] 3.1 `parse_lrc()` falls back to `.elrc` line inference when the `.lrc`
      has no timed lines.
- [x] 3.2 Merged warnings are returned in the payload.

## 4. Web (`src/web/src/helpers.js`, `app.js`)

- [x] 4.1 `lyricWindow()` pure helper (past/current/next + lit count).
- [x] 4.2 `createPlaybackGuard()` pure helper (used by the lifecycle work).
- [x] 4.3 Lyric renderer: three rows rebuilt on line change, syllable
      `lit` toggled by delta, previous line dimmed above.
- [x] 4.4 Click a lyric line to seek; disabled when seeking is unavailable.
- [x] 4.5 Active line kept in view without scrolling the page.
- [x] 4.6 `lyric_size` setting (small/medium/large), persisted and applied.
- [x] 4.7 Settings row in `index.html`; CSS overrides per size.

## 5. Regression tests

- [x] 5.1 `tests/pykaraoke/test_lrc.py`: fraction-less, colon-fraction,
      long-minute and word-tag variants; warnings for bad lines.
- [x] 5.2 `tests/pykaraoke/test_lrc.py`: ELRC header inference.
- [x] 5.3 `tests/fixtures/lrc/` fixtures for each variant.
- [x] 5.4 `tests/web/app.test.js`: `lyricWindow`, guard, and the new setting
      id in the wiring contract.

## 6. Documentation

- [x] 6.1 `docs/reference/formats.md` timestamp variants and ELRC headers.
- [x] 6.2 `docs/reference/engine-api.md` `warnings` payload.
- [x] 6.3 `docs/architecture/web-app.md` lyric window and playback lifecycle.
- [x] 6.4 User guide: lyric size and click-to-seek.

## 7. Verification

- [x] 7.1 `python -m pytest -q` green.
- [x] 7.2 `npx vitest run` green.
- [x] 7.3 `ruff`, `mypy`, `openspec validate --all --strict`.
