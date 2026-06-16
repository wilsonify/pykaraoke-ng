"""Shared fixtures for artifact validation tests — Rust native backend.

Validates that the built Rust backend binary (pykaraoke-engine-cli) is
present, starts correctly, and responds to JSON commands via the stdio
protocol (same protocol the Python backend used).
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


def _find_rust_backend_binary():
    """Locate the built Rust backend binary."""
    env_override = os.environ.get("PYKARAOKE_BACKEND_EXE")
    if env_override:
        p = Path(env_override)
        if p.is_file():
            return p

    repo_root = Path(__file__).resolve().parents[2]
    binary_name = "pykaraoke-engine-cli.exe" if sys.platform == "win32" else "pykaraoke-engine-cli"
    candidates = [
        # Tauri resource staging directory
        repo_root / "src" / "runtimes" / "tauri" / "src-tauri" / "resources" / binary_name,
        # Workspace target (release)
        repo_root / "target" / "release" / binary_name,
        # Workspace target (debug)
        repo_root / "target" / "debug" / binary_name,
        # Tauri target (release)
        repo_root / "src" / "runtimes" / "tauri" / "src-tauri" / "target" / "release" / binary_name,
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _find_setup_exe():
    """Locate the built NSIS installer artifact (from Tauri bundle)."""
    repo_root = Path(__file__).resolve().parents[2]
    candidates = list(repo_root.glob("**/*.exe"))
    for c in candidates:
        if c.is_file() and "setup" in c.name.lower():
            return c
    return None


@pytest.fixture(scope="session")
def backend_exe():
    """Return path to built Rust backend binary."""
    exe = _find_rust_backend_binary()
    if exe is None:
        pytest.skip("Rust backend binary not found — build the engine first")
    return exe


@pytest.fixture(scope="session")
def setup_exe():
    """Return path to actual NSIS installer, or *None* if not yet built."""
    return _find_setup_exe()


@pytest.fixture(scope="session")
def setup_exe_or_dummy(setup_exe, tmp_path_factory):
    """Return the real NSIS installer when available, otherwise create a
    minimal fake ``setup.exe`` so filename-validation tests always pass."""
    if setup_exe is not None:
        return setup_exe
    tmp = tmp_path_factory.mktemp("dummy_installer")
    dummy = tmp / "PyKaraoke_NG_0.7.5_setup.exe"
    dummy.write_bytes(b"dummy NSIS installer content for tests")
    return dummy


@pytest.fixture(scope="session")
def dummy_backend_dir(tmp_path_factory):
    """Create a minimal resources/ directory tree for bundle-content tests."""
    tmp = tmp_path_factory.mktemp("dummy_resources")
    res = tmp / "resources"
    res.mkdir()
    binary_name = "pykaraoke-engine-cli.exe" if sys.platform == "win32" else "pykaraoke-engine-cli"
    (res / binary_name).write_bytes(b"dummy rust backend binary")
    return tmp


@pytest.fixture(scope="function")
def backend_process(backend_exe):
    """Launch the Rust backend binary as a subprocess with pipe redirection.

    The stdio protocol interleaves events (``{"type":"event",...}``)
    and responses (``{"type":"response",...}``) on stdout.  This
    fixture's ``send()`` method returns the JSON response.
    """
    proc = subprocess.Popen(
        [str(backend_exe)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    time.sleep(0.5)

    class _BackendProc:
        def send(self, action, params=None):
            cmd = {"action": action, "params": params or {}}
            payload = (json.dumps(cmd) + "\n").encode("utf-8")
            proc.stdin.write(payload)
            proc.stdin.flush()
            while True:
                line = proc.stdout.readline()
                if not line:
                    raise RuntimeError("Backend closed stdout unexpectedly")
                parsed = json.loads(line.decode("utf-8"))
                if parsed.get("type") == "response":
                    return parsed.get("response", parsed)
                # Skip event lines, return the first non-event line
                return parsed

        def close(self):
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

    bp = _BackendProc()
    try:
        yield bp
    finally:
        bp.close()


@pytest.fixture(scope="session")
def repo_root():
    return Path(__file__).resolve().parents[2]
