#!/usr/bin/env bash
#
# Setup development environment using uv (modern Python package manager)
#
# Usage:
#   ./scripts/setup-dev-env.sh           # Standard setup
#   ./scripts/setup-dev-env.sh --full    # Include GUI dependencies
#   ./scripts/setup-dev-env.sh --ci      # CI mode (no GUI deps)
#   ./scripts/setup-dev-env.sh --legacy  # Use pip/venv (fallback)
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"

# Parse arguments
FULL_INSTALL=0
CI_MODE=0
LEGACY_MODE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --full)
            FULL_INSTALL=1
            shift
            ;;
        --ci)
            CI_MODE=1
            shift
            ;;
        --legacy)
            LEGACY_MODE=1
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --full    Install all dependencies including GUI (wxPython)"
            echo "  --ci      CI mode - minimal dependencies for testing"
            echo "  --legacy  Use pip/venv instead of uv (fallback mode)"
            echo "  -h,--help Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}" >&2
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  PyKaraoke-NG Development Setup       ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Legacy mode using pip/venv
if [[ $LEGACY_MODE -eq 1 ]]; then
    echo -e "${YELLOW}Using legacy pip/venv setup...${NC}"
    
    PYTHON_BIN="${PYTHON_BIN:-python3}"
    
    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
        echo -e "${RED}Error: $PYTHON_BIN not found.${NC}" >&2
        exit 1
    fi
    
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"
    
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install -e ".[dev,test]"
    
    if [[ $FULL_INSTALL -eq 1 ]]; then
        python -m pip install -e ".[gui]" || echo -e "${YELLOW}GUI deps failed${NC}"
    fi
    
    echo -e "${GREEN}Legacy setup complete. Activate with: source $VENV_DIR/bin/activate${NC}"
    exit 0
fi

# Modern uv-based setup
if ! command -v uv >/dev/null 2>&1; then
    echo -e "${YELLOW}uv not found. Installing uv...${NC}"
    
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo -e "${RED}Error: curl or wget required to install uv${NC}" >&2
        echo "Falling back to legacy mode..."
        exec "$0" --legacy "$@"
    fi
    
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    
    if ! command -v uv >/dev/null 2>&1; then
        echo -e "${YELLOW}uv install may require shell restart. Falling back to legacy mode...${NC}"
        exec "$0" --legacy "$@"
    fi
    
    echo -e "${GREEN}✓ uv installed successfully${NC}"
fi

echo -e "${BLUE}Using uv version:${NC} $(uv --version)"
echo ""

# Sync the project with uv
echo -e "${BLUE}Creating virtual environment and installing dependencies...${NC}"

if [[ $CI_MODE -eq 1 ]]; then
    echo -e "${YELLOW}CI mode: Installing test dependencies only${NC}"
    uv sync --extra test
elif [[ $FULL_INSTALL -eq 1 ]]; then
    echo -e "${YELLOW}Full install: Including all dependencies${NC}"
    uv sync --all-extras
else
    echo -e "${YELLOW}Standard install: dev + test dependencies${NC}"
    uv sync --extra dev --extra test
fi

echo ""
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Install pre-commit hooks if not in CI
if [[ $CI_MODE -eq 0 ]] && [[ -f ".pre-commit-config.yaml" ]]; then
    echo -e "${BLUE}Installing pre-commit hooks...${NC}"
    uv run pre-commit install 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "To activate the virtual environment:"
echo -e "  ${BLUE}source .venv/bin/activate${NC}"
echo ""
echo "Or use uv to run commands directly:"
echo -e "  ${BLUE}uv run pytest${NC}"
echo -e "  ${BLUE}uv run python -m pykaraoke${NC}"
echo ""

