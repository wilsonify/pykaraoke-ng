#!/usr/bin/env bash
#
# Run the PyKaraoke-NG test suite.
#
#   pytest    engine unit tests (CPython) — src/pykaraoke
#   vitest    web UI logic tests — extracted from src/web/index.html
#
# Usage:
#   ./src/scripts/run-tests.sh            # everything
#   ./src/scripts/run-tests.sh --engine   # pytest only
#   ./src/scripts/run-tests.sh --web      # vitest only
#   ./src/scripts/run-tests.sh --verbose
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"

MODE=all
VERBOSE=0
if [[ $# -gt 0 ]]; then
  case "$1" in
    --engine) MODE=engine ;;
    --web) MODE=web ;;
    --verbose) VERBOSE=1 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
fi

# Prefer the project venv; fall back to whatever python is on PATH.
run_python() {
  if [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
    "$VENV_DIR/Scripts/python.exe" "$@"
  elif [[ -x "$VENV_DIR/bin/python" ]]; then
    "$VENV_DIR/bin/python" "$@"
  else
    python3 "$@"
  fi
}

engine_tests() {
  echo "==> pytest (engine)"
  run_python -m pytest tests/pykaraoke -q
}

web_tests() {
  echo "==> vitest (web logic)"
  if [[ ! -d "$ROOT_DIR/tests/web/node_modules" ]]; then
    (cd "$ROOT_DIR/tests/web" && npm install)
  fi
  (cd "$ROOT_DIR/tests/web" && npm test)
}

case "$MODE" in
  engine) engine_tests ;;
  web) web_tests ;;
  all)
    engine_tests
    web_tests
    ;;
esac

echo "All requested tests passed."