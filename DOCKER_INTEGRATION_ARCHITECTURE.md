# Docker Compose Integration Testing Architecture

## Service Orchestration Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ docker compose --profile integration run test-integration       │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Docker Compose Network Setup        │
        │   (bridge network: pykaraoke-net)     │
        └───────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ backend-test │ │test-integration│ │  volumes   │
    ├──────────────┤ ├──────────────┤ ├──────────────┤
    │ Image: pykaraoke-ng:backend   │ │src/         │
    │ Port: 8080   │ │ Image: pykaraoke-ng:test  │tests/       │
    │ Status: healthy ← healthcheck ├─│ pyproject.toml│
    │ (waits for /health endpoint) │ │ depends_on: backend-test │
    │                │ │ HEALTHY       │
    │ CMD: FastAPI  │ │ CMD: pytest   │
    │ server       │ │ tests/        │
    │ listens on   │ │ -v --tb=short │
    │ :8080       │ │ -m integration│
    └──────────────┘ └──────────────┘ └──────────────┘
         │                   │
         │                   │
         │  HTTP Requests    │
         │  (port 8080)      │
         │◄──────────────────┘
         │
    /health ──check server readiness──►
    /api/state ──query backend state──►
    /api/command ──send commands──►
    /api/events ──stream events──►
```

## Test Execution Flow

```
Start Integration Tests
        │
        ▼
   ┌─────────────────────────────────┐
   │ Create Network: pykaraoke-net   │
   └─────────────────────────────────┘
        │
        ▼
   ┌─────────────────────────────────┐
   │ Start backend-test Service      │
   │ - Build image (if needed)       │
   │ - Start container               │
   │ - Run healthcheck loop          │
   └─────────────────────────────────┘
        │
        ▼ (waits for healthy status)
   ┌─────────────────────────────────┐
   │ Start test-integration Service  │
   │ - Build test image (if needed)  │
   │ - Set PYKARAOKE_API_URL         │
   │ - Run pytest                    │
   └─────────────────────────────────┘
        │
        ├─ Test: test_health_endpoint()
        │   └─ HTTP GET /health ✓
        │
        ├─ Test: test_state_endpoint()
        │   └─ HTTP GET /api/state ✓
        │
        ├─ Test: test_command_endpoint()
        │   └─ HTTP POST /api/command ✓
        │
        ├─ Test: test_events_endpoint()
        │   └─ HTTP GET /api/events ✓
        │
        ▼
   ┌─────────────────────────────────┐
   │ Test Results                    │
   │ ✓ All integration tests passed  │
   └─────────────────────────────────┘
        │
        ▼
   ┌─────────────────────────────────┐
   │ Cleanup                         │
   │ - Stop containers               │
   │ - Remove network                │
   │ - Free resources                │
   └─────────────────────────────────┘
```

## Service Communication

```
┌─────────────────────────────────────────────────┐
│              Docker Network: pykaraoke-net      │
│                                                 │
│  ┌──────────────┐                ┌──────────────┐
│  │ backend-test │                │test-integration
│  │              │                │              │
│  │ IP: 172.X.X.2               │ IP: 172.X.X.3 │
│  │ Port: 8080   │                │              │
│  │              │                │ PYKARAOKE_   │
│  │ FastAPI      │                │ API_URL:     │
│  │ - /health    │◄───HTTP────────┤ http://     │
│  │ - /api/state │                │ backend-    │
│  │ - /api/cmd   │                │ test:8080   │
│  │ - /api/events│                │              │
│  │              │                │ pytest       │
│  │ ✓ healthy    │                │ runner       │
│  └──────────────┘                └──────────────┘
│                                                 │
└─────────────────────────────────────────────────┘
```

## Running Different Test Profiles

### Unit Tests Only (No Docker)
```bash
./scripts/run-tests.sh
# or
./test-docker.sh unit
```
✓ 174 passed, 9 skipped
⏱️ ~5 seconds

### Integration Tests with Docker
```bash
./test-docker.sh integration
# or
cd deploy/docker && docker compose --profile integration run test-integration
```
✓ Runs ~20 integration tests
✓ Backend server auto-starts
⏱️ ~15-30 seconds (after images are built)

### All Tests with Docker
```bash
./test-docker.sh all
# or
cd deploy/docker && docker compose --profile test run test-all
```
✓ 174 unit + ~20 integration tests
⏱️ ~20-40 seconds

### With Coverage Report
```bash
./test-docker.sh coverage
# or
cd deploy/docker && docker compose --profile test run test-all-coverage
```
✓ Generates `htmlcov/index.html`
⏱️ ~25-45 seconds

## Key Features

### ✅ Automatic Service Management
- Backend starts automatically when integration tests requested
- Healthcheck ensures backend is ready before tests run
- Automatic cleanup when done

### ✅ Network Isolation
- Containers communicate via internal Docker network
- Port 8080 exposed from container (host port assigned dynamically)
- No conflicts with existing services

### ✅ Volume Mounting
- Source code mounted read-only for testing
- Coverage reports written to host filesystem
- Songs directory optionally mounted for test data

### ✅ Graceful Degradation
- All integration tests skip gracefully if server unavailable
- Can run without Docker (tests skip instead of failing)
- Backward compatible with existing test infrastructure

### ✅ CI/CD Ready
- Deterministic test runs
- Exit code indicates success/failure
- Works in headless environments
- Repeatable builds with Docker layer caching

## Performance Notes

| Scenario | Duration | Notes |
|----------|----------|-------|
| First run (unit) | ~5s | Local, no Docker |
| First run (integration) | 2-5 min | Builds images |
| Subsequent runs (integration) | 15-30s | Uses cached images |
| With coverage report | +5-15s | HTML generation |
| Parallel services | ~equal | backend waits for healthy |

## Troubleshooting Commands

```bash
# View service logs
docker compose logs backend-test
docker compose logs test-integration

# Check healthcheck status
docker compose ps backend-test

# Manually test health endpoint
curl http://localhost:8080/health

# Run tests in verbose mode
docker compose --profile integration run test-integration pytest -vv

# Keep containers running for debugging
docker compose --profile integration run --no-deps -it backend-test bash
```

## Integration with CI/CD

```yaml
# Example GitHub Actions workflow
- name: Run Integration Tests
  working-directory: deploy/docker
  run: docker compose --profile test run test-all

# Or use convenience script
- name: Run All Tests
  run: ./test-docker.sh all
```

## File Structure

```
pykaraoke-ng/
├── deploy/docker/
│   ├── docker-compose.yml      (updated with integration services)
│   └── Dockerfile              (updated test stage)
├── tests/
│   ├── pykaraoke/core/
│   │   ├── test_backend_api.py       (updated with integration tests)
│   │   └── test_backend_http.py      (updated with real HTTP tests)
│   └── integration/
│       └── test_end_to_end.py        (marked as integration)
├── docs/development/
│   └── integration-testing.md        (new guide)
├── test-docker.sh                    (new convenience script)
└── INTEGRATION_TESTS_SETUP.md         (this summary)
```

## See Also

- [Full Integration Testing Guide](docs/development/integration-testing.md)
- [Docker Setup Documentation](docs/development/sonarqube-setup.md)
- [Development Guide](docs/development/quality-improvements.md)
