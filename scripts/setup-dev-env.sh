#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN not found. Set PYTHON_BIN to a valid Python executable." >&2
  exit 1
fi

"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel

# Core optional runtime dependency used by the app for metadata handling
python -m pip install mutagen

# Test dependencies
python -m pip install pytest selenium

if [[ "${INSTALL_GUI_DEPS:-0}" == "1" ]]; then
  echo "Installing GUI deps (pygame, wxPython). This may take a while and can require system packages..."
  python -m pip install pygame wxPython || {
    echo "Warning: GUI deps failed to install. See README for system prerequisites." >&2
  }
else
  echo "Skipping GUI deps. Set INSTALL_GUI_DEPS=1 to install pygame and wxPython." >&2
fi

echo "Dev environment setup complete. Activate with: source $VENV_DIR/bin/activate"
