# PyKaraoke Backend - Dual Mode Support

The PyKaraoke backend now supports two execution modes:

## 1. stdio Mode (Default)

Reads JSON commands from stdin and writes responses to stdout. Suitable for desktop applications and IPC.

### Usage

```bash
# Explicit stdio mode
python -m pykaraoke.core.backend --stdio

# Or default (no flag)
python -m pykaraoke.core.backend
```

### Communication Protocol

**Command Format (stdin):**
```json
{"action": "play", "params": {"playlist_index": 0}}
```

**Response Format (stdout):**
```json
{"type": "response", "response": {"status": "ok"}}
```

**Event Format (stdout):**
```json
{"type": "event", "event": {"type": "state_changed", "timestamp": 1234567890.0, "data": {...}}}
```

## 2. HTTP API Mode

Runs a FastAPI-based HTTP server. Suitable for Docker, Kubernetes, and headless execution.

### Installation

Install HTTP mode dependencies:

```bash
# Using pip
pip install pykaraoke-ng[http]

# Using uv
uv pip install pykaraoke-ng[http]
```

### Usage

```bash
# Start HTTP server on default port (8080)
python -m pykaraoke.core.backend --http

# Custom host and port
python -m pykaraoke.core.backend --http --host 127.0.0.1 --port 9000

# Using environment variables
BACKEND_MODE=http PYKARAOKE_API_HOST=0.0.0.0 PYKARAOKE_API_PORT=8080 python -m pykaraoke.core.backend
```

### API Endpoints

#### Health Check
```bash
GET /health
```
Returns: `{"status": "healthy", "timestamp": 1234567890.0}`

#### Get State
```bash
GET /api/state
```
Returns current backend state including playback status, playlist, and volume.

#### Execute Command
```bash
POST /api/command
Content-Type: application/json

{"action": "set_volume", "params": {"volume": 0.75}}
```

#### Playback Control
- `POST /api/play` - Start playback
- `POST /api/pause` - Pause playback
- `POST /api/stop` - Stop playback
- `POST /api/next` - Next track
- `POST /api/previous` - Previous track
- `POST /api/volume?volume=0.75` - Set volume (0.0-1.0)

#### Playlist Management
- `POST /api/playlist/add?filepath=/path/to/song.cdg` - Add to playlist
- `DELETE /api/playlist/{index}` - Remove from playlist
- `DELETE /api/playlist` - Clear playlist

#### Library Management
- `GET /api/library/search?query=artist` - Search library
- `GET /api/library` - Get all songs
- `POST /api/library/scan` - Scan library folders
- `POST /api/library/folder?folder=/path/to/songs` - Add folder

#### Events
- `GET /api/events?since=1234567890.0` - Poll for events since timestamp
- `DELETE /api/events` - Clear event queue

### Docker Example

```bash
# Run in HTTP mode
docker run -p 8080:8080 -e BACKEND_MODE=http pykaraoke-ng:backend

# Test health check
curl http://localhost:8080/health

# Get current state
curl http://localhost:8080/api/state

# Control playback
curl -X POST http://localhost:8080/api/play
```

### Docker Compose

```yaml
services:
  backend:
    image: pykaraoke-ng:backend
    environment:
      - BACKEND_MODE=http
      - PYKARAOKE_API_HOST=0.0.0.0
      - PYKARAOKE_API_PORT=8080
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Mode Selection

The backend mode can be selected via:

### Command-line Arguments

```bash
# stdio mode
python -m pykaraoke.core.backend --stdio

# HTTP mode
python -m pykaraoke.core.backend --http
```

### Environment Variable

```bash
# stdio mode
BACKEND_MODE=stdio python -m pykaraoke.core.backend

# HTTP mode
BACKEND_MODE=http python -m pykaraoke.core.backend
```

**Priority:** Command-line arguments override environment variables.

## Architecture

```
PyKaraokeBackend (Core Business Logic)
     ├── handle_command()      # Transport-agnostic command handler
     ├── get_state()            # State retrieval
     └── event_callback        # Event emission

create_stdio_server()          # stdin/stdout transport
     └── Reads from stdin, writes to stdout

create_http_server()           # HTTP/REST transport
     └── FastAPI + Uvicorn server
```

## Benefits

- **No Code Duplication:** Core logic is shared between both modes
- **Clean Separation:** Transport concerns are isolated from business logic
- **Explicit Configuration:** Mode is clearly specified, not inferred
- **Container-Friendly:** HTTP mode doesn't exit when stdin is closed
- **Flexible Deployment:** Same binary works for desktop and containerized environments

## Graceful Shutdown

Both modes handle SIGTERM and SIGINT signals gracefully:
- Closes active players
- Cleans up resources
- Exits cleanly

## Logging

- stdio mode: Logs to stderr (stdout reserved for protocol)
- HTTP mode: Logs to stdout with uvicorn's access logs

## Testing

Run tests for both modes:

```bash
# All backend tests
pytest tests/pykaraoke/core/test_backend_api.py tests/pykaraoke/core/test_backend_http.py -v

# HTTP mode tests only
pytest tests/pykaraoke/core/test_backend_http.py -v
```
