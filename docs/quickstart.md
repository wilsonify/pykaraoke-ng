# Quick Start

Get running in under a minute after cloning.

[← Home](index.md)

---

## 1. Clone and install

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng
uv sync                       # or: pip install -e .
```

## 2. Run tests

```bash
uv run pytest tests/ -v       # or: ./scripts/run-tests.sh
```

## 3. Play a file

```bash
uv run python -m pykaraoke.players.cdg song.cdg
uv run python -m pykaraoke.players.kar song.kar
uv run python -m pykaraoke.players.mpg song.mpg
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
```

## 5. Tauri desktop app

### Dev mode (uses local Python)

```bash
cd src/runtimes/tauri
npx tauri dev
```

### Production build (standalone .exe, no Python needed on target)

```bash
cd src/runtimes/tauri
python -m pip install pyinstaller
npx tauri build
```

Installer at `src-tauri/target/release/bundle/`.

## Common Issues

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: pykaraoke` | Run `uv sync` or `pip install -e .` |
| Tests fail with import errors | Use `uv run pytest` or set `PYTHONPATH=src` |
| Tauri linker errors (Windows) | Run `vcvars64.bat` first |
| `cargo tauri` not found | Install CLI via npm: `npm install -g @tauri-apps/cli@1` |
