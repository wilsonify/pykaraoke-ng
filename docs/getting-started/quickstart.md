# Quick Start

Get running in under a minute after cloning.

[← Home](../index.md)

---

## 1. Clone and install

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
./src/scripts/setup-dev-env.sh       # .venv + editable install + dev deps
# or: uv sync                     # plain uv
```

## 2. Run the tests

```bash
./src/scripts/run-tests.sh            # pytest + vitest
```

Individually:

```bash
uv run pytest tests/pykaraoke/ -v # Python engine tests
cd tests/web && npm ci && npm test # JS extracted from src/web/index.html
```

## 3. Run in a browser

```bash
bash src/scripts/build-web.py         # build the wheel + vendor Pyodide/PyScript
python -m http.server 18000 --directory src/web
```

Open <http://localhost:18000>.

The page loads Pyodide in a Web Worker, installs the `pykaraoke` wheel,
and runs the app from `src/web/index.html`. Folder picking falls back to
`<input webkitdirectory>` when there is no Tauri window.

## 4. Desktop app (Tauri)

### Dev mode

```bash
cd src/runtimes/tauri
npm ci
npx tauri dev
```

`beforeDevCommand` serves `src/web/` on port 18000; the window loads that
URL. Reload the window after editing `src/web/index.html`.

### Production build

```bash
cd src/runtimes/tauri
npx tauri build --bundles nsis    # Windows
npx tauri build --bundles dmg     # macOS
npx tauri build --bundles deb     # Linux
```

Installers land in `src/runtimes/tauri/src-tauri/target/release/bundle/`.
Python must be on `PATH` so `beforeBuildCommand` can rebuild the wheel.

## 5. Code quality

```bash
uv run ruff check .
uv run ruff format --check .
```

## Common Issues

| Problem | Fix |
|---------|------|
| `ModuleNotFoundError: pykaraoke` | Run `uv sync` or `pip install -e .` |
| Tests fail with import errors | Use `uv run pytest` or set `PYTHONPATH=src` |
| `npm ci` fails in `tests/web` | Node 20+ required |
| Blank page, engine never starts | Run `src/scripts/build-web.py` first — `_wheel/` and `_assets/` are generated |
| Tauri linker errors (Windows) | Install VS Build Tools, then run `vcvars64.bat` |
| `npx tauri` not found | `cd src/runtimes/tauri && npm ci` |
| Port 18000 already in use | `python -m http.server 18001 --directory src/web` and load that port |
