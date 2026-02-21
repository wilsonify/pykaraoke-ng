# Test Troubleshooting Guide

This guide helps resolve common issues when running tests for PyKaraoke-NG.

## Quick Fix: Ensure All Tests Pass

If tests are failing, follow these steps in order:

### 1. Setup Development Environment

```bash
# Run the setup script
./scripts/setup-dev-env.sh

# Or for legacy pip/venv setup:
./scripts/setup-dev-env.sh --legacy
```

### 2. Verify Package Installation

The most common issue is that the `pykaraoke` package is not installed in editable mode. Tests need to import the package.

```bash
# Activate virtual environment
source .venv/bin/activate

# Verify package is installed
python -c "import pykaraoke; print(pykaraoke.__file__)"

# If not installed, install in editable mode
pip install -e .
```

### 3. Run Tests

```bash
# Run all tests
./scripts/run-tests.sh

# Or directly with pytest
python -m pytest -v

# With coverage
./scripts/run-tests.sh --coverage
```

## Common Issues

### Issue: `ModuleNotFoundError: No module named 'pykaraoke'`

**Cause**: Package not installed in the Python environment.

**Solution**:

```bash
# Activate virtual environment
source .venv/bin/activate

# Install package in editable mode
pip install -e .

# Run tests again
python -m pytest -v
```

### Issue: `ERROR: Package 'pykaraoke-ng' requires a different Python`

**Cause**: Using Python < 3.10, but package requires Python 3.10+.

**Solution**:

```bash
# Check Python version in venv
.venv/bin/python --version

# If version is < 3.10, recreate venv with Python 3.10+
rm -rf .venv
python3.10 -m venv .venv  # or python3.11, python3.13, etc.
source .venv/bin/activate
pip install -e ".[dev,test]"
```

### Issue: `OSError: Readme file does not exist: README.txt`

**Cause**: `pyproject.toml` references wrong README filename.

**Solution**: Already fixed in `pyproject.toml`. If you see this error:

```bash
# Edit pyproject.toml line 5
# Change: readme = "README.txt"
# To:     readme = "README.md"
```

### Issue: Tests run but fail with import errors inside test files

**Cause**: Virtual environment not activated or wrong Python interpreter.

**Solution**:

```bash
# Always use the virtual environment's Python
source .venv/bin/activate
python -m pytest -v

# Or use absolute path
.venv/bin/python -m pytest -v
```

## Expected Test Results

When all tests pass, you should see:

```bash
======================== 126 passed, 6 skipped in 0.63s ========================
```

**Skipped tests** are normal and include:

- Platform-specific tests (Windows/macOS on Linux, etc.)
- Tests requiring full pygame environment

**126 passed** = All functional tests working ✓

## Manual Verification

If automated tests pass but you want to verify manually:

```bash
# Check package imports
python -c "from pykaraoke.config import constants, environment, version; print('✓ Config modules OK')"

# Check players import
python -c "from pykaraoke.players import cdg, kar, mpg; print('✓ Player modules OK')"

# Check core imports
python -c "from pykaraoke.core import backend, database, manager; print('✓ Core modules OK')"
```

## CI/CD Setup

For continuous integration:

```bash
# Setup in CI mode (minimal dependencies)
./scripts/setup-dev-env.sh --ci

# Run tests
./scripts/run-tests.sh --quick --coverage
```

## Getting Help

If issues persist:

1. Check [Developer Guide](../docs/developers.md)
2. Verify Python version: `python --version` (must be 3.10+)
3. Check virtual environment: `which python` (should point to `.venv/bin/python`)
4. Reinstall dependencies: `pip install -e ".[dev,test]"`
5. Open an issue on GitHub with test output

## Test Organization

```txt
tests/
├── integration/          # End-to-end tests
├── pykaraoke/
│   ├── config/          # Configuration tests
│   ├── core/            # Core functionality tests
│   └── players/         # Player format tests
└── test_settings.py     # Settings tests
```

Each test module corresponds to source code in `src/pykaraoke/`.
