"""Unit tests for pykconstants module."""

import pytest


class TestEnvironmentConstants:
    """Test environment type constants."""

    def test_environment_constants_are_unique(self):
        """Environment constants should have unique values."""
        from pykconstants import ENV_WINDOWS, ENV_POSIX, ENV_OSX, ENV_GP2X, ENV_UNKNOWN

        env_values = [ENV_WINDOWS, ENV_POSIX, ENV_OSX, ENV_GP2X, ENV_UNKNOWN]
        assert len(env_values) == len(set(env_values)), "Environment constants must be unique"

    def test_environment_constants_are_integers(self):
        """Environment constants should be integers."""
        from pykconstants import ENV_WINDOWS, ENV_POSIX, ENV_OSX, ENV_GP2X, ENV_UNKNOWN

        for const in [ENV_WINDOWS, ENV_POSIX, ENV_OSX, ENV_GP2X, ENV_UNKNOWN]:
            assert isinstance(const, int), f"Expected int, got {type(const)}"


class TestStateConstants:
    """Test player state constants."""

    def test_state_constants_are_unique(self):
        """State constants should have unique values."""
        from pykconstants import (
            STATE_INIT,
            STATE_PLAYING,
            STATE_PAUSED,
            STATE_NOT_PLAYING,
            STATE_CLOSING,
            STATE_CLOSED,
            STATE_CAPTURING,
        )

        state_values = [
            STATE_INIT,
            STATE_PLAYING,
            STATE_PAUSED,
            STATE_NOT_PLAYING,
            STATE_CLOSING,
            STATE_CLOSED,
            STATE_CAPTURING,
        ]
        assert len(state_values) == len(set(state_values)), "State constants must be unique"

    def test_state_constants_are_integers(self):
        """State constants should be integers."""
        from pykconstants import (
            STATE_INIT,
            STATE_PLAYING,
            STATE_PAUSED,
            STATE_NOT_PLAYING,
            STATE_CLOSING,
            STATE_CLOSED,
            STATE_CAPTURING,
        )

        for const in [
            STATE_INIT,
            STATE_PLAYING,
            STATE_PAUSED,
            STATE_NOT_PLAYING,
            STATE_CLOSING,
            STATE_CLOSED,
            STATE_CAPTURING,
        ]:
            assert isinstance(const, int), f"Expected int, got {type(const)}"

    def test_init_state_is_zero(self):
        """STATE_INIT should be 0 for easy boolean checks."""
        from pykconstants import STATE_INIT

        assert STATE_INIT == 0


class TestGP2XButtonConstants:
    """Test GP2X joystick button mapping constants."""

    def test_gp2x_button_constants_defined(self):
        """All GP2X button constants should be defined."""
        from pykconstants import (
            GP2X_BUTTON_UP,
            GP2X_BUTTON_DOWN,
            GP2X_BUTTON_LEFT,
            GP2X_BUTTON_RIGHT,
            GP2X_BUTTON_UPLEFT,
            GP2X_BUTTON_UPRIGHT,
            GP2X_BUTTON_DOWNLEFT,
            GP2X_BUTTON_DOWNRIGHT,
            GP2X_BUTTON_CLICK,
            GP2X_BUTTON_A,
            GP2X_BUTTON_B,
            GP2X_BUTTON_X,
            GP2X_BUTTON_Y,
            GP2X_BUTTON_L,
            GP2X_BUTTON_R,
            GP2X_BUTTON_START,
            GP2X_BUTTON_SELECT,
            GP2X_BUTTON_VOLUP,
            GP2X_BUTTON_VOLDOWN,
        )

        # Just verify they're all integers
        buttons = [
            GP2X_BUTTON_UP,
            GP2X_BUTTON_DOWN,
            GP2X_BUTTON_LEFT,
            GP2X_BUTTON_RIGHT,
            GP2X_BUTTON_UPLEFT,
            GP2X_BUTTON_UPRIGHT,
            GP2X_BUTTON_DOWNLEFT,
            GP2X_BUTTON_DOWNRIGHT,
            GP2X_BUTTON_CLICK,
            GP2X_BUTTON_A,
            GP2X_BUTTON_B,
            GP2X_BUTTON_X,
            GP2X_BUTTON_Y,
            GP2X_BUTTON_L,
            GP2X_BUTTON_R,
            GP2X_BUTTON_START,
            GP2X_BUTTON_SELECT,
            GP2X_BUTTON_VOLUP,
            GP2X_BUTTON_VOLDOWN,
        ]
        for button in buttons:
            assert isinstance(button, int), f"Button mapping should be int, got {type(button)}"


class TestBorderConstants:
    """Test display border constants."""

    def test_border_constants_positive(self):
        """Border constants should be positive integers."""
        from pykconstants import X_BORDER, Y_BORDER

        assert X_BORDER > 0, "X_BORDER should be positive"
        assert Y_BORDER > 0, "Y_BORDER should be positive"

    def test_border_constants_reasonable_values(self):
        """Border constants should have reasonable values for a display."""
        from pykconstants import X_BORDER, Y_BORDER

        assert X_BORDER < 100, "X_BORDER should be reasonable (< 100)"
        assert Y_BORDER < 100, "Y_BORDER should be reasonable (< 100)"
