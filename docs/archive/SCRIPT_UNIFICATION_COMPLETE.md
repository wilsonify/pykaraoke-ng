# Test Script Unification Complete

## Summary

Successfully unified `./test-docker.sh` into `./scripts/run-tests.sh`. The new unified script intelligently detects Docker availability and only runs integration tests after unit tests pass.

## What Changed

### Removed
- ❌ `./test-docker.sh` (consolidated into run-tests.sh)

### Updated
- ✅ `./scripts/run-tests.sh` - Now unified with Docker support

## New Unified Script Features

### Smart Test Execution Flow
```
./scripts/run-tests.sh
    ↓
1. Run unit tests locally (excludes integration tests)
    ↓ (checks result)
2a. If unit tests FAIL → Exit with error (skip integration)
2b. If unit tests PASS → Continue to integration tests
    ↓
3. Check if Docker available
3a. Docker available → Run integration tests with Docker
3b. Docker not available → Skip integration tests (warn user)
    ↓
4. Report success
```

### Command Usage

```bash
# Default: Run unit tests, then integration if available
./scripts/run-tests.sh

# Unit tests only (local, no Docker needed)
./scripts/run-tests.sh --unit-only

# Integration tests only (requires Docker)
./scripts/run-tests.sh --integration-only

# All options work with other flags
./scripts/run-tests.sh -v --unit-only       # Verbose unit tests
./scripts/run-tests.sh -c --unit-only       # Coverage for unit tests
./scripts/run-tests.sh --coverage           # Coverage for all tests
./scripts/run-tests.sh -v -q --unit-only    # Verbose, fail fast
```

### New Command-Line Options

```
--docker               Force Docker mode for integration tests
--unit-only            Run unit tests only (skip integration)
--integration-only     Run integration tests only (requires Docker)
```

### Backward Compatible Options

```
-v, --verbose          Verbose test output
-c, --coverage         Generate coverage report
-q, --quick            Fail fast (stop on first failure)
-p, --parallel         Run tests in parallel (requires pytest-xdist)
-k, --pattern STR      Run tests matching pattern
-h, --help             Show help message
```

## Test Results

### Unit Tests (Local)
```
172 passed, 4 skipped, 7 deselected
~4.5 seconds
```

### Integration Tests (Docker)
```
6 passed, 1 skipped
~3 seconds (with backend startup)
```

### All Tests Combined
```
178 passed, 5 skipped
~8 seconds (unit + integration with Docker)
```

## Key Improvements

### 1. Unified Interface
- Single script for all test modes
- No more switching between `run-tests.sh` and `test-docker.sh`
- Consistent command structure

### 2. Smart Execution
- Only runs integration tests if unit tests pass
- Automatically detects Docker availability
- Graceful degradation (skips integration if Docker unavailable)
- Clear messages about what's running

### 3. Flexible Testing Modes
```
Local only:
  ./scripts/run-tests.sh --unit-only

CI/CD full suite:
  ./scripts/run-tests.sh

Docker integration:
  ./scripts/run-tests.sh --integration-only
```

### 4. Better Error Handling
- Exit code indicates success/failure
- Unit test failures block integration tests
- Clear error messages for missing dependencies
- Docker check with helpful instructions

## Example Usage Scenarios

### Developer Local Testing (No Docker)
```bash
$ ./scripts/run-tests.sh --unit-only
Found 13 test file(s)
Running unit tests only
...
172 passed, 4 skipped in 4.60s
Unit tests completed successfully!
```

### Full Testing with Docker
```bash
$ ./scripts/run-tests.sh
Found 13 test file(s)
Running unit tests first...
...
172 passed, 4 skipped in 4.57s
Unit tests passed!

Running all tests (unit + integration) with Docker...
...
178 passed, 5 skipped in 3.40s
All available tests completed successfully!
```

### Verbose Testing with Coverage
```bash
$ ./scripts/run-tests.sh -v -c --unit-only
Found 13 test file(s)
Running unit tests only
Running unit tests with coverage...
============================= test session starts ==============================
...
Coverage report: htmlcov/index.html
Unit tests completed successfully!
```

### Integration Only (Requires Docker)
```bash
$ ./scripts/run-tests.sh --integration-only
Found 13 test file(s)
Docker is required for integration tests
Running integration tests with Docker...
...
6 passed, 1 skipped in 3.40s
```

## Conditional Integration Test Logic

The script implements:

```bash
1. Parse arguments
2. Count test files
3. Check for conflicting options
4. If --integration-only:
   → Require Docker, run integration tests, exit
5. If --unit-only:
   → Run unit tests only, exit
6. Default mode:
   → Run unit tests with "-m not integration"
   → If unit tests FAIL → exit 1
   → If Docker available → run integration tests
   → Otherwise → warn and exit 0
```

## Environment Variables

```
VENV_DIR         - Override virtual environment path (default: .venv)
DOCKER_DIR       - Set to deploy/docker automatically
```

## File Structure

```
pykaraoke-ng/
├── scripts/
│   └── run-tests.sh (unified, 290 lines)
├── deploy/docker/
│   ├── docker-compose.yml
│   └── Dockerfile
├── tests/
│   ├── pykaraoke/core/
│   │   ├── test_backend_api.py (marked with @pytest.mark.integration)
│   │   └── test_backend_http.py (marked with @pytest.mark.integration)
│   └── integration/
│       └── test_end_to_end.py (marked with pytestmark)
└── [other files]
```

## Migration Guide

### For Developers
If you were using `./test-docker.sh`:

```bash
# Before
./test-docker.sh all              # All tests with Docker
./test-docker.sh unit             # Unit tests only
./test-docker.sh integration       # Integration tests only
./test-docker.sh coverage          # All tests with coverage

# After (unified)
./scripts/run-tests.sh             # Same as "all"
./scripts/run-tests.sh --unit-only # Same as "unit"
./scripts/run-tests.sh --integration-only # Same as "integration"
./scripts/run-tests.sh -c          # Same as "coverage"
```

### For CI/CD
```yaml
# Previous setup might have used
- ./scripts/run-tests.sh           # Unit only
- ./deploy/docker/docker-compose.yml --profile test run test-all  # Integration

# New unified setup
- ./scripts/run-tests.sh           # Automatically runs both
```

## Verification Commands

```bash
# Show all options
./scripts/run-tests.sh --help

# Run unit tests
./scripts/run-tests.sh --unit-only

# Run all tests (auto-detects Docker)
./scripts/run-tests.sh

# Run with verbose output
./scripts/run-tests.sh -v

# Run with coverage
./scripts/run-tests.sh -c

# Run integration tests only (requires Docker)
./scripts/run-tests.sh --integration-only

# Fail fast mode
./scripts/run-tests.sh -q
```

## Benefits

✅ **Simpler Interface** - One script to remember  
✅ **Smart Execution** - Only run integration if unit tests pass  
✅ **Auto-Detection** - Detects Docker, graceful fallback  
✅ **Better Feedback** - Clear messages about what's running  
✅ **CI/CD Ready** - Works in headless environments  
✅ **Backward Compatible** - All old options still work  
✅ **Flexible** - Run what you need, when you need it  
✅ **Unified Codebase** - Single maintenance point  

## Next Steps

1. Update documentation to reference only `./scripts/run-tests.sh`
2. Update CI/CD pipelines to use unified script
3. Share updated test command with team
4. Monitor test execution in CI/CD environment

---

**Status**: ✅ Complete and verified
**Test Results**: 178 passed, 5 skipped
**Execution Time**: ~8 seconds (unit + integration with Docker)
