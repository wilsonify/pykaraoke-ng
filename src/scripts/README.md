# Development Scripts

Small helpers for setup, testing, and serving the single-file web app.

## `setup-dev-env.sh`

Creates `.venv/`, installs `pykaraoke-ng[dev]` in editable mode, builds the
web assets (`scripts/build-web.py`), and installs the frontend test runner.

```bash
./scripts/setup-dev-env.sh

# Options:
PYTHON=python3.12 ./scripts/setup-dev-env.sh   # interpreter to use
VENV_DIR=/tmp/venv ./scripts/setup-dev-env.sh  # venv location (default: .venv)
```

## `run-tests.sh`

Runs the whole suite: pytest (Python engine) then vitest (JS extracted
from `web/index.html`).

```bash
./scripts/run-tests.sh              # both suites
./scripts/run-tests.sh --engine     # pytest only
./scripts/run-tests.sh --web        # vitest only
./scripts/run-tests.sh --verbose    # verbose pytest output
```

Coverage runs use pytest directly:

```bash
uv run pytest tests/pykaraoke --cov --cov-report=html
```

## `build-web.py`

Builds everything `web/index.html` needs at runtime:

1. builds `web/_wheel/pykaraoke_ng-*.whl` from `src/pykaraoke`
2. vendors Pyodide + PyScript into `web/_assets/`

Run it before serving the page, and before `npx tauri build`
(`beforeBuildCommand` runs it for you).

```bash
python scripts/build-web.py
```

## `serve-web.py`

Serves `web/` on a port with the right MIME types for `.wasm`, `.mjs`,
`.zip`, and `.whl`.

```bash
python scripts/serve-web.py 18000
```

`tauri.conf.json` uses this as `beforeDevCommand`.

## Troubleshooting

| Problem | Fix |
|---------|------|
| `ModuleNotFoundError: pykaraoke` | Run `./scripts/setup-dev-env.sh`, or `uv sync` |
| `npm: command not found` in `run-tests.sh` | Install Node 20+, or run the two suites manually (`uv run pytest`, `cd tests/web && npm test`) |
| Page loads but engine never starts | Run `scripts/build-web.py` — `_wheel/` and `_assets/` are generated |
| Port already in use | Pass another port, e.g. `python scripts/serve-web.py 18001` |

More detail: [Developer Guide](../docs/developers.md).
