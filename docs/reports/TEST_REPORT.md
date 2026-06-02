# Test Report

Date: 2026-06-02

## Environment
- Host OS: Windows
- Validated Python interpreter: 3.13 (venv: .venv313)
- System Python 3.14 was not viable for full install due to pygame build path incompatibility in this environment

## Commands Executed
- py -3.13 -m venv .venv313
- .venv313/Scripts/python.exe -m pip install -e ".[dev,test,http]"
- .venv313/Scripts/python.exe -m pytest -q
- Focused rerun for former failures:
  - tests/integration/test_tauri_packaging.py
  - tests/manual/test_backend_modes.py
  - tests/integration/test_ui_buttons.py

## Results
- Full suite status: PASS (with expected skips)
- Previously failing tests now pass:
  - tests/integration/test_tauri_packaging.py::TestJavaScriptApiResilience::test_app_js_provides_invoke_fallback
  - tests/manual/test_backend_modes.py startup/help tests
- Previously erroring Selenium tests now SKIP cleanly when selenium host is not resolvable

## Skip Summary (Expected/Environment-driven)
- Selenium UI integration tests skip when SELENIUM_URL host is unavailable
- Platform-specific tests skip on non-target OS
- Backend integration tests skip when backend services are not running
- wx-dependent tests skip when wx is unavailable

## Defects Fixed
- Environment clobbering in subprocess tests (manual backend mode tests)
- Fragile Selenium fixture behavior in non-compose local runs
- Regression expectation mismatch for Tauri API fallback detection

## Coverage Notes
- Existing coverage tooling is configured and operational
- No new test files were required for this remediation because targeted regressions were covered by existing tests

