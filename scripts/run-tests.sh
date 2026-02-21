#!/usr/bin/env bash
#
# Run the PyKaraoke test suite (locally or with Docker)
#
# Usage:
#   ./scripts/run-tests.sh              # Run all tests (unit locally, integration with Docker if available)
#   ./scripts/run-tests.sh --verbose    # Verbose output
#   ./scripts/run-tests.sh --coverage   # Run with coverage report
#   ./scripts/run-tests.sh --quick      # Fail fast mode
#   ./scripts/run-tests.sh --parallel   # Run tests in parallel
#   ./scripts/run-tests.sh --docker     # Force Docker mode for integration tests
#   ./scripts/run-tests.sh --unit-only  # Run unit tests only (skip integration)
#   ./scripts/run-tests.sh --integration-only  # Run integration tests only (requires Docker)
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
DOCKER_DIR="$ROOT_DIR/deploy/docker"

# Default options
VERBOSE=0
COVERAGE=0
QUICK=0
PARALLEL=0
PATTERN=""
FORCE_DOCKER=0
UNIT_ONLY=0
INTEGRATION_ONLY=0

# Determine how to run Python (prefer uv if available)
run_python() {
    if command -v uv >/dev/null 2>&1 && [[ -f "$ROOT_DIR/pyproject.toml" ]]; then
        uv run "$@"
    elif [[ -f "$VENV_DIR/bin/activate" ]]; then
        # shellcheck disable=SC1090
        source "$VENV_DIR/bin/activate"
        python "$@"
    else
        echo -e "${RED}Error: No Python environment found.${NC}" >&2
        echo -e "${YELLOW}Run: bash scripts/setup-dev-env.sh${NC}" >&2
        exit 1
    fi
}

# Check if Docker is available
has_docker() {
    command -v docker >/dev/null 2>&1 && command -v docker-compose >/dev/null 2>&1
}

# Run tests with Docker Compose
run_integration_tests_docker() {
    local test_cmd="$1"
    
    if ! has_docker; then
        echo -e "${YELLOW}Docker not available. Skipping integration tests.${NC}"
        return 0
    fi
    
    cd "$DOCKER_DIR"
    
    case "$test_cmd" in
        "integration-only")
            echo -e "${BLUE}Running integration tests with Docker...${NC}"
            docker compose --profile integration run test-integration
            ;;
        "all-with-docker")
            echo -e "${BLUE}Running all tests (unit + integration) with Docker...${NC}"
            docker compose --profile test --profile integration run test-all
            ;;
        "coverage-with-docker")
            echo -e "${BLUE}Running all tests with coverage and Docker...${NC}"
            docker compose --profile test --profile integration run test-all-coverage
            echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
            ;;
    esac
    
    cd "$ROOT_DIR"
}

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
    -p|--parallel)
      PARALLEL=1
      shift
      ;;
    -k|--pattern)
      PATTERN="$2"
      shift 2
      ;;
    --docker)
      FORCE_DOCKER=1
      shift
      ;;
    --unit-only)
      UNIT_ONLY=1
      shift
      ;;
    --integration-only)
      INTEGRATION_ONLY=1
      FORCE_DOCKER=1
      shift
      ;;
    -h|--help)
      cat << 'EOF'
Usage: ./scripts/run-tests.sh [OPTIONS]

Options:
  -v, --verbose          Verbose test output
  -c, --coverage         Generate coverage report
  -q, --quick            Fail fast (stop on first failure)
  -p, --parallel         Run tests in parallel (requires pytest-xdist)
  -k, --pattern STR      Run tests matching pattern
  --docker               Force Docker mode for integration tests
  --unit-only            Run unit tests only (skip integration)
  --integration-only     Run integration tests only (requires Docker)
  -h, --help             Show this help message

Examples:
  ./scripts/run-tests.sh                    # Run all tests (auto-detect)
  ./scripts/run-tests.sh --unit-only        # Unit tests only
  ./scripts/run-tests.sh --integration-only # Integration tests only (Docker)
  ./scripts/run-tests.sh --coverage         # All tests with coverage
  ./scripts/run-tests.sh -v --quick         # Verbose, fail fast
EOF
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}" >&2
      exit 1
      ;;
  esac
done

# Count test files
TEST_COUNT=$(find "$TESTS_DIR" -type f \( -name "test_*.py" -o -name "*_test.py" \) 2>/dev/null | wc -l | tr -d ' ')

if [[ "$TEST_COUNT" == "0" ]]; then
  echo -e "${YELLOW}No tests found (no test_*.py or *_test.py files).${NC}"
  exit 0
