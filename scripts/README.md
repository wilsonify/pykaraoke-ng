# Development Scripts

This directory contains scripts to help with development, testing, and deployment of PyKaraoke-NG.

## Quick Start

```bash
# Setup development environment
./scripts/setup-dev-env.sh

# Run all tests
./scripts/run-tests.sh

# Run tests with coverage
./scripts/run-tests.sh --coverage
```

## Available Scripts

### Development Setup

#### `setup-dev-env.sh`
Sets up the development environment with all necessary dependencies.

**Usage:**
```bash
./scripts/setup-dev-env.sh           # Standard setup
./scripts/setup-dev-env.sh --full    # Include GUI dependencies
./scripts/setup-dev-env.sh --ci      # CI mode (no GUI deps)
./scripts/setup-dev-env.sh --legacy  # Use pip/venv (fallback)
```

**What it does:**
- Creates a Python virtual environment in `.venv/`
- Installs the package in editable mode (`pip install -e .`)
- Installs development and test dependencies
- Optionally installs GUI dependencies (wxPython)
- Sets up pre-commit hooks

**Requirements:**
- Python 3.10 or higher
- Either `uv` (recommended) or `pip` and `venv`

### Testing

#### `run-tests.sh`
Runs the test suite with various options.

**Usage:**
```bash
./scripts/run-tests.sh              # Run all tests
./scripts/run-tests.sh --verbose    # Verbose output
./scripts/run-tests.sh --coverage   # Run with coverage report
./scripts/run-tests.sh --quick      # Fail fast mode
./scripts/run-tests.sh --parallel   # Run tests in parallel
./scripts/run-tests.sh --pattern    # Run tests matching pattern
```

**Options:**
- `-v, --verbose` - Show detailed test output
- `-c, --coverage` - Generate HTML coverage report in `htmlcov/`
- `-q, --quick` - Stop on first test failure
- `-p, --parallel` - Run tests in parallel (faster)
- `-k, --pattern PATTERN` - Run only tests matching pattern
- `-h, --help` - Show help message

**Examples:**
```bash
# Run only config tests
./scripts/run-tests.sh -k config

# Fast fail with verbose output
./scripts/run-tests.sh -q -v

# Full coverage report
./scripts/run-tests.sh --coverage
```

**Expected Output:**
```
126 passed, 6 skipped in 0.25s
Tests completed successfully!
```

### Validation Scripts

#### `validate-before-refactor.sh`
Captures baseline test and code metrics before refactoring.

#### `validate-refactor.sh`
Compares current state against baseline to ensure refactoring didn't break anything.

### Utility Scripts

#### `test-utils.sh`
Common test utilities and helper functions (sourced by other scripts).

### Kubernetes

#### `kind-setup.sh`
Sets up a local Kubernetes cluster using kind for testing deployments.

### Build Scripts

#### `build/cross-build-gp2x.sh`
Cross-compilation script for GP2X handheld device (legacy platform).

## Troubleshooting

If tests fail, see [Test Troubleshooting Guide](troubleshooting-tests.md) for common issues and solutions.

### Common Issues

**Tests fail with `ModuleNotFoundError: No module named 'pykaraoke'`**
```bash
# Install package in editable mode
source .venv/bin/activate
pip install -e .
```

**Wrong Python version**
```bash
# Check version (needs 3.10+)
python --version

# Recreate venv with correct Python
rm -rf .venv
python3.10 -m venv .venv  # or python3.11, python3.13, etc.
./scripts/setup-dev-env.sh
```

**Virtual environment not activated**
```bash
# Always activate before running commands
source .venv/bin/activate

# Or use the script which handles this automatically
./scripts/run-tests.sh
```

## CI/CD Integration

For continuous integration pipelines:

```bash
# Quick setup and test
./scripts/setup-dev-env.sh --ci
./scripts/run-tests.sh --quick --coverage

# Or use uv directly
uv sync --extra test
uv run pytest --cov=src --cov-report=xml
```

## Environment Variables

Scripts respect these environment variables:

- `VENV_DIR` - Custom virtual environment location (default: `.venv`)
- `PYTHON_BIN` - Python executable to use (default: `python3`)
- `UV_LINK_MODE` - UV linking mode for installations (e.g., `copy`)

## Script Maintenance

All scripts follow these conventions:
- Use `set -euo pipefail` for safety
- Support `--help` flag
- Provide colored output for readability
- Handle both modern (`uv`) and legacy (`pip`) workflows
- Are executable (`chmod +x`)

## Getting Help

1. Check script help: `./scripts/<script-name>.sh --help`
2. Review [Test Troubleshooting Guide](troubleshooting-tests.md)
3. See [Developer Guide](../docs/developers.md)
4. Open an issue on GitHub

## Contributing

When adding new scripts:
1. Make them executable: `chmod +x scripts/new-script.sh`
2. Add usage documentation in the header
3. Support `--help` flag
4. Update this README
5. Use consistent error handling and output formatting
