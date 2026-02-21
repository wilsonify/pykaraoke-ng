# Integration Testing with Docker Compose

This guide explains how to run integration tests using Docker Compose to automate the PyKaraoke backend server setup.

## Overview

Previously, integration tests were skipped because they required a running backend server. Now, Docker Compose orchestrates:
- The PyKaraoke backend HTTP API server
- The integration test runner that connects to the server

## Test Categories

### Unit Tests
Tests that run locally without external dependencies:
```bash
docker compose --profile test run test
```

### Integration Tests
Tests that require a running backend server:
```bash
docker compose --profile integration run test-integration
```

### All Tests
Both unit and integration tests:
```bash
docker compose --profile test run test-all
```

### With Coverage Reports
```bash
docker compose --profile test run test-coverage
docker compose --profile integration run test-all-coverage
```

## Available Commands

### Run Unit Tests Only
```bash
cd deploy/docker
docker compose --profile test run test
```

### Run Integration Tests Only
The backend server will start automatically and tests will run once it's healthy:
```bash
cd deploy/docker
docker compose --profile integration run test-integration
```

### Run All Tests
```bash
cd deploy/docker
docker compose --profile test run test-all
```

### Generate Coverage Report
```bash
cd deploy/docker
docker compose --profile test run test-all-coverage
```
Coverage results will be in `htmlcov/` directory.

### Run Specific Test File
```bash
cd deploy/docker
docker compose --profile integration run test-integration pytest tests/pykaraoke/core/test_backend_http.py -v
```

### Run Tests Matching a Pattern
```bash
cd deploy/docker
docker compose --profile test run test-all -k "test_health"
```

## Docker Compose Services

### `backend-test`
- **Profile**: `integration`
- **Purpose**: Runs the PyKaraoke backend HTTP API server
- **Port**: `8080`
- **Healthcheck**: Uses `/health` endpoint to verify readiness
- **Dependencies**: None (starts automatically)

### `test-integration`
- **Profile**: `integration`
- **Purpose**: Runs integration tests marked with `@pytest.mark.integration`
- **Dependencies**: Waits for `backend-test` to be healthy

### `test`
- **Profile**: `test`
- **Purpose**: Runs unit tests only (excludes integration tests)

### `test-coverage`
- **Profile**: `test`
- **Purpose**: Runs unit tests with coverage report generation

### `test-all`
- **Profile**: `test`
- **Purpose**: Runs all tests (unit + integration)
- **Dependencies**: Waits for `backend-test` to be healthy

### `test-all-coverage`
- **Profile**: `test`
- **Purpose**: Runs all tests with coverage report
- **Dependencies**: Waits for `backend-test` to be healthy

## Environment Variables

### `PYKARAOKE_API_URL`
Set in integration test containers to communicate with the backend:
- Default (when not in Docker): `http://localhost:8080`
- Docker Compose: `http://backend-test:8080`

### `SONGS_DIR`
Directory containing test songs (optional):
```bash
SONGS_DIR=/path/to/songs docker compose --profile integration run test-integration
```

## Writing Integration Tests

### Marking Tests
Add the `@pytest.mark.integration` decorator to integration test methods:

```python
import pytest

class TestHTTPEndpoints:
    @pytest.mark.integration
    def test_health_endpoint(self):
        """Test /health endpoint"""
        import urllib.request
        api_url = os.environ.get("PYKARAOKE_API_URL", "http://localhost:8080")
        response = urllib.request.urlopen(f"{api_url}/health", timeout=5)
        assert response.status == 200
```

### Module-Level Marking
To mark all tests in a file as integration tests:

```python
import pytest

pytestmark = pytest.mark.integration

class TestIntegration:
    def test_something(self):
        pass
```

### Graceful Degradation
Always wrap server calls with proper exception handling:

```python
@pytest.mark.integration
def test_endpoint(self):
    try:
        response = urllib.request.urlopen(url, timeout=5)
        assert response.status == 200
    except urllib.error.URLError:
        pytest.skip("Backend API server not running")
```

## Troubleshooting

### Backend Server Won't Start
Check logs:
```bash
docker compose logs backend-test
```

### Tests Timing Out
Increase the healthcheck timeout in `docker-compose.yml` or wait longer:
```bash
docker compose --profile integration run --timeout 60 test-integration
```

### Port Already in Use
The container's port 8080 is dynamically assigned. If you need a specific port:
```bash
docker compose --profile integration run -p 8080:8080 backend-test
```

### Permission Issues
Ensure the songs directory is readable:
```bash
chmod -R a+r /path/to/songs
```

## CI/CD Integration

For continuous integration, run all tests including integration tests:
```bash
cd deploy/docker
docker compose --profile test run test-all
```

The exit code reflects test success (0) or failure (non-zero).

## Performance Notes

- First run downloads and builds images (~2-5 minutes depending on connection)
- Subsequent runs use cached layers (~10-30 seconds for test startup)
- Backend healthcheck adds ~2-5 seconds per run
- Add `--quiet` flag to reduce output verbosity

## See Also

- [Development Setup](./quality-improvements.md)
- [Docker Setup](./sonarqube-setup.md)
- Main [README](../README.md)
