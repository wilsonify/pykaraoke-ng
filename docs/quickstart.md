# Quick Start

[← Back to Home](index.md)

---

Get running in under a minute after cloning.

## 1. Clone and install

```bash
git clone https://github.com/wilsonify/pykaraoke-ng.git
cd pykaraoke-ng

# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## 2. Run tests

```bash
./scripts/run-tests.sh

# Or directly
uv run pytest tests/ -v
```

## 3. Run the backend

```bash
# stdio mode (for Tauri / desktop IPC)
uv run python -m pykaraoke.core.backend

# HTTP mode (for Docker / headless)
uv run python -m pykaraoke.core.backend --http
```

## 4. Run a player

```bash
uv run python -m pykaraoke.players.cdg song.cdg
uv run python -m pykaraoke.players.kar song.kar
uv run python -m pykaraoke.players.mpg song.mpg
```

## 5. Build the Tauri app

```bash
cd src/runtimes/tauri/src-tauri
cargo tauri dev     # development
cargo tauri build   # production
```

## Common Issues

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'pykaraoke'` | Run `uv sync` or `pip install -e .` |
| Tests fail with import errors | Use `uv run pytest` or set `PYTHONPATH=src` |
| Can't find assets | Assets are in `assets/fonts/` and `assets/icons/` |

## Next

- **[Developer Guide](developers.md)** — full development workflow
- **[Repository Structure](architecture/structure.md)** — where everything lives
