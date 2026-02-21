#!/bin/bash
# Script to run tests with Docker Compose
# Usage: ./test-docker.sh [unit|integration|all|coverage]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="${SCRIPT_DIR}/deploy/docker"

# Default to all tests
TEST_TYPE="${1:-all}"

cd "$DOCKER_DIR"

case "$TEST_TYPE" in
  unit)
    echo "Running unit tests..."
    docker compose --profile test run test
    ;;
  integration)
    echo "Running integration tests..."
    docker compose --profile integration run test-integration
    ;;
  all)
    echo "Running all tests (unit + integration)..."
    docker compose --profile test run test-all
    ;;
  coverage)
    echo "Running all tests with coverage report..."
    docker compose --profile test run test-all-coverage
    echo ""
    echo "Coverage report generated in htmlcov/index.html"
    ;;
  *)
    echo "Usage: $0 [unit|integration|all|coverage]"
    echo ""
    echo "  unit        - Run unit tests only"
    echo "  integration - Run integration tests only (requires Docker)"
    echo "  all         - Run all tests (unit + integration) (requires Docker)"
    echo "  coverage    - Run all tests with coverage report (requires Docker)"
    echo ""
    exit 1
    ;;
esac
