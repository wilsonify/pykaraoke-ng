# Build system

How PyKaraoke-NG is assembled and packaged on Windows, macOS, and Linux — and
the rules that keep those builds working on every CI runner.

[← Development](./index.md) · [Architecture overview](../architecture/overview.md)

---

## What a build produces

There is **no bundler**. The front end is plain HTML, CSS, and native ES
modules living directly under `src/web/`. A single `index.html` links the
stylesheets in `css/`, loads the module `src/app.js`, the PyScript runtime, and
the Pyodide interpreter, and loads the Python bridge from `src/bridge.py`.

```text
src/pykaraoke/                      pure-stdlib Python engine
        │
        │  python src/scripts/build-web.py
        ▼
src/web/                            authoritative frontend root (committed)
├── index.html                      the application page (source of truth)
├── css/                            stylesheets, one topical file per area
│   ├── base.css                    tokens, reset, focus rings
│   ├── layout.css                  app shell: header, column, status, notices
│   ├── buttons.css                 .btn family, transport buttons, chips
│   ├── sections.css                panels, headings, counts, empty states
│   ├── filters.css                 search box and format filters
│   ├── song-list.css               song rows, badges, queue rows
│   ├── player.css                  stage, CD+G canvas, lyrics, progress
│   ├── library.css                 library management and scan diagnostics
│   └── settings.css                settings panel and groups
├── src/
│   ├── app.js                      UI wiring (browser-only, no framework)
│   ├── helpers.js                  pure helpers (exported for tests)
│   └── bridge.py                   PyScript bridge → window.pykaraoke_api
├── _wheel/                         engine wheel        (generated, git-ignored)
└── _assets/
    ├── pyodide/                    vendored runtime    (generated, git-ignored)
    └── pyscript/                   vendored runtime    (generated, git-ignored)
```

`src/web/` is both what the dev server serves and what Tauri embeds in the
production build, so dev and prod run the *same* page — there is no separate
dist tree to fall out of sync.

## Building

### Generate the web assets

```bash
python src/scripts/build-web.py
```

This builds `src/web/_wheel/pykaraoke_ng-*.whl`, vendors Pyodide and PyScript
into `src/web/_assets/` (verifying pinned SHA-256 checksums, reusing files that
already match so a warm build needs no network), and then cross-checks that
every asset `index.html` references actually exists — a missing asset fails the
build instead of shipping a page that 404s at runtime.

Run it before serving the page by hand:

```bash
python src/scripts/serve-web.py 18000
```

### Build the desktop app

```bash
cd src/runtimes/tauri
npm ci
npx tauri build --bundles nsis   # Windows
npx tauri build --bundles dmg    # macOS
npx tauri build --bundles deb    # Linux
```

`beforeBuildCommand` runs `build-web.py`, so you do not have to regenerate the
assets first. Output lands in
`src/runtimes/tauri/src-tauri/target/release/bundle/`.

## Tauri hooks and their working directory

Both hooks run from the **Tauri project root** (`src/runtimes/tauri/`) — *not*
from `src-tauri/`. That single fact has caused every path bug in this build.

| Hook | Value | Effect |
|------|-------|--------|
| `beforeBuildCommand` | `python ../../scripts/build-web.py` | Rebuild the wheel and vendor the runtime |
| `beforeDevCommand` | `python ../../scripts/serve-web.py 18000` | Serve `src/web/` for `devUrl` |
| `devUrl` | `http://localhost:18000` | Where the Tauri dev window loads from |
| `frontendDist` | `../../../web` | What Tauri embeds; relative to `src-tauri/` |

```text
src/runtimes/tauri/          ← CWD for both hooks
├── package.json             ← wraps the Tauri CLI (no build toolchain)
└── src-tauri/               ← the Rust project
    ├── tauri.conf.json      ← frontendDist: ../../../web
    ├── Cargo.toml
    └── build.rs
```

From `src/runtimes/tauri/`, the scripts are two levels up (`../../scripts/...`);
from `src-tauri/`, the checkout root and the web directory are three levels up
(`../../../web`). When a hook or package script moves, recompute **every**
relative path from the new working directory before pushing.

## Development workflow

```bash
cd src/runtimes/tauri
npm ci
npx tauri dev
```

`beforeDevCommand` starts `python ../../scripts/serve-web.py 18000`, which
serves `src/web/` (including `index.html`, `css/`, `src/app.js`, `_assets/`, and
`_wheel/`) on `http://localhost:18000`. Edit `src/web/src/app.js`,
`helpers.js`, `bridge.py`, a file in `css/`, or `index.html` and reload the
window — there is no dev rebuild step.

You can open the same URL in a plain browser; the frontend detects the absence
of `window.__TAURI__.core` and falls back to a browser folder picker.

### The PyScript bridge

The bridge is the only Python in the page. It builds one
`pykaraoke.webapp.KaraokeApp` and publishes a single JSON-friendly dispatcher:

```python
app = KaraokeApp()

def api(name, *args):
    return getattr(app, name)(*[_to_py(a) for a in args])

window.pykaraoke_api = api
```

It lives in `src/web/src/bridge.py`, loaded by the `<script type="py">` tag in
`index.html`. `app.js` polls for `window.pykaraoke_api` before calling the
engine, so the extra fetch is not a race. Edit it and reload; there is no
second copy to keep in sync.

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

The vitest suite imports the modules directly from `src/web/src/`
(`helpers.js` for pure logic, `app.js` for the wired DOM). Keeping those green
is part of every change.

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

- Keep `src/web/` as the authoritative frontend root: page structure in
  `index.html`, styles in `css/*.css`, the bridge in `src/bridge.py`, browser
  wiring in `src/app.js`, pure helpers in `src/helpers.js`. Do not
  reintroduce a bundler or a `dist/` tree.
- Keep `src/pykaraoke/` untouched by the frontend; engine work belongs there
  and must stay **stdlib-only** so it runs under Pyodide.
- Changes that touch extracted logic must keep `tests/web` green.
- Do not add frontend dependencies unless there is a concrete, documented need.
