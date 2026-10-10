# Tasks: Presenter / stage output window

## 1. Pure pieces and tests (vitest)

- [ ] 1.1 `buildStageSnapshot(...)` (pure): tests for field mapping,
      singer inclusion, version field, and no lyric text leakage in the
      frequent payload.
- [ ] 1.2 Stage bridge module: mock channel (`BroadcastChannel` +
      `postMessage` fallback) tests for snapshot send, handshake reply,
      unknown-version ignore, and open-failure status path.

## 2. Stage page

- [ ] 2.1 `src/web/stage.html`: dark full-bleed layout (header, 3 lyric
      lines, footer timing, CDG canvas area, idle state).
- [ ] 2.2 `src/web/stage.js`: listen/handshake/render diff logic; graceful
      exit when the main window goes away.

## 3. Main-window wiring (index.html)

- [ ] 3.1 Stage control button in the header with accessible label;
      `openStageWindow`/`toggleStageWindow` (Tauri + browser paths),
      popup-blocked status message.
- [ ] 3.2 Snapshot pushes: line/syllable changes, throttled transport tick,
      song start/stop, CDG tile snapshots; reply to `stage-hello`.

## 4. Verification

- [ ] 4.1 vitest green; pytest green (no Python changes expected).
- [ ] 4.2 Build check that `stage.html` is included in the packaged web
      assets (`asset gathering`/Tauri dist list) so the desktop bundle
      ships it.
