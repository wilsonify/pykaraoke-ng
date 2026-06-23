//! Playback state management — mirrors `PykPlayer` from
//! `src/pykaraoke/core/player.py`.

use serde::{Deserialize, Serialize};

/// Player states mirroring `pykaraoke.config.constants`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PlayerState {
    /// Player created but not started
    Init = 0,
    /// Actively playing
    Playing = 1,
    /// Paused
    Paused = 2,
    /// Stopped/rewound
    NotPlaying = 3,
    /// Shutdown in progress
    Closing = 4,
    /// Fully shut down
    Closed = 5,
    /// Frame dump mode
    Capturing = 6,
}

/// Backend-level state mirroring `BackendState` from `pykaraoke.core.backend`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum BackendState {
    #[serde(rename = "idle")]
    Idle,
    #[serde(rename = "playing")]
    Playing,
    #[serde(rename = "paused")]
    Paused,
    #[serde(rename = "stopped")]
    Stopped,
    #[serde(rename = "loading")]
    Loading,
    #[serde(rename = "error")]
    Error,
}

impl Default for BackendState {
    fn default() -> Self {
        Self::Idle
    }
}

/// Playback timing state, mirroring `PykPlayer` time tracking fields.
#[derive(Debug, Clone)]
pub struct PlaybackTiming {
    /// Accumulated ms when paused/not playing
    pub play_time: u64,
    /// `get_ticks()` value when play started (adjusted for pauses)
    pub play_start_time: u64,
    /// Frame counter
    pub play_frame: u64,
    /// Seek target position in ms
    pub seek_pos_ms: u64,
    /// Offset time for internal sync
    pub internal_offset_time: u64,
    /// Sync delay in ms (adjustable with Ctrl+arrows)
    pub sync_delay_ms: i64,
}

impl Default for PlaybackTiming {
    fn default() -> Self {
        Self {
            play_time: 0,
            play_start_time: 0,
            play_frame: 0,
            seek_pos_ms: 0,
            internal_offset_time: 0,
            sync_delay_ms: 0,
        }
    }
}

/// Player instance state, mirroring `PykPlayer`.
#[derive(Debug, Clone)]
pub struct Player {
    pub state: PlayerState,
    pub timing: PlaybackTiming,
    pub supports_font_zoom: bool,
}

impl Default for Player {
    fn default() -> Self {
        Self {
            state: PlayerState::Init,
            timing: PlaybackTiming::default(),
            supports_font_zoom: false,
        }
    }
}

impl Player {
    pub fn new() -> Self {
        Self::default()
    }

    /// Transition to Playing state.
    /// Returns the previous state.
    pub fn play(&mut self, current_time_ms: u64) -> PlayerState {
        let prev = self.state;
        self.timing.play_start_time = current_time_ms;
        self.state = PlayerState::Playing;
        prev
    }

    /// Toggle between Playing and Paused.
    /// Returns the new state.
    pub fn pause(&mut self, current_time_ms: u64) -> PlayerState {
        match self.state {
            PlayerState::Playing => {
                self.timing.play_time = current_time_ms.saturating_sub(self.timing.play_start_time);
                self.state = PlayerState::Paused;
            }
            PlayerState::Paused => {
                self.timing.play_start_time = current_time_ms.saturating_sub(self.timing.play_time);
                self.state = PlayerState::Playing;
            }
            _ => {}
        }
        self.state
    }

    /// Seek to a position in ms.
    pub fn seek(&mut self, position_ms: u64, current_time_ms: u64) {
        self.timing.seek_pos_ms = position_ms;
        if self.state == PlayerState::Playing {
            self.timing.play_start_time = current_time_ms.saturating_sub(position_ms);
        } else {
            self.timing.play_time = position_ms;
        }
    }

    /// Rewind (stop and go back to start).
    pub fn rewind(&mut self) {
        self.timing.play_time = 0;
        self.timing.play_start_time = 0;
        self.timing.play_frame = 0;
        self.timing.seek_pos_ms = 0;
        self.state = PlayerState::NotPlaying;
    }

    /// Alias for `rewind`.
    pub fn stop(&mut self) {
        self.rewind();
    }

