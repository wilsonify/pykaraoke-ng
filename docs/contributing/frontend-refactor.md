# Web frontend refactor

This page documents the 2026 web-frontend refactor: why it happened, the
new file layout, the webpack build, the development and production serving
story, where the PyScript bridge lives, and how the tests work.

It does **not** change any user-visible behavior. The DOM IDs, keyboard
shortcuts, settings keys, playback behavior, and the UI spec invariants are
preserved from the original single-file application; the refactor only changes
how the source is organized and built.

## Why

The original application was one self-contained file — `src/web/index.html` —
that held the markup, CSS, vanilla JS module, and the PyScript bridge all in
one place. That worked for a small app, but as the feature set grew the file
became hard to review, the test loader relied on a regex that extracted the
inline module, and the build story was implicit.

The refactor:

- separates the CSS, pure helpers, store/bridge, and DOM/playback wiring into
  cohesive modules under `src/web/src/`;
- replaces the regex test loader with direct imports;
- adds a small webpack build that produces a self-contained production page in
  `src/web/dist/`;
- keeps the Tauri dev workflow serving the source tree directly so the editor
  loop is still instant.

## Source layout

```text
src/web/
├── dist/                     production build (git-ignored)
│   ├── index.html            the application page
│   ├── style.css             extracted CSS
│   └── app.js                webpack bundle
├── src/
│   ├── index.html            source of truth for the page structure
│   ├── webpack.config.cjs    webpack configuration
│   ├── styles.css            CSS (extracted from the old inline <style>)
│   ├── main.js               entry module: startup + top-level DOM wiring
│   ├── helpers.js            pure helpers (exported for tests)
│   ├── store.js              state + persistence helpers
│   ├── bridge.js             engine-bridge wrapper
│   ├── boot.js               boot sequence (restore state, wire UI, start)
│   ├── ui/
│   │   ├── wire-ui.js        top-level DOM wiring
│   │   ├── commands.js        keyboard shortcut handlers
│   │   ├── render.js          rendering helpers (library count, scan summary,
│   │   │                    results, queue, status, playing, zoom)
│   │   └── playback.js        file access, scanning, playback, transport,
│   │                           CDG stage, lyrics, and the MidiSynth class
│   └── pyscript-bridge.raw   verbatim copy of the inline PyScript bridge
├── _wheel/                   engine wheel        (generated, git-ignored)
└── _assets/
    ├── pyodide/              vendored runtime    (generated, git-ignored)
    └── pyscript/             vendored runtime    (generated, git-ignored)
```

The page structure lives in `src/web/src/index.html`. The inline CSS lives in
`src/web/src/styles.css`. The JS modules are the sources for the part of the
page that used to be the `<script type="module">` block.

## The PyScript bridge

The inline Python bridge is the only Python in the page. It builds one
`pykaraoke.webapp.KaraokeApp` and publishes a single JSON-friendly dispatcher:

```python
app = KaraokeApp()

def api(name, *args):
    return getattr(app, name)(*[_to_py(a) for a in args])

window.pykaraoke_api = api
```

That text lives in two places:

- `src/web/src/index.html` — the source of truth (the page you edit).
- `src/web/src/pyscript-bridge.raw` — the same text extracted into its own
  file so the webpack configuration can embed it verbatim into the built
  `index.html`.

If you change the bridge, change it in `src/web/src/index.html` first and
then copy the updated text into `pyscript-bridge.raw` so the production page
stays in sync.

The bridge text in `pyscript-bridge.raw` is:

```python
"""PyScript bridge: expose the karaoke engine to the inline app script.

Loaded by PyScript from this ``<script type="py">`` block.  Builds a
:class:`pykaraoke.webapp.KaraokeApp` and publishes a single JSON-friendly
dispatcher to ``window.pykaraoke_api``.

Boundary rules:

* JS ``Uint8Array`` arguments arrive as Python ``bytes``/``memoryview``
  (Pyodide auto-conversion), which the engine accepts directly.
* JS objects/arrays are converted deeply with ``to_py()`` so the engine
  sees plain dicts/lists.
* Return values are Python objects; the app script converts PyProxies
  with ``toJs()``.  ``None`` becomes JS ``undefined`` automatically.
"""

from js import window

from pykaraoke.webapp import KaraokeApp

app = KaraokeApp()


def _to_py(value):
    """Deep-convert a JS value into a plain Python value."""
    if hasattr(value, "to_py"):
        return value.to_py()
    return value


def api(name, *args):
    """Call ``app.<name>(*args)`` with converted arguments."""
    return getattr(app, name)(*[_to_py(a) for a in args])


window.pykaraoke_api = api
```

## The build

### Production build

```bash
cd src/web
npx webpack --config webpack.config.cjs --mode production
```

This produces `src/web/dist/index.html`, `style.css`, and `app.js`. The
page is self-contained at that point (aside from the generated wheel and
vendored runtime under `src/web/_wheel/` and `src/web/_assets/`), and it is
identical in structure to the old monolithic page: an inline PyScript bridge,
an inline app bundle, and the same DOM IDs.

### Development workflow

The Tauri dev command serves the *source* tree, not the webpack output:

```bash
cd src/runtimes/tauri
npm ci
npx tauri dev
```

`beforeDevCommand` starts `python ../../scripts/serve-web.py 18000`, which
serves `src/web/` (including the inline `index.html`, `_assets/`, and `_wheel/`)
on `http://localhost:18000`. Edit `src/web/src/*.js`, `styles.css`, or
`index.html` and reload the window — there is no dev rebuild step.

