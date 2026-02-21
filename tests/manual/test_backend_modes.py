#!/usr/bin/env python
"""
Simple integration test for backend modes.
Tests that the mode selection and server startup logic works correctly.
"""

import subprocess
import sys
import time
from pathlib import Path


# Calculate path to src directory relative to this test file
TEST_DIR = Path(__file__).parent
REPO_ROOT = TEST_DIR.parent.parent
SRC_DIR = REPO_ROOT / "src"


def test_stdio_help():
    """Test that stdio mode shows help correctly"""
    result = subprocess.run(
        [sys.executable, "-m", "pykaraoke.core.backend", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
        env={"PYTHONPATH": str(SRC_DIR)},
    )
    assert "--stdio" in result.stdout
    assert "--http" in result.stdout
    assert "BACKEND_MODE" in result.stdout
    print("✓ Help output looks good")


def test_http_mode_startup():
    """Test that HTTP mode can start (will fail due to missing deps but mode selection works)"""
    proc = subprocess.Popen(
        [sys.executable, "-m", "pykaraoke.core.backend", "--http", "--port", "18080"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={"PYTHONPATH": str(SRC_DIR)},
    )
    
    # Wait a moment and check output
    time.sleep(2)
    proc.terminate()
    stdout, stderr = proc.communicate(timeout=3)
    
    # Check that it tried to start in HTTP mode
    combined = stdout + stderr
    assert "http mode" in combined.lower() or "HTTP" in combined
    print("✓ HTTP mode startup initiated")


def test_stdio_mode_startup():
    """Test that stdio mode can start (will fail due to missing deps but mode selection works)"""
    proc = subprocess.Popen(
        [sys.executable, "-m", "pykaraoke.core.backend", "--stdio"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={"PYTHONPATH": str(SRC_DIR)},
    )
    
    # Wait a moment and check output
    time.sleep(2)
    proc.terminate()
    stdout, stderr = proc.communicate(timeout=3)
    
    # Check that it tried to start in stdio mode
    combined = stdout + stderr
    assert "stdio mode" in combined.lower() or "stdio" in combined
    print("✓ stdio mode startup initiated")


if __name__ == "__main__":
    print("Testing backend mode selection...")
    test_stdio_help()
    test_http_mode_startup()
    test_stdio_mode_startup()
    print("\n✅ All mode selection tests passed!")
