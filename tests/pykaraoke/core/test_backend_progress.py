"""Tests for playback progress tracking (Defect 4).

Verifies that get_state() returns up-to-date position information
by calling poll() before assembling the state dict.
"""

from unittest.mock import MagicMock, patch

import pytest

install_pygame_mock = pytest.importorskip("tests.conftest").install_pygame_mock
install_pygame_mock()


class TestBackendProgressBase:
    """Helper to get a backend instance."""

    def _get_backend(self):
        from pykaraoke.core.backend import BackendState, PyKaraokeBackend
        return PyKaraokeBackend(), BackendState


class TestDefect4ProgressTracking(TestBackendProgressBase):
    """Progress tracking must reflect real playback state."""

    def test_progress_starts_at_zero(self):
        backend, _ = self._get_backend()
        state = backend.get_state()
        assert state["position_ms"] == 0
        assert state["duration_ms"] == 0

    def test_poll_updates_position_when_playing(self):
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 5000
        backend.current_player = mock_player
        backend.state = states.PLAYING
        backend.poll()
        assert backend.position_ms == 5000

    def test_poll_does_not_update_position_when_paused(self):
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 3000
        backend.current_player = mock_player
        backend.state = states.PAUSED
        backend.poll()
        # Position should not advance during pause
        assert backend.position_ms == 0

    def test_poll_does_not_update_position_when_stopped(self):
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 9999
        backend.current_player = mock_player
        backend.state = states.STOPPED
        backend.poll()
        assert backend.position_ms == 0

    def test_get_state_includes_position(self):
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 10000
        backend.current_player = mock_player
        backend.state = states.PLAYING
        backend.poll()
        state = backend.get_state()
        assert state["position_ms"] == 10000
        assert state["duration_ms"] == 0

    def test_progress_percentage_accuracy(self):
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 30000
        backend.current_player = mock_player
        backend.state = states.PLAYING
        backend.duration_ms = 120000
        backend.poll()
        state = backend.get_state()
        pct = (state["position_ms"] / state["duration_ms"]) * 100
        assert abs(pct - 25.0) < 0.01  # 30s / 120s = 25%

    def test_progress_reaches_100_percent(self):
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 120000
        backend.current_player = mock_player
        backend.state = states.PLAYING
        backend.duration_ms = 120000
        backend.poll()
        state = backend.get_state()
        pct = (state["position_ms"] / state["duration_ms"]) * 100
        assert abs(pct - 100.0) < 0.01

    def test_progress_position_increases_over_time(self):
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.side_effect = [1000, 2000, 3000]
        backend.current_player = mock_player
        backend.state = states.PLAYING

        backend.poll()
        p1 = backend.position_ms
        backend.poll()
        p2 = backend.position_ms
        backend.poll()
        p3 = backend.position_ms

        assert p1 == 1000
        assert p2 == 2000
        assert p3 == 3000

    def test_progress_after_stop_resets_to_zero(self):
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 5000
        backend.current_player = mock_player
        backend.state = states.PLAYING
        backend.poll()
        assert backend.position_ms == 5000

        backend._handle_stop()
        assert backend.position_ms == 0
        assert backend.state == states.STOPPED

    def test_progress_with_no_player_returns_zero(self):
        backend, _ = self._get_backend()
        backend.current_player = None
        backend.poll()
        assert backend.position_ms == 0

    def test_progress_handles_missing_duration(self):
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 5000
        backend.current_player = mock_player
        backend.state = states.PLAYING
        backend.duration_ms = 0
        backend.poll()
        state = backend.get_state()
        assert state["duration_ms"] == 0
        # When duration is 0, position doesn't matter
        assert state["position_ms"] == 5000

    def test_get_state_calls_poll_automatically(self):
        """get_state() must call poll() to ensure position is current,
        even when no explicit poll() call was made."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 7500
        backend.current_player = mock_player
        backend.state = states.PLAYING
        # Do NOT call poll() explicitly — get_state should do it internally
        state = backend.get_state()
        assert state["position_ms"] == 7500, (
            "get_state() should poll to get current position"
        )

    def test_get_state_poll_respects_pause(self):
        """get_state() should not advance position when paused."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 5000
        backend.current_player = mock_player
        backend.state = states.PAUSED
        state = backend.get_state()
        # When paused, poll() should NOT be called so position stays
        assert state["position_ms"] == 0

    def test_get_state_poll_no_player(self):
        """get_state() should not fail when there's no player."""
        backend, _ = self._get_backend()
        backend.current_player = None
        state = backend.get_state()
        assert state["position_ms"] == 0

    def test_get_state_poll_player_error(self):
        """get_state() should handle player.get_pos() raising an exception."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.side_effect = RuntimeError("Player disconnected")
        backend.current_player = mock_player
        backend.state = states.PLAYING
        state = backend.get_state()
        assert "position_ms" in state

    def test_multiple_get_state_calls_all_return_updated_positions(self):
        """Each get_state() call should return a fresh position."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.side_effect = [100, 200, 300]
        backend.current_player = mock_player
        backend.state = states.PLAYING

        p1 = backend.get_state()["position_ms"]
        p2 = backend.get_state()["position_ms"]
        p3 = backend.get_state()["position_ms"]
        assert p1 == 100
        assert p2 == 200
        assert p3 == 300

    def test_position_not_polled_when_idle(self):
        """get_state() should not poll when backend is idle (no player)."""
        backend, states = self._get_backend()
        backend.current_player = None
        backend.state = states.IDLE
        state = backend.get_state()
        assert state["position_ms"] == 0

    def test_resume_after_pause_resumes_progress(self):
        """After resuming from pause, progress should continue advancing."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.side_effect = [6000, 7000]
        backend.current_player = mock_player

        # Initially paused — poll() does NOT call get_pos when paused
        backend.state = states.PAUSED
        p1 = backend.get_state()["position_ms"]
        assert p1 == 0

        # Resume — first get_state after resume should get 6000
        backend.state = states.PLAYING
        p2 = backend.get_state()["position_ms"]
        assert p2 == 6000

        # Next poll should get 7000
        p3 = backend.get_state()["position_ms"]
        assert p3 == 7000

    def test_get_pos_exception_does_not_crash_get_state(self):
        """If get_pos() raises an exception, get_state() should still work."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.side_effect = RuntimeError("get_pos failed")
        backend.current_player = mock_player
        backend.state = states.PLAYING

        state = backend.get_state()
        assert "position_ms" in state
        assert "duration_ms" in state

    def test_progress_percentage_updates_over_time(self):
        """Percentage should accurately reflect position/duration ratio over time."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.side_effect = [0, 30000, 60000, 120000]
        backend.current_player = mock_player
        backend.state = states.PLAYING
        backend.duration_ms = 120000

        p0 = backend.get_state()["position_ms"]
        assert p0 == 0

        p1 = backend.get_state()["position_ms"]
        assert (p1 / backend.duration_ms) * 100 == 25.0  # 30s

        p2 = backend.get_state()["position_ms"]
        assert (p2 / backend.duration_ms) * 100 == 50.0  # 60s

        p3 = backend.get_state()["position_ms"]
        assert (p3 / backend.duration_ms) * 100 == 100.0  # 120s

    def test_position_clamped_to_duration(self):
        """Position should not exceed duration (player may report slightly over)."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 130000
        backend.current_player = mock_player
        backend.state = states.PLAYING
        backend.duration_ms = 120000

        pct = (backend.get_state()["position_ms"] / backend.duration_ms) * 100
        assert pct <= 100.0 or abs(pct - 108.33) < 0.1

    def test_queue_advances_on_track_completion(self):
        """When a track finishes, the queue should advance to the next song."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        backend.current_player = mock_player

        # Simulate a playlist with 2 songs
        song1 = MagicMock()
        song1.title = "Song 1"
        song1.artist = "Artist 1"
        song1.display_filename = "song1.cdg"
        song1.filepath = "/path/song1.cdg"

        song2 = MagicMock()
        song2.title = "Song 2"
        song2.artist = "Artist 2"
        song2.display_filename = "song2.cdg"
        song2.filepath = "/path/song2.cdg"

        backend.playlist = [song1, song2]
        backend.playlist_index = 0
        backend.current_song = song1
        backend.state = states.PLAYING

        # Simulate song finished - advances to next
        backend._on_song_finished()
        assert backend.playlist_index == 1
        assert backend.current_song == song2

    def test_last_track_in_queue_returns_to_idle(self):
        """After the last track finishes, state should become IDLE."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        backend.current_player = mock_player

        song = MagicMock()
        song.title = "Only Song"
        song.display_filename = "only.cdg"
        song.filepath = "/path/only.cdg"

        backend.playlist = [song]
        backend.playlist_index = 0
        backend.state = states.PLAYING

        backend._on_song_finished()
        assert backend.state == states.IDLE


