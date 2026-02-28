# Backend Modes

[← Home](index.md) · [Architecture](architecture/overview.md)

---

The backend supports two transport modes over identical core logic.

## stdio (default)

Reads JSON commands from stdin, writes responses to stdout.
Used by the Tauri desktop shell.

```bash
python -m pykaraoke.core.backend           # default
python -m pykaraoke.core.backend --stdio   # explicit
```

### Protocol

Commands (stdin):
```json
{"action": "play", "params": {"playlist_index": 0}}
```

Responses (stdout):
```json
{"type": "response", "response": {"status": "ok"}}
```

Events (stdout):
```json
{"type": "event", "event": {"type": "state_changed", "timestamp": 1234567890.0, "data": {...}}}
```

## HTTP

FastAPI server for Docker, Kubernetes, and headless deployments.

```bash
pip install pykaraoke-ng[http]                          # install deps
python -m pykaraoke.core.backend --http                 # default port 8080
python -m pykaraoke.core.backend --http --port 9000     # custom port
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | `{"status": "healthy", "timestamp": ...}` |
| `GET` | `/api/state` | Current playback state |
| `POST` | `/api/command` | Send a JSON command |
| `POST` | `/api/play` | Start playback |
| `POST` | `/api/pause` | Pause |
| `POST` | `/api/stop` | Stop |
| `POST` | `/api/next` | Next track |
| `POST` | `/api/previous` | Previous track |
| `POST` | `/api/volume?volume=0.75` | Set volume (0.0–1.0) |
| `POST` | `/api/playlist/add?filepath=...` | Add to playlist |
| `DELETE` | `/api/playlist/{index}` | Remove from playlist |
| `DELETE` | `/api/playlist` | Clear playlist |
| `GET` | `/api/library/search?query=...` | Search library |
| `GET` | `/api/library` | List all songs |
| `POST` | `/api/library/scan` | Re-scan folders |
| `POST` | `/api/library/folder?folder=...` | Add folder |
| `GET` | `/api/events?since=...` | Poll events since timestamp |
| `DELETE` | `/api/events` | Clear event queue |

### Docker example

```bash
docker run -p 8080:8080 -e BACKEND_MODE=http pykaraoke-ng:backend
curl http://localhost:8080/health
curl http://localhost:8080/api/state
curl -X POST http://localhost:8080/api/play
```

---

## Mode selection

| Method | stdio | HTTP |
|--------|-------|------|
| CLI flag | `--stdio` | `--http` |
| Env var | `BACKEND_MODE=stdio` | `BACKEND_MODE=http` |

CLI flags override environment variables.

## Architecture

```
PyKaraokeBackend (core logic)
├── handle_command()      # transport-agnostic
├── get_state()
└── event_callback

create_stdio_server()     # stdin/stdout transport
create_http_server()      # FastAPI + Uvicorn
```

Core logic is shared. Transport concerns are isolated.

## Shutdown

Both modes handle `SIGTERM` and `SIGINT`: close active players, clean up, exit.

## Logging

- stdio: logs to stderr (stdout reserved for protocol).
- HTTP: logs to stdout via uvicorn.

## Testing

```bash
pytest tests/pykaraoke/core/test_backend_api.py tests/pykaraoke/core/test_backend_http.py -v
```