fi

echo -e "${BLUE}Found $TEST_COUNT test file(s)${NC}"

# Check for conflicting options
if [[ $UNIT_ONLY -eq 1 && $INTEGRATION_ONLY -eq 1 ]]; then
  echo -e "${RED}Error: --unit-only and --integration-only are mutually exclusive${NC}" >&2
  exit 1
fi

# Determine test mode
if [[ $INTEGRATION_ONLY -eq 1 ]]; then
  # Run integration tests only
  if ! has_docker; then
    echo -e "${RED}Error: Docker is required for integration tests${NC}" >&2
    echo -e "${YELLOW}Install Docker and docker-compose, or use --unit-only${NC}" >&2
    exit 1
  fi
  run_integration_tests_docker "integration-only"
  exit $?
fi

if [[ $UNIT_ONLY -eq 1 ]]; then
  # Run unit tests only
  echo -e "${BLUE}Running unit tests only${NC}"
  
  # Build pytest arguments for unit tests only
  PYTEST_ARGS=("$TESTS_DIR" "-m" "not integration")
  
  if [[ $VERBOSE -eq 1 ]]; then
    PYTEST_ARGS+=("-v" "-s")
  fi
  
  if [[ $QUICK -eq 1 ]]; then
    PYTEST_ARGS+=("-x")
  fi
  
  if [[ $PARALLEL -eq 1 ]]; then
    PYTEST_ARGS+=("-n" "auto")
  fi
  
  if [[ -n "$PATTERN" ]]; then
    PYTEST_ARGS+=("-k" "$PATTERN")
  fi
  
  if [[ $COVERAGE -eq 1 ]]; then
    echo -e "${BLUE}Running unit tests with coverage...${NC}"
    run_python -m pytest "${PYTEST_ARGS[@]}" \
      --cov="$ROOT_DIR" \
      --cov-report=term-missing \
      --cov-report=html:"$ROOT_DIR/htmlcov" || exit $?
    
    if [[ -d "$ROOT_DIR/htmlcov" ]]; then
      echo -e "${GREEN}Coverage report: $ROOT_DIR/htmlcov/index.html${NC}"
    fi
  else
    run_python -m pytest "${PYTEST_ARGS[@]}" || exit $?
  fi
  
  echo -e "${GREEN}Unit tests completed successfully!${NC}"
  exit 0
fi

# Default mode: Run unit tests, then integration if available and successful
echo -e "${BLUE}Running unit tests first...${NC}"

# Build pytest arguments for unit tests
PYTEST_ARGS=("$TESTS_DIR" "-m" "not integration")

if [[ $VERBOSE -eq 1 ]]; then
  PYTEST_ARGS+=("-v" "-s")
fi

if [[ $QUICK -eq 1 ]]; then
  PYTEST_ARGS+=("-x")
fi

if [[ $PARALLEL -eq 1 ]]; then
  PYTEST_ARGS+=("-n" "auto")
fi

if [[ -n "$PATTERN" ]]; then
  PYTEST_ARGS+=("-k" "$PATTERN")
fi

# Run unit tests (without coverage first to check if they pass)
if [[ $COVERAGE -eq 1 ]]; then
  run_python -m pytest "${PYTEST_ARGS[@]}" \
    --cov="$ROOT_DIR" \
    --cov-report=term-missing \
    --cov-report=html:"$ROOT_DIR/htmlcov"
else
  run_python -m pytest "${PYTEST_ARGS[@]}"
fi

if [[ $? -ne 0 ]]; then
  echo -e "${RED}Unit tests failed. Skipping integration tests.${NC}"
  exit 1
fi

echo -e "${GREEN}Unit tests passed!${NC}"

# Check if we should run integration tests
if [[ $FORCE_DOCKER -eq 1 ]] || has_docker; then
  if [[ $FORCE_DOCKER -eq 1 ]] && ! has_docker; then
    echo -e "${YELLOW}Docker not available (--docker specified but Docker not found). Skipping integration tests.${NC}"
    exit 0
  fi
  
  if has_docker; then
    echo ""
    if [[ $COVERAGE -eq 1 ]]; then
      run_integration_tests_docker "coverage-with-docker"
    else
      run_integration_tests_docker "all-with-docker"
    fi
  fi
else
  echo -e "${YELLOW}Docker not available. Skipping integration tests.${NC}"
  echo -e "${YELLOW}To run integration tests, install Docker or use: ./scripts/run-tests.sh --unit-only${NC}"
fi

echo -e "${GREEN}All available tests completed successfully!${NC}"
