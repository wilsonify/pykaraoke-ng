#!/usr/bin/env bash
#
# Run the PyKaraoke test suite
#
# Usage:
#   ./scripts/run-tests.sh              # Run all tests
#   ./scripts/run-tests.sh --verbose    # Verbose output
#   ./scripts/run-tests.sh --coverage   # Run with coverage report
#   ./scripts/run-tests.sh --quick      # Fail fast mode
#   ./scripts/run-tests.sh --help       # Show help
#
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
TESTS_DIR="$ROOT_DIR/tests"

# Default options
VERBOSE=0
COVERAGE=0
QUICK=0
PATTERN=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--verbose)
      VERBOSE=1
      shift
      ;;
    -c|--coverage)
      COVERAGE=1
      shift
      ;;
    -q|--quick)
      QUICK=1
      shift
      ;;
    -k|--pattern)
      PATTERN="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  -v, --verbose     Verbose test output"
      echo "  -c, --coverage    Generate coverage report"
      echo "  -q, --quick       Fail fast (stop on first failure)"
      echo "  -k, --pattern     Run tests matching pattern"
      echo "  -h, --help        Show this help message"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}" >&2
      exit 1
      ;;
  esac
done

# Check virtual environment
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo -e "${RED}Error: virtual environment not found at $VENV_DIR.${NC}" >&2
  echo -e "${YELLOW}Run: bash scripts/setup-dev-env.sh${NC}" >&2
  exit 1
fi

# Count test files
TEST_COUNT=$(find "$TESTS_DIR" -type f \( -name "test_*.py" -o -name "*_test.py" \) 2>/dev/null | wc -l | tr -d ' ')

if [[ "$TEST_COUNT" == "0" ]]; then
  echo -e "${YELLOW}No tests found (no test_*.py or *_test.py files).${NC}"
  exit 0
fi

echo -e "${BLUE}Found $TEST_COUNT test file(s)${NC}"

# Build pytest arguments
PYTEST_ARGS=("$TESTS_DIR")

if [[ $VERBOSE -eq 1 ]]; then
  PYTEST_ARGS+=("-v" "-s")
fi

if [[ $QUICK -eq 1 ]]; then
  PYTEST_ARGS+=("-x")
fi

if [[ -n "$PATTERN" ]]; then
  PYTEST_ARGS+=("-k" "$PATTERN")
fi

# Run with pytest if available
if python -c "import pytest" >/dev/null 2>&1; then
  if [[ $COVERAGE -eq 1 ]]; then
    if python -c "import coverage" >/dev/null 2>&1; then
      echo -e "${BLUE}Running tests with coverage...${NC}"
      python -m pytest "${PYTEST_ARGS[@]}" \
        --cov="$ROOT_DIR" \
        --cov-report=term-missing \
        --cov-report=html:"$ROOT_DIR/htmlcov" \
        --cov-config="$ROOT_DIR/.coveragerc" 2>/dev/null || \
      python -m pytest "${PYTEST_ARGS[@]}" \
        --cov="$ROOT_DIR" \
        --cov-report=term-missing \
        --cov-report=html:"$ROOT_DIR/htmlcov"
      
      if [[ -d "$ROOT_DIR/htmlcov" ]]; then
        echo -e "${GREEN}Coverage report: $ROOT_DIR/htmlcov/index.html${NC}"
      fi
    else
      echo -e "${YELLOW}Warning: coverage package not installed, running without coverage${NC}"
      python -m pytest "${PYTEST_ARGS[@]}"
    fi
  else
    python -m pytest "${PYTEST_ARGS[@]}"
  fi
else
  echo -e "${YELLOW}Warning: pytest not installed, using unittest${NC}"
  python -m unittest discover -s "$TESTS_DIR" -p "test*.py"
fi

echo -e "${GREEN}Tests completed successfully!${NC}"
