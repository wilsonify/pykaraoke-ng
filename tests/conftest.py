"""Shared test fixtures."""

import os
import sys

# Ensure the project root and src/ are importable regardless of how pytest
# is invoked.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_PROJECT_ROOT, "src")
for _p in (_PROJECT_ROOT, _SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

FIXTURES_DIR = os.path.join(_PROJECT_ROOT, "tests", "fixtures")
