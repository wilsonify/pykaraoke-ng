# Build system

How PyKaraoke-NG is assembled and packaged on Windows, macOS, and Linux — and
the rules that keep those builds working on every CI runner.

[← Development](./index.md) · [Architecture overview](../architecture/overview.md)

---

## What a build produces

The front end is now a small webpack project under `src/web/`, but the
*shape* of the application on disk is almost the same as before: a single
`index.html` that references a stylesheet, a JS bundle, the PyScript runtime,
and the Pyodide interpreter, plus an inline Python bridge.

```text
src/pykaraoke/                      pure-stdlib Python engine
        │
        │  python src/scripts/build-web.py
        ▼
src/web/
├── dist/                           production build (generated, git-ignored)
│   ├── index.html                  the application page
│   ├── style.css                   extracted CSS
│   └── app.js                      extracted JS bundle
├── src/
│   ├── index.html                  source of truth for the page structure
│   ├── webpack.config.cjs          webpack configuration (CommonJS, runs in node_modules)
│   ├── styles.css                   CSS, extracted to dist/style.css by webpack
│   ├── main.js                     entry module: startup + top-level DOM wiring
│   ├── helpers.js                  pure helpers (exported for tests)
│   ├── store.js                    state + persistence helpers
│   ├── bridge.js                   engine-bridge wrapper
│   ├── bootstrap.js                boot sequence (restore state, wire UI, start)
│   ├── ui/
│   │   ├── wire-ui.js              top-level DOM wiring
│   │   ├── commands.js             keyboard shortcut handlers
│   │   ├── render.js               rendering helpers (library count, scan summary,
│   │   │                           results, queue, status, playing, zoom)
│   │   └── playback.js             file access, scanning, playback, transport,
│   │   │                           CDG stage, lyrics, and the MidiSynth class
│   │   └── commands.js             keyboard shortcut handlers
│   └── lib/
│       ├── format-time.js
│       ├── debounce.js
│       ├── sorting.js
│       ├── filtering.js
│       └── snapshots.js
├── _wheel/                         engine wheel        (generated, git-ignored)
└── _assets/
    ├── pyodide/                    vendored runtime    (generated, git-ignored)
    └── pyscript/                   vendored runtime    (generated, git-ignored)
```

The PyScript bridge (`<script type="py">` in the page) is prose extracted
from `src/web/index.html` into `src/web/src/pyscript-bridge.raw`; the webpack
configuration embeds it verbatim into the built `index.html` so the production
page is identical to the old monolithic page.

## Building

### Generate the web assets

```bash
python src/scripts/build-web.py
```

This builds `src/web/_wheel/pykaraoke_ng-*.whl` and vendors Pyodide and
PyScript into `src/web/_assets/`. Run it before serving the page by hand:

```bash
python -m http.server 18000 --directory src/web
```

### Build the frontend (webpack)

```bash
cd src/web
npx webpack --config webpack.config.cjs --mode production
```

This produces `src/web/dist/index.html`, `style.css`, and `app.js`. No
frontend dependency tree is committed other than `package-lock.json`.

### Build the desktop app

```bash
cd src/runtimes/tauri
npm ci
npx tauri build --bundles nsis   # Windows
npx tauri build --bundles dmg    # macOS
npx tauri build --bundles deb    # Linux
```

`beforeBuildCommand` runs `build-web.py` *and* the webpack production build,
so you do not have to regenerate the assets or the JS bundle first. Output
lands in `src/runtimes/tauri/src-tauri/target/release/bundle/`.

## Tauri hooks and their working directory

Both hooks run from the **Tauri project root** (`src/runtimes/tauri/`) — *not*
from `src-tauri/`. That single fact has caused every path bug in this build.

| Hook | Value | Effect |
|------|-------|--------|
| `beforeBuildCommand` | `python ../../scripts/build-web.py && cd ../.. && npm run build` | Rebuild the wheel, vendor the runtime, then run the webpack production build |
| `beforeDevCommand` | `python ../../scripts/serve-web.py 18000` | Serve `src/web/` for `devUrl` |
| `devUrl` | `http://localhost:18000` | Where the Tauri dev window loads from |
| `frontendDist` | `../../../web/dist` | What Tauri embeds; expressed relative to `src-tauri/` |

```text
src/runtimes/tauri/          ← CWD for both hooks
├── package.json             ← "build": python ../../scripts/build-web.py && cd ../.. && npm run build
└── src-tauri/               ← the Rust project
    ├── tauri.conf.json      ← frontendDist: ../../../web/dist
    ├── Cargo.toml
    └── build.rs
```

From `src/runtimes/tauri/`, the scripts are two levels up (`../../scripts/...`);
from `src-tauri/`, the checkout root and the web *distribution* directory are
three levels up (`../../../web/dist`). When a hook or package script moves,
recompute **every** relative path from the new working directory before pushing.

## Development workflow

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

### The PyScript bridge

The inline Python bridge is the only Python in the page. It builds one
`pykaraoke.webapp.KaraokeApp` and publishes a single JSON-friendly dispatcher:

```python
app = KaraokeApp()

def api(name, *args):
    return getattr(app, name)(*[_to_py(a) for a in args])

window.pykaraoke_api = api
```

That text lives in two places:

- `src/web/index.html` — the source of truth (the page you edit).
- `src/web/src/pyscript-bridge.raw` — the same text extracted into its own
  file so the webpack configuration can embed it verbatim into the built
  `index.html`.

If you change the bridge, change it in `src/web/index.html` first, then copy
the updated text into `pyscript-bridge.raw` and rebuild so the production page
stays in sync.

## Testing

### Python

```bash
uv run pytest tests/pykaraoke/ -v              # unit tests
uv run pytest tests/pykaraoke/ --cov --cov-report=html
uv run pytest tests/pykaraoke/test_cdg.py -v   # single file
```

### Frontend

```bash
cd tests/web
npm ci
npm test
```

The vitest suite no longer extracts the script out of `src/web/index.html`;
the tests import the extracted modules directly from `src/web/src/`. Keeping
those modules green is part of every change.

### Rust

```bash
cd src/runtimes/tauri/src-tauri
cargo test
```

### Everything

```bash
cd src/runtimes/tauri
./../../scripts/run-tests.sh          # pytest + vitest
```

## Code Quality

```bash
uv run ruff check .             # lint
uv run ruff check . --fix       # auto-fix
uv run ruff format .            # format
```

## Editing rules

- Keep `src/web/src/` as the place where JS/CSS/HTML responsibilities are
  separated: page structure in `index.html`, CSS in `styles.css`, JS modules
  in `src/web/src/`.
- Keep `src/pykaraoke/` untouched by the frontend refactor; engine work
  belongs there and must stay **stdlib-only** so it runs under Pyodide.
- Changes that touch extracted logic must keep `tests/web` green.
- Do not add frontend dependencies unless there is a concrete, documented need.
