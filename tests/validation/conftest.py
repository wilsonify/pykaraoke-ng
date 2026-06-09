"""Shared fixtures for artifact validation tests."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


def _find_backend_exe():
    """Locate the built backend.exe artifact."""
    env_override = os.environ.get("PYKARAOKE_BACKEND_EXE")
    if env_override:
        p = Path(env_override)
        if p.is_file():
            return p

    repo_root = Path(__file__).resolve().parents[2]
    candidates = [
        repo_root / "src" / "runtimes" / "tauri" / "src-tauri" / "backend" / "backend.exe",
        repo_root / "dist" / "backend" / "backend.exe",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _find_setup_exe():
    """Locate the built NSIS installer artifact."""
    repo_root = Path(__file__).resolve().parents[2]
    candidates = list(repo_root.glob("dist/**/*setup.exe")) + list(repo_root.glob("dist/**/*.exe"))
    for c in candidates:
        if c.is_file() and "setup" in c.name.lower():
            return c
    return None


@pytest.fixture(scope="session")
def backend_exe():
    """Return path to built backend.exe."""
    exe = _find_backend_exe()
    if exe is None:
        pytest.skip("backend.exe not found — build the backend artifact first")
    return exe


@pytest.fixture(scope="session")
def setup_exe():
    """Return path to NSIS installer."""
    exe = _find_setup_exe()
    if exe is None:
        pytest.skip("NSIS setup.exe not found — run 'tauri build --bundles nsis' first")
    return exe


@pytest.fixture(scope="function")
def backend_process(backend_exe):
    """Launch backend.exe as a subprocess with pipe redirection.

    The stdio protocol interleaves events (``{"type":"event",...}``)
    and responses (``{"type":"response",...}``) on stdout.  This
    fixture's ``send()`` method skips event lines and returns only
    the actual command response.
    """
    proc = subprocess.Popen(
        [str(backend_exe)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    time.sleep(1.5)

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