If you want to see the webpack output locally, build it and then serve the
distribution directory:

```bash
cd src/web
npx webpack --config webpack.config.cjs --mode production
python src/scripts/serve-web.py 18000
```

That serves `src/web/dist/`, which is what Tauri embeds in the production
build. The dev server does **not** serve `dist/` during `tauri dev`.

### Test build

The frontend tests import the extracted modules directly, so they do not need
the webpack output at all.

## Tests

### Frontend

```bash
cd tests/web
npm ci
npm test
```

The vitest suite imports the extracted modules directly from
`src/web/src/`. That includes:

- `helpers.js` — the pure helpers that were already being tested
  (`formatTime`, `debounce`, `escapeHtml`, `songLabel`, `companionBaseName`,
  `companionMember`, `SongQueue`, `PART_IDS`, `partClass`, `partLabel`,
  `buildLyricLines`, `highlightState`, `noteToFrequency`,
  `computeNoteTimeline`, `voiceFor`, `writeTileRgba`, and the constants).
- The settings-panel tests still read `src/web/src/index.html` to verify the
  naming-convention `<select>` matches the engine's `FileNameType` enum.

### Python

```bash
uv run pytest tests/pykaraoke/ -v
```

### Rust

```bash
cd src/runtimes/tauri/src-tauri
cargo test
```

## The webpack configuration

`src/web/webpack.config.cjs` is intentionally small:

- Entry: `src/web/src/main.js`.
- CSS: extracted to `dist/style.css` by `mini-css-extract-plugin`; `css-loader`
  resolves the `styles.css` import from `main.js`.
- HTML: `HtmlWebpackPlugin` uses `src/web/src/index.html.ejs` as the template
  and embeds the PyScript bridge verbatim so the built page is identical in
  structure to the old monolithic page.

The configuration is CommonJS (`webpack.config.cjs`) because the root
`package.json` declares `"type": "module"`, and webpack's config loader expects
CommonJS when it is named `.cjs`.

## Dev vs prod serving

This is the most common source of confusion.

- `tauri dev` serves the *source tree* (`src/web/`). The page it loads is the
  inline `index.html`, the inline bridge, and the same `_assets/`/`_wheel/`
  layout as before. Editing source files is immediate; there is no rebuild step.
- The *production* build produces `src/web/dist/` from the extracted modules
  and the `index.html.ejs` template (which embeds the bridge verbatim). That
  is what `frontendDist` points at for `tauri build`.
- The `serve-web.py` helper can serve either directory; by default it serves
  `src/web/`.

The old docs said "no build step for the app itself." That is still true for
the dev workflow. The production build now uses webpack, but only to
consolidate the extracted modules into a self-contained page — it does not
transpile the app or add a framework.

## Script commands

From the repo root:

```bash
npm run build        # webpack production build into src/web/dist/
npm run build:dev    # webpack development build into src/web/dist/
npm run typecheck    # node --check on src/web/src/main.js
```

From `src/runtimes/tauri/`:

```bash
npm run build        # python ../../scripts/build-web.py && cd ../.. && npm run build
npm run tauri        # tauri CLI
```

The Tauri `beforeBuildCommand` runs both `build-web.py` and the webpack
production build, so a full desktop build produces the wheel, the vendored
runtime, and the webpack output in one shot.

## Behavioral invariants

The refactor preserves:

- all DOM IDs, labels, visible controls, and status messages;
- search, filtering, sorting, library scanning, and queue operations;
- queue and settings persistence, including the existing storage keys and
  backward compatibility;
- playback, MIDI synthesis, lyrics, transport controls, and error recovery;
- keyboard bindings: `/`, `Ctrl/Cmd+K`, `Esc`, arrow keys, `Space`, and
  `Ctrl+→`;
- the slim-sidebar layout at 300, 380, and 450 px;
- offline operation using vendored Pyodide/PyScript assets;
- the existing browser, Pyodide, and Tauri runtime compatibility.

`src/pykaraoke/` is untouched.

The behavioral contract for the JS↔Python bridge — argument and return-value
conversions, error handling, and asynchronous behavior — is preserved from the
original `window.pykaraoke_api(name, ...args)` dispatcher.

## What did not change

- `src/pykaraoke/` is untouched.
- The DOM IDs, labels, keyboard shortcuts, settings keys, and the slim-sidebar
  layout invariants are unchanged.
- The Tauri dev workflow still serves the source tree directly.
- The production page is still a single `index.html` with an inline bridge and
  an inline app bundle; webpack only reorganizes the source and produces that
  page from extracted modules.

## What changed

- `src/web/index.html` is now the source of truth for the page structure, with
  the inline CSS and JS module extracted into `src/web/src/`.
- `src/web/src/` holds the extracted modules.
- `src/web/webpack.config.cjs` builds the production page.
- `src/web/src/pyscript-bridge.raw` holds a verbatim copy of the bridge.
- `tests/web/load-app.mjs` was removed; the tests import the extracted modules
  directly.
- `tests/web/app.test.js` was rewritten to import from `src/web/src/`.
- `package.json` and `package-lock.json` were added for the webpack toolchain.
- `.gitignore` was updated for `dist/`, `node_modules/`, and related caches.
- The contributing docs were updated to describe the new layout and build.
