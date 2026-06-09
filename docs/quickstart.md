# Quick Start

Get running in under a minute after cloning.

[← Home](index.md)

---

## 1. Clone and install

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
uv sync                       # or: pip install -e ".[dev]"
```

## 2. Run unit tests

```bash
uv run pytest tests/pykaraoke/ -v       # Python unit tests
```

Run the full suite (including validation tests against the built artifact):

```bash
uv run pytest tests/ -v                 # all tests
uv run pytest tests/ --cov --cov-report=html  # with coverage
```

## 3. Play a file

```bash
uv run python -m pykaraoke.players.cdg song.cdg   # CD+G
uv run python -m pykaraoke.players.kar song.kar    # MIDI / KAR
uv run python -m pykaraoke.players.mpg song.mpg    # video
```

## 4. Start the backend (stdio mode)

```bash
uv run python -m pykaraoke.core.backend
```

Send commands via stdin:

```bash
echo '{"action":"get_state","params":{}}' | uv run python -m pykaraoke.core.backend
```

Or start the HTTP API:

```bash
uv run python -m pykaraoke.core.backend --http
curl http://localhost:8080/health
curl http://localhost:8080/api/state
```

## 5. Build the production backend artifact

```bash
cd src/runtimes/tauri
python -m PyInstaller backend.spec --distpath src-tauri --workpath build/pyinstaller-work --clean -y
```

The resulting `src-tauri/backend/backend.exe` (~12 MB) runs standalone
with no Python dependency.

## 6. Validation tests

Test the real built artifact (no mocking):

```bash
export PYKARAOKE_BACKEND_EXE=src/runtimes/tauri/src-tauri/backend/backend.exe
uv run pytest tests/validation/ -v -m artifact
```

## 7. Tauri desktop app

### Dev mode (uses local Python)

```bash
cd src/runtimes/tauri
npx tauri dev
```

### Production build (standalone installer)

```bash
cd src/runtimes/tauri
python -m pip install pyinstaller
npm install -g @tauri-apps/cli@1
npx tauri build --bundles nsis     # Windows
npx tauri build --bundles dmg      # macOS
npx tauri build --bundles deb      # Linux
```

Installer at `src-tauri/target/release/bundle/`.

## Common Issues

| Problem | Fix |
|---------|------|
| `ModuleNotFoundError: pykaraoke` | Run `uv sync` or `pip install -e .` |
| Tests fail with import errors | Use `uv run pytest` or set `PYTHONPATH=src` |
| `backend.exe` not found for validation | Build it first (step 5) or set `PYKARAOKE_BACKEND_EXE` |
| Tauri linker errors (Windows) | Run `vcvars64.bat` first |
| `cargo tauri` not found | Install CLI: `npm install -g @tauri-apps/cli@1` |