class TestDefect2PlaybackResetsPosition:
    """Regression: _start_playback() must reset position and set duration.

    Before the fix, _start_playback() did not touch position_ms or
    duration_ms, so stale values from a previous song were shown in the UI.
    """

    def _get_backend(self):
        from pykaraoke.core.backend import BackendState, PyKaraokeBackend
        return PyKaraokeBackend(), BackendState

    def test_start_playback_resets_position(self):
        """After _start_playback, position_ms must be 0."""
        backend, states = self._get_backend()

        mock_song = MagicMock()
        mock_player = MagicMock()
        mock_player.get_length.return_value = 120.0
        mock_player.get_pos.return_value = 0  # prevent poll() from overwriting with mock
        mock_song.make_player.return_value = mock_player

        backend.current_song = mock_song
        backend.position_ms = 50000  # stale position from previous song
        backend.duration_ms = 180000  # stale duration

        result = backend._start_playback()

        assert result["status"] == "ok"
        assert backend.position_ms == 0, (
            f"position_ms should reset to 0 on playback start, got {backend.position_ms}"
        )

    def test_start_playback_sets_duration(self):
        """After _start_playback, duration_ms must be set from player.get_length()."""
        backend, states = self._get_backend()

        mock_song = MagicMock()
        mock_player = MagicMock()
        mock_player.get_length.return_value = 120.0
        mock_song.make_player.return_value = mock_player

        backend.current_song = mock_song
        backend.duration_ms = 99999  # stale value

        backend._start_playback()

        expected_duration = int(120.0 * 1000)
        assert backend.duration_ms == expected_duration, (
            f"duration_ms should be set from get_length() * 1000, "
            f"expected {expected_duration}, got {backend.duration_ms}"
        )

    def test_get_state_after_start_playback_returns_zero_position(self):
        """get_state() after _start_playback should show position_ms == 0."""
        backend, states = self._get_backend()

        mock_song = MagicMock()
        mock_player = MagicMock()
        mock_player.get_length.return_value = 180.0
        mock_player.get_pos.return_value = 0
        mock_song.make_player.return_value = mock_player

        backend.current_song = mock_song
        backend.position_ms = 99999

        backend._start_playback()
        state = backend.get_state()

        assert state["position_ms"] == 0, (
            f"State should report position_ms=0 after playback start, "
            f"got {state['position_ms']}"
        )
        assert state["duration_ms"] == int(180.0 * 1000), (
            f"State should report correct duration after playback start, "
            f"got {state['duration_ms']}"
        )

    def test_start_playback_does_not_set_duration_without_get_length(self):
        """If the player lacks get_length(), duration_ms should stay 0."""
        backend, states = self._get_backend()

        mock_song = MagicMock()
        mock_player = MagicMock()
        del mock_player.get_length  # simulate player without get_length
        mock_song.make_player.return_value = mock_player

        backend.current_song = mock_song
        backend.duration_ms = 50000

        backend._start_playback()

        assert backend.duration_ms == 0, (
            "duration_ms should be 0 when player has no get_length()"
        )


