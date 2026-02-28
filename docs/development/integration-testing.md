# Integration Testing

Run integration tests against a live backend using Docker Compose.

[← Home](../index.md) · [Developer Guide](../developers.md)

---

## Quick Reference

```bash
./scripts/run-tests.sh                    # unit + integration (auto-detects Docker)
./scripts/run-tests.sh --unit-only        # unit only, no Docker
./scripts/run-tests.sh --integration-only # integration only, requires Docker
```

## How It Works

Docker Compose starts a backend HTTP server, waits for its `/health`
endpoint, then runs pytest against it.

```
docker compose start backend-test   → PyKaraoke HTTP server on :8080
         ↓ healthcheck passes
docker compose run test-integration → pytest -m integration
```

## Docker Compose Services

| Service | Profile | Purpose |
|---------|---------|---------|
| `backend-test` | `integration` | HTTP API server with healthcheck |
| `test-integration` | `integration` | Runs `@pytest.mark.integration` tests only |
| `test` | `test` | Unit tests (excludes integration) |
| `test-all` | `test` | Unit + integration together |
| `test-all-coverage` | `test` | All tests with coverage report |

## Running Directly with Docker Compose

```bash
cd deploy/docker

# Integration tests only
docker compose --profile integration run test-integration

# All tests
docker compose --profile test run test-all

# Coverage
docker compose --profile test run test-all-coverage
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYKARAOKE_API_URL` | `http://localhost:8080` | Backend URL (set automatically in Docker) |
| `SONGS_DIR` | — | Optional test songs directory |

## Writing Integration Tests

Mark tests with `@pytest.mark.integration`:

```python
import pytest

@pytest.mark.integration
def test_health_endpoint():
    import urllib.request, os
    api_url = os.environ.get("PYKARAOKE_API_URL", "http://localhost:8080")
    try:
        response = urllib.request.urlopen(f"{api_url}/health", timeout=5)
        assert response.status == 200
    except urllib.error.URLError:
        pytest.skip("Backend not running")
```

Always include a `pytest.skip` fallback so tests pass locally without Docker.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Backend won't start | `docker compose logs backend-test` |
| Tests timing out | Increase healthcheck timeout in `docker-compose.yml` |
| Port in use | Docker assigns ports dynamically; check `docker compose ps` |

## Performance Notes

- First run downloads and builds images (~2-5 minutes depending on connection)
- Subsequent runs use cached layers (~10-30 seconds for test startup)
- Backend healthcheck adds ~2-5 seconds per run
- Add `--quiet` flag to reduce output verbosity

## See Also

- [Development Setup](./quality-improvements.md)
- [Docker Setup](./sonarqube-setup.md)
- Main [README](../README.md)