    /// Start closing sequence.
    pub fn close(&mut self) {
        self.state = PlayerState::Closing;
    }

    /// Complete shutdown.
    pub fn shutdown(&mut self) -> PlayerState {
        if self.state != PlayerState::Closed {
            self.state = PlayerState::Closed;
        }
        self.state
    }

    /// Get current position in ms.
    pub fn get_pos(&self, current_time_ms: u64) -> u64 {
        match self.state {
            PlayerState::Playing => {
                let base = current_time_ms.saturating_sub(self.timing.play_start_time);
                if self.timing.sync_delay_ms >= 0 {
                    base.saturating_add(self.timing.sync_delay_ms as u64)
                } else {
                    base.saturating_sub((-self.timing.sync_delay_ms) as u64)
                }
            }
            _ => self.timing.play_time,
        }
    }

    /// Get song length (default 0 — overridden by format handlers).
    pub fn get_length(&self) -> f64 {
        0.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_initial_state() {
        let player = Player::new();
        assert_eq!(player.state, PlayerState::Init);
    }

    #[test]
    fn test_play_transition() {
        let mut player = Player::new();
        player.play(1000);
        assert_eq!(player.state, PlayerState::Playing);
        assert_eq!(player.timing.play_start_time, 1000);
    }

    #[test]
    fn test_pause_toggle() {
        let mut player = Player::new();
        player.play(0);
        assert_eq!(player.state, PlayerState::Playing);

        player.pause(5000);
        assert_eq!(player.state, PlayerState::Paused);
        assert_eq!(player.timing.play_time, 5000);

        player.pause(8000);
        assert_eq!(player.state, PlayerState::Playing);
        // play_start_time should be adjusted: 8000 - 5000 = 3000
        assert_eq!(player.timing.play_start_time, 3000);
    }

    #[test]
    fn test_rewind_resets_timing() {
        let mut player = Player::new();
        player.play(0);
        player.pause(10000);
        player.rewind();

        assert_eq!(player.state, PlayerState::NotPlaying);
        assert_eq!(player.timing.play_time, 0);
        assert_eq!(player.timing.play_start_time, 0);
        assert_eq!(player.timing.play_frame, 0);
        assert_eq!(player.timing.seek_pos_ms, 0);
    }

    #[test]
    fn test_seek_during_play() {
        let mut player = Player::new();
        player.play(1000);
        player.seek(5000, 6000);

        assert_eq!(player.timing.seek_pos_ms, 5000);
        // play_start_time adjusted: 6000 - 5000 = 1000
        assert_eq!(player.timing.play_start_time, 1000);
    }

    #[test]
    fn test_seek_during_pause() {
        let mut player = Player::new();
        player.play(0);
        player.pause(5000);
        player.seek(3000, 5000);

        assert_eq!(player.timing.play_time, 3000);
    }

    #[test]
    fn test_close_and_shutdown() {
        let mut player = Player::new();
        player.close();
        assert_eq!(player.state, PlayerState::Closing);

        player.shutdown();
        assert_eq!(player.state, PlayerState::Closed);

        // Second shutdown should stay Closed
        player.shutdown();
        assert_eq!(player.state, PlayerState::Closed);
    }

    #[test]
    fn test_stop_is_rewind() {
        let mut player = Player::new();
        player.play(0);
        player.stop();
        assert_eq!(player.state, PlayerState::NotPlaying);
    }

    #[test]
    fn test_get_pos_during_play() {
        let mut player = Player::new();
        player.play(100);
        // current_time(500) - play_start_time(100) = 400
        assert_eq!(player.get_pos(500), 400);
    }

    #[test]
    fn test_get_pos_during_pause() {
        let mut player = Player::new();
        player.play(0);
        player.pause(5000);
        assert_eq!(player.get_pos(9999), 5000); // play_time is frozen
    }

    #[test]
    fn test_get_pos_with_sync_delay() {
        let mut player = Player::new();
        player.timing.sync_delay_ms = 250;
        player.play(100);
        // (500 - 100) + 250 = 650
        assert_eq!(player.get_pos(500), 650);
    }
}
