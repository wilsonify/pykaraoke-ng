# Design: Presenter / stage output window

## Window lifecycle

* `openStageWindow()`:
  * Tauri (`__TAURI__` present): `new WebviewWindow('presenter', {url:
    'stage.html', title: 'PyKaraoke NG — Stage', width, height})`; the
    existing `core:default` capability already permits
    `core:webview:allow-create-webview-window`. If construction throws,
    status-bar error.
  * Browser: `window.open('stage.html', 'pykaraoke-stage',
    'popup,width=1280,height=720')`; `null` return → popup blocked →
    status-bar error telling the user to allow popups for this origin.
* `toggleStageWindow()` tracks a handle + `closed` polling (browser) or a
  window label check (Tauri); focus-if-open on repeat activation.
* Stage page on load posts `{type: 'stage-hello'}`; main page replies with
  a full snapshot so a reloaded stage never starts blank mid-song.

## Channel

Single module-level channel created lazily: `BroadcastChannel('pykaraoke-ng-stage')`
when defined, else `window.opener && window.opener.postMessage(..., '*')`
from the stage and `stageWindow.postMessage(..., '*')` from the main page.
Messages: `{type: 'snapshot', payload}`, `{type: 'stage-hello'}`. The main
page ignores messages from unknown types; the stage ignores payloads with a
`v` it does not understand (forward-compat guard).

## Snapshot builder (pure, testable)

```js
buildStageSnapshot({show, song, lineIdx, syllableIdx, positionMs,
                    cdgTiles}) →
{ v: 1, song: {id, title, artist, mime},
  singer: name|null, lineIdx, syllableIdx,
  elapsedMs, totalMs, semitones, tempo, cdgTiles | null }
```

Lyric text itself is **not** shipped in every snapshot: the stage fetches
the song's lyric line array once per song id (it can read the same library
store the main page loaded) and only receives indices thereafter. That keeps
the frequent messages small.

## Stage rendering

* Dark full-bleed layout, large next-line-ahead text (3 lines: previous,
  current with sung/un-sung split, next).
* Header: title — artist · singer; footer: elapsed/remaining/total + key
  readout (read-only).
* CDG mode: mirrored canvas area sized to the viewport; tile snapshots
  blitted on receipt.
* No controls (except a minimal "close" that calls `window.close()`) — the
  stage is for the audience, not the operator.

## Failure behaviour

* No runtime permission for a second window → status message, main app
  unaffected.
* Stage open but channel unavailable → stage shows an idle "Waiting for
  main window…" hint; no crash.
* Main window closed → stage detects channel close/opener gone and shows
  idle state, then exits its render loop.
