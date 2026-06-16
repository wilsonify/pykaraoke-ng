"""Unit tests for environment detection module."""

import importlib
import os
from unittest import mock

import pytest


def _detect_env():
    """Re-import the environment module to trigger detection logic.

    Used by tests that mock os.name / os.uname so every code path
    in environment.py can be exercised on any host OS.
    """
    import pykaraoke.config.environment
    importlib.reload(pykaraoke.config.environment)
    return pykaraoke.config.environment.env


class TestEnvironmentDetection:
    """Test environment detection functionality."""

    def test_env_is_defined(self):
        """The env variable should be defined after import."""
        from pykaraoke.config.environment import env

        assert env is not None

    def test_env_is_known_constant(self):
        """The env should be one of the known environment constants."""
        from pykaraoke.config.constants import ENV_GP2X, ENV_OSX, ENV_POSIX, ENV_UNKNOWN, ENV_WINDOWS
        from pykaraoke.config.environment import env

        known_envs = {ENV_WINDOWS, ENV_POSIX, ENV_OSX, ENV_GP2X, ENV_UNKNOWN}
        assert env in known_envs, f"env={env} is not a known environment constant"

    def test_env_matches_os_name(self):
        """The env should match the current OS name."""
        from pykaraoke.config.constants import ENV_OSX, ENV_POSIX, ENV_WINDOWS
        from pykaraoke.config.environment import env

        if os.name == "nt":
            assert env == ENV_WINDOWS, "On Windows, env should be ENV_WINDOWS"
        elif os.name == "posix":
            # Could be POSIX, OSX, or GP2X
            assert env in {ENV_POSIX, ENV_OSX}, (
                f"On POSIX, env should be ENV_POSIX or ENV_OSX, got {env}"
            )

    def test_env_is_integer(self):
        """The env should be an integer constant."""
        from pykaraoke.config.environment import env

        assert isinstance(env, int), f"env should be int, got {type(env)}"


class TestPlatformSpecificDetection:
    """Test platform-specific detection logic with mocked OS interfaces."""

    def test_windows_detection(self):
        """When os.name == 'nt', should detect ENV_WINDOWS."""
        from pykaraoke.config.constants import ENV_WINDOWS

        with mock.patch.object(os, "name", "nt"):
            env = _detect_env()
            assert env == ENV_WINDOWS, "On Windows, env should be ENV_WINDOWS"

    def test_posix_detection(self):
        """On generic POSIX (Linux, BSD, etc.), should detect ENV_POSIX."""
        from pykaraoke.config.constants import ENV_POSIX

        with (
            mock.patch.object(os, "name", "posix"),
            mock.patch.object(os, "uname", create=True, return_value=("Linux", "buildbox", "6.1", "1", "x86_64")),
        ):
            env = _detect_env()
            assert env == ENV_POSIX, "Generic POSIX system should be ENV_POSIX"

    def test_osx_detection(self):
        """On macOS (darwin), should detect ENV_OSX."""
        from pykaraoke.config.constants import ENV_OSX

        with (
            mock.patch.object(os, "name", "posix"),
            mock.patch.object(os, "uname", create=True, return_value=("Darwin", "macmini", "24.0", "1", "arm64")),
        ):
            env = _detect_env()
            assert env == ENV_OSX, "macOS system should be ENV_OSX"

    def test_gp2x_detection(self):
        """On GP2X hardware, should detect ENV_GP2X."""
        from pykaraoke.config.constants import ENV_GP2X

        with (
            mock.patch.object(os, "name", "posix"),
            mock.patch.object(os, "uname", create=True, return_value=("Linux", "gp2x", "2.6", "1", "armv5tel")),
        ):
            env = _detect_env()
            assert env == ENV_GP2X, "GP2X host should be ENV_GP2X"

    def test_unknown_os_detection(self):
        """On an unrecognised OS, should detect ENV_UNKNOWN."""
        from pykaraoke.config.constants import ENV_UNKNOWN

        with mock.patch.object(os, "name", "cbm"):
            env = _detect_env()
            assert env == ENV_UNKNOWN, "Unknown OS should be ENV_UNKNOWN"
