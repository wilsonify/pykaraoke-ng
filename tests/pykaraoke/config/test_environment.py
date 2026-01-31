"""Unit tests for environment detection module."""

import os

import pytest


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
    """Test platform-specific detection logic."""

    @pytest.mark.skipif(os.name != "posix", reason="POSIX-only test")
    def test_posix_detection(self):
        """On POSIX systems, should detect correctly."""
        from pykaraoke.config.constants import ENV_OSX, ENV_POSIX
        from pykaraoke.config.environment import env

        # GP2X is a specific embedded Linux device, unlikely on modern systems
        assert env in {ENV_POSIX, ENV_OSX}, "POSIX system should be POSIX or OSX"

    @pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
    def test_windows_detection(self):
        """On Windows systems, should detect ENV_WINDOWS."""
        from pykaraoke.config.constants import ENV_WINDOWS
        from pykaraoke.config.environment import env

        assert env == ENV_WINDOWS, "Windows system should be ENV_WINDOWS"

    @pytest.mark.skipif(
        not (os.name == "posix" and os.uname().sysname.lower().startswith("darwin")),
        reason="macOS-only test",
    )
    def test_osx_detection(self):
        """On macOS systems, should detect ENV_OSX."""
        from pykaraoke.config.constants import ENV_OSX
        from pykaraoke.config.environment import env

        assert env == ENV_OSX, "macOS system should be ENV_OSX"

    @pytest.mark.skipif(
        not (os.name == "posix" and os.uname().sysname.lower() == "linux"),
        reason="Linux-only test",
    )
    def test_linux_detection(self):
        """On Linux systems (non-GP2X), should detect ENV_POSIX."""
        from pykaraoke.config.constants import ENV_POSIX
        from pykaraoke.config.environment import env

        # Unless running on actual GP2X hardware
        if os.uname().nodename != "gp2x":
            assert env == ENV_POSIX, "Linux system should be ENV_POSIX"
