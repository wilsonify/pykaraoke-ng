"""
Pytest configuration and shared fixtures for compatibility tests.

Provides:
  - ``py_filename_parser`` fixture (Python reference)
  - ``rs_exec`` helper to call the Rust engine CLI
"""

import json
import os
import subprocess
import sys

import pytest

# ── Paths ───────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Built Rust binary (dev profile)
RS_ENGINE_CLI = os.path.join(
    PROJECT_ROOT,
    "target",
    "debug",
    "pykaraoke-engine-cli.exe" if sys.platform == "win32" else "pykaraoke-engine-cli",
)


# ── Helpers ─────────────────────────────────────────────────────────


def rs_exec(command: str, **kwargs) -> dict:
    """Run the Rust engine CLI with *command* and keyword arguments.

    Returns the parsed JSON response dict.
    """
    if not os.path.isfile(RS_ENGINE_CLI):
        pytest.skip(f"Rust CLI not built at {RS_ENGINE_CLI}")
    args = [RS_ENGINE_CLI, command]
    for key, value in kwargs.items():
        args.append(f"--{key}")
        args.append(str(value))
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        pytest.fail(f"Rust CLI failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")
    return json.loads(result.stdout)


# ── Python reference fixtures ───────────────────────────────────────


@pytest.fixture(scope="session")
def py_filename_parser():
    """Return the Python reference ``FilenameParser`` class."""
    from pykaraoke.core.filename_parser import FilenameParser as _cls
    return _cls


@pytest.fixture(scope="session")
def py_parsed_song():
    """Return the Python reference ``ParsedSong`` class."""
    from pykaraoke.core.filename_parser import ParsedSong as _cls
    return _cls


@pytest.fixture(scope="session")
def py_file_name_type():
    """Return the Python reference ``FileNameType`` enum."""
    from pykaraoke.core.filename_parser import FileNameType as _enum
    return _enum


@pytest.fixture(scope="session")
def py_player():
    """Return the Python reference ``PykPlayer`` class."""
    from pykaraoke.core.player import PykPlayer as _cls
    return _cls


@pytest.fixture(scope="session")
def py_backend():
    """Return the Python reference ``PyKaraokeBackend`` class."""
    from pykaraoke.core.backend import PyKaraokeBackend as _cls, BackendState as _st
    return _cls, _st
