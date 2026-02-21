#!/usr/bin/env bash
#
# Test utilities for pykaraoke-ng
# Source this file to get helper functions for testing.
#
# Usage: source scripts/test-utils.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
TESTS_DIR="$ROOT_DIR/tests"

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# Check if virtual environment exists and is activated
check_venv() {
    if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
        print_error "Virtual environment not found at $VENV_DIR"
        print_info "Run: bash scripts/setup-dev-env.sh"
        return 1
    fi
    
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        print_warning "Virtual environment not activated. Activating..."
        # shellcheck disable=SC1090
        source "$VENV_DIR/bin/activate"
    fi
    
    print_success "Virtual environment active: $VIRTUAL_ENV"
    return 0
}

# Check if pytest is available
check_pytest() {
    if ! python -c "import pytest" >/dev/null 2>&1; then
        print_error "pytest not installed"
        print_info "Run: pip install pytest"
        return 1
    fi
    print_success "pytest is available"
    return 0
}

# Count test files
count_test_files() {
    find "$TESTS_DIR" -type f \( -name "test_*.py" -o -name "*_test.py" \) | wc -l | tr -d ' '
}

# List all test files
list_test_files() {
    print_info "Test files in $TESTS_DIR:"
    find "$TESTS_DIR" -type f \( -name "test_*.py" -o -name "*_test.py" \) -exec basename {} \; | sort
}

# Run a single test file
run_single_test() {
    local test_file="$1"
    
    if [[ ! -f "$test_file" ]] && [[ -f "$TESTS_DIR/$test_file" ]]; then
        test_file="$TESTS_DIR/$test_file"
    fi
    
    if [[ ! -f "$test_file" ]]; then
        print_error "Test file not found: $test_file"
        return 1
    fi
    
    print_info "Running: $test_file"
    python -m pytest "$test_file" -v
}

# Run tests matching a pattern
run_tests_matching() {
    local pattern="$1"
    print_info "Running tests matching: $pattern"
    python -m pytest "$TESTS_DIR" -v -k "$pattern"
}

# Run tests with coverage
run_with_coverage() {
    if ! python -c "import coverage" >/dev/null 2>&1; then
        print_warning "coverage not installed, running without coverage"
        python -m pytest "$TESTS_DIR" -v
        return $?
    fi
    
    print_info "Running tests with coverage..."
    python -m pytest "$TESTS_DIR" -v --cov="$ROOT_DIR" --cov-report=term-missing --cov-report=html
    
    if [[ -d "$ROOT_DIR/htmlcov" ]]; then
        print_success "Coverage report generated: $ROOT_DIR/htmlcov/index.html"
    fi
}

# Check for pygame (required by main modules)
check_pygame() {
    if python -c "import pygame" >/dev/null 2>&1; then
        print_success "pygame is available"
        return 0
    else
        print_warning "pygame not installed - GUI-dependent tests will be skipped"
        return 1
    fi
}

# Print test environment info
print_test_env() {
    echo ""
    print_info "Test Environment Information"
    echo "=============================="
    echo "Root directory: $ROOT_DIR"
    echo "Virtual env: ${VIRTUAL_ENV:-not activated}"
    echo "Python: $(python --version 2>&1)"
    echo "Test files: $(count_test_files)"
    echo ""
    
    check_pytest || true
    check_pygame || true
    echo ""
}

# Quick test run (fail fast)
quick_test() {
    print_info "Running quick tests (fail fast)..."
    python -m pytest "$TESTS_DIR" -x -q
}

# Verbose test run with output
verbose_test() {
    print_info "Running verbose tests..."
    python -m pytest "$TESTS_DIR" -v -s
}

# Main entry point when script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    print_info "Test utilities loaded. Available functions:"
    echo ""
    echo "  check_venv         - Verify virtual environment"
    echo "  check_pytest       - Verify pytest is installed"
    echo "  count_test_files   - Count test files"
    echo "  list_test_files    - List all test files"
    echo "  run_single_test    - Run a single test file"
    echo "  run_tests_matching - Run tests matching pattern"
    echo "  run_with_coverage  - Run tests with coverage report"
    echo "  print_test_env     - Print environment info"
    echo "  quick_test         - Fast test run (fail fast)"
    echo "  verbose_test       - Verbose test run"
    echo ""
    echo "Usage: source scripts/test-utils.sh"
    echo "       Then call functions directly, e.g.: quick_test"
    echo ""
    
    # If sourced with an argument, run that function
    if [[ $# -gt 0 ]]; then
        cmd="$1"
        shift
        if declare -f "$cmd" >/dev/null; then
            "$cmd" "$@"
        else
            print_error "Unknown function: $cmd"
            exit 1
        fi
    fi
fi
