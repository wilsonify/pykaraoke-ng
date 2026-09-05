#!/usr/bin/env bash
#
# Set up the PyKaraoke-NG development environment.
#
# Creates a virtualenv (`.venv`), installs the engine + dev/test deps,
# builds the web assets (wheel + vendored Pyodide/PyScript), and installs
# the frontend test runner.
#
# Usage:
#   ./scripts/setup-dev-env.sh
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"

if [[ ! -x "$VENV_DIR/bin/python" && ! -x "$VENV_DIR/Scripts/python.exe" ]]; then
  echo "==> Creating virtualenv at $VENV_DIR"
  "$PYTHON" -m venv "$VENV_DIR"
fi

if [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
  VENV_PY="$VENV_DIR/Scripts/python.exe"
else
  VENV_PY="$VENV_DIR/bin/python"
fi

echo "==> Installing pykaraoke-ng[dev]"
"$VENV_PY" -m pip install -e "$ROOT_DIR[dev]" || "$VENV_PY" -m pip install -e "$ROOT_DIR"

echo "==> Building web assets"
"$VENV_PY" "$ROOT_DIR/scripts/build-web.py"

echo "==> Installing frontend test runner"
(cd "$ROOT_DIR/tests/web" && npm install)

echo "Setup complete. Run ./scripts/run-tests.sh"