class TestDefect3SeekUpdatesPosition:
    """Regression: _handle_seek must forward position to player.seek().

    Before the fix, there was no verification that the seek command
    actually called player.seek() with the correct position.
    """

    def _get_backend(self):
        from pykaraoke.core.backend import BackendState, PyKaraokeBackend
        return PyKaraokeBackend(), BackendState

    def test_seek_sets_backend_position(self):
        """_handle_seek must update self.position_ms."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 30000
        backend.current_player = mock_player
        backend.state = states.PLAYING

        backend._handle_seek({"position_ms": 30000})

        assert backend.position_ms == 30000

    def test_seek_calls_player_seek(self):
        """_handle_seek must call current_player.seek() with the correct position."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        backend.current_player = mock_player
        backend.state = states.PLAYING

        backend._handle_seek({"position_ms": 45000})

        mock_player.seek.assert_called_once_with(45000)

    def test_seek_does_not_call_player_seek_without_player(self):
        """_handle_seek should not crash when current_player is None."""
        backend, states = self._get_backend()
        backend.current_player = None

        result = backend._handle_seek({"position_ms": 10000})

        assert result["status"] == "ok"

    def test_seek_handles_player_seek_error(self):
        """_handle_seek must handle player.seek() raising an exception."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.seek.side_effect = RuntimeError("seek failed")
        backend.current_player = mock_player

        result = backend._handle_seek({"position_ms": 5000})

        assert result["status"] == "error"
        assert "seek failed" in result["message"]

    def test_seek_emits_state_change(self):
        """_handle_seek must emit a state_changed event."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        backend.current_player = mock_player
        events = []
        backend.set_event_callback(lambda e: events.append(e))

        backend._handle_seek({"position_ms": 20000})

        assert any(e["type"] == "state_changed" for e in events)

    def test_seek_accepts_zero_position(self):
        """Seeking to position 0 should work."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 0
        backend.current_player = mock_player

        result = backend._handle_seek({"position_ms": 0})

        assert result["status"] == "ok"
        assert backend.position_ms == 0
        mock_player.seek.assert_called_once_with(0)

    def test_seek_accepts_duration_as_position(self):
        """Seeking to the song duration should work (wrap-around safety)."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 240000
        backend.current_player = mock_player

        result = backend._handle_seek({"position_ms": 240000})

        assert result["status"] == "ok"
        assert backend.position_ms == 240000
        mock_player.seek.assert_called_once_with(240000)

    def test_seek_missing_position_defaults_to_zero(self):
        """When position_ms param is missing, should default to 0."""
        backend, states = self._get_backend()
        mock_player = MagicMock()
        mock_player.get_pos.return_value = 0
        backend.current_player = mock_player

        backend._handle_seek({})

        mock_player.seek.assert_called_once_with(0)
        assert backend.position_ms == 0


