# End-to-End Failure Analysis

## Defect #1: UnicodeEncodeError in manual backend mode tests

### Test File
`tests/manual/test_backend_modes.py`

### Affected Tests
- `test_stdio_help`
- `test_http_mode_startup`
- `test_stdio_mode_startup`

### Failing Tests
All 3 tests failed with identical symptom.

### Observed Behavior
```
FAILED tests/manual/test_backend_modes.py::test_stdio_help - UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'...
FAILED tests/manual/test_backend_modes.py::test_http_mode_startup - UnicodeEncodeError...
FAILED tests/manual/test_backend_modes.py::test_stdio_mode_startup - UnicodeEncodeError...
```

The error occurs at the `print()` statement after the assertion:
```
print("✓ Help output looks good")
```

### Expected Behavior
The tests should pass on all platforms, printing simple ASCII progress markers.

### Root Cause
The test file uses Unicode character `\u2713` (CHECK MARK, ✓) and `\u2705` (WHITE HEAVY CHECK MARK, ✅) in `print()` statements. On Windows with cp1252 console encoding, these characters cannot be encoded, raising a `UnicodeEncodeError`.

### Remediation
Replace all Unicode print statements with ASCII equivalents:
- `✓` -> `[OK]`
- `✅` -> `[PASS]`

### Files Modified
- `tests/manual/test_backend_modes.py` — 4 print statement replacements

### Regression Prevention
No additional coverage needed — this is a purely cosmetic output encoding issue.

---

## Build & Integration Summary

### Build Status: PASS
- sdist and wheel build successfully via `python -m build`
- No compilation errors

### Unit Tests: 529/529 PASS
All unit tests in `tests/pykaraoke/` pass.

### Integration Tests: 1/1 PASS
`tests/integration/test_end_to_end.py` passes (Selenium portion skipped gracefully).

### Static Analysis Tests: 15/15 PASS
`tests/integration/test_tauri_packaging.py` — all 15 static regression checks pass.

### Selenium UI Tests: 22 SKIPPED
`tests/integration/test_ui_buttons.py` — all 22 tests skipped because `selenium` host is not resolvable (expected in non-Docker environment).

### Total Test Suite: 626 PASS, 33 SKIP, 0 FAIL

## Skipped Tests (Environment-Dependent)

| Count | Reason | Environment |
|-------|--------|-------------|
| 22 | Selenium host not resolvable | Docker/CI |
| 3 | Platform-specific (POSIX/macOS/Linux) | Non-matching OS |
| 4 | Backend API server not running | CI Docker |
| 2 | Backend startup failed | Full environment |
| 2 | Performer prompt requires wx | wxPython not installed |
