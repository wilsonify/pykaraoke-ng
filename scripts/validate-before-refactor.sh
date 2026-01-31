#!/usr/bin/env bash
#
# Pre-refactoring validation script
# Run this before making changes to ensure the codebase is in a good state.
#
# Usage:
#   ./scripts/validate-before-refactor.sh
#
set -uo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  PyKaraoke Pre-Refactoring Validation  ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Track failures
FAILURES=0

# Helper functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    FAILURES=$((FAILURES + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Check virtual environment
echo -e "${BLUE}1. Checking virtual environment...${NC}"
if [[ -f "$VENV_DIR/bin/activate" ]]; then
    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"
    check_pass "Virtual environment found and activated"
else
    check_fail "Virtual environment not found. Run: bash scripts/setup-dev-env.sh"
    echo -e "${RED}Cannot continue without virtual environment.${NC}"
    exit 1
fi

# 2. Check Python version
echo -e "${BLUE}2. Checking Python version...${NC}"
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR="${PYTHON_VERSION%%.*}"
if [[ "$PYTHON_MAJOR" -ge 3 ]]; then
    check_pass "Python $PYTHON_VERSION detected"
else
    check_warn "Python $PYTHON_VERSION detected (Python 3.x recommended)"
fi

# 3. Check required packages
echo -e "${BLUE}3. Checking required packages...${NC}"

if python -c "import pytest" >/dev/null 2>&1; then
    check_pass "pytest is installed"
else
    check_fail "pytest not installed"
fi

if python -c "import selenium" >/dev/null 2>&1; then
    check_pass "selenium is installed"
else
    check_warn "selenium not installed (optional, for E2E tests)"
fi

# 4. Check test files exist
echo -e "${BLUE}4. Checking test files...${NC}"
TEST_COUNT=$(find "$ROOT_DIR/tests" -name "test_*.py" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$TEST_COUNT" -gt 0 ]]; then
    check_pass "Found $TEST_COUNT test file(s)"
else
    check_fail "No test files found"
fi

# 5. Check Python 3 test files have valid syntax
echo -e "${BLUE}5. Checking test file syntax...${NC}"
SYNTAX_ERRORS=0
for file in "$ROOT_DIR/tests"/test_*.py; do
    if [[ -f "$file" ]]; then
        if ! python -m py_compile "$file" 2>/dev/null; then
            check_fail "Syntax error in: $(basename "$file")"
            SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
        fi
    fi
done

if [[ $SYNTAX_ERRORS -eq 0 ]]; then
    check_pass "All test files have valid Python 3 syntax"
fi

# Note about Python 2 source files
echo ""
check_warn "Note: Main source files (*.py in root) are Python 2 - to be refactored"

# 6. Run the test suite
echo ""
echo -e "${BLUE}6. Running test suite...${NC}"
echo ""
if python -m pytest "$ROOT_DIR/tests" -q --tb=line 2>&1; then
    echo ""
    check_pass "All tests passed"
else
    echo ""
    check_fail "Some tests failed"
fi

# 7. Check for uncommitted changes
echo ""
echo -e "${BLUE}7. Checking git status...${NC}"
if [[ -d "$ROOT_DIR/.git" ]]; then
    UNCOMMITTED=$(git -C "$ROOT_DIR" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$UNCOMMITTED" -eq 0 ]]; then
        check_pass "No uncommitted changes"
    else
        check_warn "$UNCOMMITTED uncommitted change(s) - consider committing before refactoring"
        git -C "$ROOT_DIR" status --short 2>/dev/null || true
    fi
else
    check_warn "Not a git repository"
fi

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
if [[ $FAILURES -eq 0 ]]; then
    echo -e "${GREEN}  VALIDATION PASSED${NC}"
    echo -e "${GREEN}  Ready for refactoring!${NC}"
else
    echo -e "${RED}  VALIDATION FAILED${NC}"
    echo -e "${RED}  $FAILURES issue(s) found. Please fix before refactoring.${NC}"
fi
echo -e "${BLUE}========================================${NC}"

exit $FAILURES