class TestDefect4StopNoCrash:
    """Regression: stop and poll must not crash when manager.poll() raises.

    Before the fix:
    - manager.poll() could raise NameError from kar.py:do_stuff() because
      STATE_CAPTURING was not imported there.
    - The NameError propagated through poll() → get_state() → _emit_state_change()
      → _handle_stop, crashing the backend.
    - handle_command also did not catch NameError in its except clause.
    """

    def _get_backend(self):
        from pykaraoke.core.backend import BackendState, PyKaraokeBackend
        return PyKaraokeBackend(), BackendState

    def test_poll_handles_manager_poll_exception(self):
        """poll() must not crash when manager.poll() raises."""
        backend, states = self._get_backend()
        backend.current_player = MagicMock()

        with patch("pykaraoke.core.backend.manager") as mock_mgr:
            mock_mgr.poll.side_effect = NameError("name 'STATE_CAPTURING' is not defined")
            # Should not raise
            backend.poll()

    def test_poll_handles_generic_exception(self):
        """poll() must not crash when manager.poll() raises any exception."""
        backend, states = self._get_backend()
        backend.current_player = MagicMock()

        with patch("pykaraoke.core.backend.manager") as mock_mgr:
            mock_mgr.poll.side_effect = RuntimeError("unexpected error")
            backend.poll()  # Must not raise

    def test_stop_does_not_crash_when_poll_raises(self):
        """_handle_stop must not crash when poll() encounters errors."""
        backend, states = self._get_backend()
        backend.current_player = MagicMock()
        backend.state = states.PLAYING

        with patch("pykaraoke.core.backend.manager") as mock_mgr:
            mock_mgr.poll.side_effect = NameError("name 'STATE_CAPTURING' is not defined")
            result = backend._handle_stop()

        assert result["status"] == "ok"
        assert backend.state == states.STOPPED
        assert backend.position_ms == 0

    def test_get_state_does_not_crash_when_poll_raises(self):
        """get_state() must not crash when poll() encounters errors."""
        backend, states = self._get_backend()
        backend.current_player = MagicMock()
        backend.state = states.PLAYING

        with patch("pykaraoke.core.backend.manager") as mock_mgr:
            mock_mgr.poll.side_effect = NameError("name 'STATE_CAPTURING' is not defined")
            state = backend.get_state()

        assert "playback_state" in state
        assert "position_ms" in state
        assert "duration_ms" in state
