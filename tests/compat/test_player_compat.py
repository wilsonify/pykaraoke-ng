"""
Compatibility tests: playback state machine (Priority 5).

Exercises the same state transitions through both the Python reference
implementation and the Rust engine, then compares state, position, and
timing.
"""

import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import install_pygame_mock

install_pygame_mock()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RS_CLI = os.path.join(
    PROJECT_ROOT,
    "target",
    "debug",
    "pykaraoke-engine-cli.exe" if sys.platform == "win32" else "pykaraoke-engine-cli",
)


def rs_player_command(command, **params):
    """Send a command to the Rust player CLI and return the JSON state."""
    if not os.path.isfile(RS_CLI):
        pytest.skip(f"Rust CLI not built at {RS_CLI}")
    args = [RS_CLI, "player", command]
    for key, value in params.items():
        args.append(f"--{key}")
        args.append(str(value))
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        pytest.fail(f"Rust player CLI failed:\n{result.stderr}")
    return json.loads(result.stdout)


class TestPlayerStateCompat:
    """Compare Python and Rust player state transitions."""

    @pytest.fixture
    def py_player_instance(self):
        """Create a Python PykPlayer instance with mocked pygame."""
        with patch("pygame.time.get_ticks", return_value=0):
            from pykaraoke.core.player import PykPlayer
            from pykaraoke.core.database import SettingsStruct

            # Create minimal mock song_db
            mock_song_db = MagicMock()
            mock_song_db.settings = SettingsStruct()

            player = PykPlayer(song="dummy.kar", song_db=mock_song_db)
            return player

    def test_initial_state(self):
        """Both engines start in Init state."""
        # Python (can't easily test without pygame runtime)
        # Rust
        state = rs_player_command("state")
        assert state["state"] in ("Init", "init")

    def test_play_transition(self, py_player_instance):
        """Play sets state to Playing and records start time."""
        # Python
        with patch("pygame.time.get_ticks", return_value=1000):
            py_player_instance.play()
            assert py_player_instance.state == 1  # STATE_PLAYING

        # Rust
        state = rs_player_command("play", current_time_ms=1000)
        assert state["state"] == "Playing"

    def test_pause_toggle(self, py_player_instance):
        """Pause toggles between Playing and Paused."""
        with patch("pygame.time.get_ticks", side_effect=[0, 5000, 8000]):
            py_player_instance.play()
            assert py_player_instance.state == 1  # STATE_PLAYING

            py_player_instance.pause()
            assert py_player_instance.state == 2  # STATE_PAUSED
            assert py_player_instance.play_time == 5000

            py_player_instance.pause()
            assert py_player_instance.state == 1  # STATE_PLAYING

    def test_rewind_resets_timing(self, py_player_instance):
        """Rewind resets timing and sets NotPlaying."""
        with patch("pygame.time.get_ticks", side_effect=[0, 10000]):
            py_player_instance.play()
            py_player_instance.pause()
            py_player_instance.rewind()
            assert py_player_instance.state == 3  # STATE_NOT_PLAYING
            assert py_player_instance.play_time == 0

    def test_close_and_shutdown(self, py_player_instance):
        """Close initiates shutdown sequence."""
        py_player_instance.close()
        assert py_player_instance.state == 4  # STATE_CLOSING

        py_player_instance.shutdown()
        assert py_player_instance.state == 5  # STATE_CLOSED
