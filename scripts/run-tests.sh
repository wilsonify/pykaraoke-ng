#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"

if [[ -f "$VENV_DIR/bin/activate" ]]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo "Error: virtual environment not found at $VENV_DIR. Run scripts/setup-dev-env.sh first." >&2
  exit 1
fi

TEST_COUNT=$(find "$ROOT_DIR" -type f \( -name "test_*.py" -o -name "*_test.py" \) \
  -not -path "$ROOT_DIR/.venv/*" -not -path "$ROOT_DIR/scripts/*" | wc -l | tr -d ' ')

if [[ "$TEST_COUNT" == "0" ]]; then
  echo "No tests found (no test_*.py or *_test.py)."
  exit 0
fi

if python -c "import pytest" >/dev/null 2>&1; then
  python -m pytest
else
  python -m unittest discover -s "$ROOT_DIR" -p "test*.py"
fi
