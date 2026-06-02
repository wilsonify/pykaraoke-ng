# Reliability Report

Date: 2026-06-02

## Reliability Areas Reviewed
- Test execution resilience
- Environment portability
- Failure handling in integration fixtures
- Build toolchain consistency

## Issues Found and Fixed

### 1) Manual backend subprocess tests failed on Windows due to replaced environment
- Root cause: subprocess env argument replaced full environment with PYTHONPATH only
- Fix: preserve os.environ.copy() and inject PYTHONPATH
- File: tests/manual/test_backend_modes.py
- Validation: targeted test module passes

### 2) Selenium integration tests errored instead of skipping in local non-compose runs
- Root cause: fixture always attempted remote driver creation against non-resolvable host
- Fix: preflight host resolution and skip when unavailable; catch WebDriverException
- File: tests/integration/test_ui_buttons.py
- Validation: module now cleanly skips when selenium host is unavailable

### 3) Cross-platform test-runner portability gaps
- Root cause: scripts/run-tests.sh expected POSIX venv layout and docker-compose binary only
- Fix: added Windows venv activation/python paths and Docker Compose plugin detection
- File: scripts/run-tests.sh
- Validation: static review and command-path logic verification

## Remaining Reliability Risks
- Integration and E2E tests still depend on external services (Docker stack)
- Some tests are environment-sensitive and skip by design when dependencies are missing

