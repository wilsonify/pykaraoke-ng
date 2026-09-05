#!/usr/bin/env bash
#
# Run the PyKaraoke-NG test suite.
#
#   pytest    engine unit tests (CPython)
#   vitest    web UI logic tests
#   smoke     verify the built web app serves its assets (and, when a
#             chromium is available, that the PyScript engine boots)
#
# Usage:
#   ./scripts/run-tests.sh            # everything
#   ./scripts/run-tests.sh --engine   # pytest only
#   ./scripts/run-tests.sh --web      # vitest only
#   ./scripts/run-tests.sh --smoke    # UI smoke test only
#   ./scripts/run-tests.sh --verbose
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"

MODE=all
VERBOSE=0
if [[ $# -gt 0 ]]; then
  case "$1" in
    --engine) MODE=engine ;;
    --web) MODE=web ;;
    --smoke) MODE=smoke ;;
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

smoke_test() {
  echo "==> UI smoke test"
  run_python "$ROOT_DIR/scripts/ui-smoke.py"
}

case "$MODE" in
  engine) engine_tests ;;
  web) web_tests ;;
  smoke) smoke_test ;;
  all)
    engine_tests
    web_tests
    smoke_test
    ;;
esac

echo "All requested tests passed."