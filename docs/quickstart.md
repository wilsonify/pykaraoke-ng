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
./scripts/run-tests.sh        # or: uv run pytest tests/ -v
```

## 3. Run the backend

```bash
uv run python -m pykaraoke.core.backend          # stdio (desktop IPC)
uv run python -m pykaraoke.core.backend --http    # HTTP (headless)
```

## 4. Play a file

```bash
uv run python -m pykaraoke.players.cdg song.cdg
uv run python -m pykaraoke.players.kar song.kar
uv run python -m pykaraoke.players.mpg song.mpg
```

## 5. Build the Tauri app

```bash
cd src/runtimes/tauri/src-tauri
cargo tauri dev      # development
cargo tauri build    # production
```

## Common issues

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: pykaraoke` | Run `uv sync` or `pip install -e .` |
| Tests fail with import errors | Use `uv run pytest` or set `PYTHONPATH=src` |

## Next

- [Developer Guide](developers.md) — full development workflow
- [Repository Structure](architecture/structure.md) — project layout
