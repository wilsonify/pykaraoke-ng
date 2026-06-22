//! Queue management — mirrors playlist logic from
//! `src/pykaraoke/core/backend.py`.

use crate::song::SongStruct;
use serde::{Deserialize, Serialize};

/// Events emitted by the queue manager.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum QueueEvent {
    #[serde(rename = "playlist_updated")]
    PlaylistUpdated { data: PlaylistUpdatedData },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlaylistUpdatedData {
    pub playlist: Vec<SongSummary>,
}

/// A summary of a song for serialization to the frontend.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SongSummary {
    pub title: String,
    pub artist: String,
    pub filepath: String,
    pub display_filename: String,
}

impl From<&SongStruct> for SongSummary {
    fn from(song: &SongStruct) -> Self {
        Self {
            title: song.title.clone(),
            artist: song.artist.clone(),
            filepath: song.filepath.clone(),
            display_filename: song.display_filename.clone(),
        }
    }
}

/// Queue (playlist) manager.
#[derive(Debug, Clone)]
pub struct Queue {
    /// Ordered list of songs to play.
    pub playlist: Vec<SongStruct>,
    /// Index of the currently playing (or next to play) song.
    /// `None` when nothing is queued.
    pub playlist_index: Option<usize>,
    /// The currently loaded song (may be from the playlist or loaded directly).
    pub current_song: Option<SongStruct>,
}

impl Default for Queue {
    fn default() -> Self {
        Self {
            playlist: Vec::new(),
            playlist_index: None,
            current_song: None,
        }
    }
}

impl Queue {
    pub fn new() -> Self {
        Self::default()
    }

    fn sync_current_song(&mut self) {
        self.current_song = self
            .playlist_index
            .and_then(|index| self.playlist.get(index).cloned());
    }

    /// Add a song to the end of the playlist.
    pub fn add(&mut self, song: SongStruct) {
        self.playlist.push(song);
    }

    /// Remove a song from the playlist by index.
    /// Returns `None` if index is out of bounds.
    pub fn remove(&mut self, index: usize) -> Option<SongStruct> {
        if index < self.playlist.len() {
            let song = self.playlist.remove(index);
            // Adjust current index if needed
            if let Some(current) = self.playlist_index {
                if index < current {
                    self.playlist_index = Some(current - 1);
                } else if index == current {
                    self.playlist_index = if current < self.playlist.len() {
                        Some(current)
                    } else if self.playlist.is_empty() {
                        None
                    } else {
                        Some(self.playlist.len() - 1)
                    };
                }
            }
            self.sync_current_song();
            Some(song)
        } else {
            None
        }
    }

    /// Move a song within the playlist and keep the current selection stable.
    /// Returns `false` if either index is out of bounds.
    pub fn move_item(&mut self, from: usize, to: usize) -> bool {
        if from >= self.playlist.len() || to >= self.playlist.len() {
            return false;
        }
        if from == to {
            return true;
        }

        let selected_song = self.current_song.clone();
        let song = self.playlist.remove(from);
        self.playlist.insert(to, song);

        if let Some(selected) = selected_song {
            self.playlist_index = self
                .playlist
                .iter()
                .position(|song| song.filepath == selected.filepath);
        }
        self.sync_current_song();
        true
    }

    /// Clear the entire playlist.
    pub fn clear(&mut self) {
        self.playlist.clear();
        self.playlist_index = None;
        self.current_song = None;
    }

    /// Get the current playlist length.
    pub fn len(&self) -> usize {
        self.playlist.len()
    }

    /// Returns `true` if the playlist is empty.
    pub fn is_empty(&self) -> bool {
        self.playlist.is_empty()
    }

    /// Get a reference to a song at a given index.
    pub fn get(&self, index: usize) -> Option<&SongStruct> {
        self.playlist.get(index)
    }

    /// Select a song from the playlist as the current song.
    /// Returns `None` if the index is out of bounds.
    pub fn select(&mut self, index: usize) -> Option<&SongStruct> {
        if index < self.playlist.len() {
            self.playlist_index = Some(index);
            self.current_song = Some(self.playlist[index].clone());
            self.current_song.as_ref()
        } else {
            None
        }
    }

    /// Advance to the next song in the playlist.
    /// Returns `None` if already at the end.
    pub fn advance(&mut self) -> Option<&SongStruct> {
        let next_index = self.playlist_index.map(|i| i + 1).unwrap_or(0);
        self.select(next_index)
    }

    /// Go back to the previous song in the playlist.
    /// Returns `None` if already at the beginning.
    pub fn previous(&mut self) -> Option<&SongStruct> {
        let prev_index = match self.playlist_index {
            Some(i) if i > 0 => i - 1,
            _ => return None,
        };
        self.select(prev_index)
    }

    /// Get summaries of all songs in the playlist (for serialization).
    pub fn summaries(&self) -> Vec<SongSummary> {
        self.playlist.iter().map(SongSummary::from).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_song(title: &str, artist: &str, filepath: &str) -> SongStruct {
        SongStruct {
            title: title.to_string(),
            artist: artist.to_string(),
            filepath: filepath.to_string(),
            display_filename: filepath.rsplit_once('/')
                .map(|(_, f)| f.to_string())
                .unwrap_or_else(|| filepath.to_string()),
            ..Default::default()
        }
    }

    #[test]
    fn test_empty_queue() {
        let queue = Queue::new();
        assert!(queue.is_empty());
        assert_eq!(queue.len(), 0);
    }

    #[test]
    fn test_add_song() {
        let mut queue = Queue::new();
        queue.add(make_song("Test", "Artist", "/tmp/test.kar"));
        assert_eq!(queue.len(), 1);
        assert!(!queue.is_empty());
    }

    #[test]
    fn test_add_multiple() {
        let mut queue = Queue::new();
        queue.add(make_song("Song 1", "A", "/tmp/1.kar"));
        queue.add(make_song("Song 2", "B", "/tmp/2.kar"));
        queue.add(make_song("Song 3", "C", "/tmp/3.kar"));
        assert_eq!(queue.len(), 3);
    }

    #[test]
    fn test_remove_by_index() {
        let mut queue = Queue::new();
        queue.add(make_song("Song 1", "A", "/tmp/1.kar"));
        queue.add(make_song("Song 2", "B", "/tmp/2.kar"));
        queue.add(make_song("Song 3", "C", "/tmp/3.kar"));

        let removed = queue.remove(1);
        assert!(removed.is_some());
        assert_eq!(removed.unwrap().title, "Song 2");
        assert_eq!(queue.len(), 2);
    }

    #[test]
    fn test_remove_out_of_bounds() {
        let mut queue = Queue::new();
        let removed = queue.remove(0);
        assert!(removed.is_none());
    }

    #[test]
    fn test_clear() {
        let mut queue = Queue::new();
        queue.add(make_song("Song 1", "A", "/tmp/1.kar"));
        queue.add(make_song("Song 2", "B", "/tmp/2.kar"));
        queue.clear();
        assert!(queue.is_empty());
        assert!(queue.current_song.is_none());
    }

    #[test]
    fn test_select_song() {
        let mut queue = Queue::new();
        queue.add(make_song("Song 1", "A", "/tmp/1.kar"));
        queue.add(make_song("Song 2", "B", "/tmp/2.kar"));

        let selected = queue.select(1);
        assert!(selected.is_some());
        assert_eq!(selected.unwrap().title, "Song 2");
        assert_eq!(queue.playlist_index, Some(1));
    }

    #[test]
    fn test_select_out_of_bounds() {
        let mut queue = Queue::new();
        let selected = queue.select(0);
        assert!(selected.is_none());
    }

    #[test]
    fn test_advance() {
        let mut queue = Queue::new();
        queue.add(make_song("Song 1", "A", "/tmp/1.kar"));
        queue.add(make_song("Song 2", "B", "/tmp/2.kar"));
        queue.select(0);

        let next = queue.advance();
        assert!(next.is_some());
        assert_eq!(next.unwrap().title, "Song 2");
        assert_eq!(queue.playlist_index, Some(1));
    }

    #[test]
    fn test_advance_past_end() {
        let mut queue = Queue::new();
        queue.add(make_song("Song 1", "A", "/tmp/1.kar"));
        queue.select(0);

        let next = queue.advance();
        assert!(next.is_none()); // past end
    }

    #[test]
    fn test_previous() {
        let mut queue = Queue::new();
        queue.add(make_song("Song 1", "A", "/tmp/1.kar"));
        queue.add(make_song("Song 2", "B", "/tmp/2.kar"));
        queue.select(1);

        let prev = queue.previous();
        assert!(prev.is_some());
        assert_eq!(prev.unwrap().title, "Song 1");
        assert_eq!(queue.playlist_index, Some(0));
    }

    #[test]
    fn test_previous_at_start() {
        let mut queue = Queue::new();
        queue.add(make_song("Song 1", "A", "/tmp/1.kar"));
        queue.select(0);

        let prev = queue.previous();
        assert!(prev.is_none());
    }

    #[test]
    fn test_remove_adjusts_index() {
        let mut queue = Queue::new();
        queue.add(make_song("A", "A1", "/tmp/a.kar"));
        queue.add(make_song("B", "B1", "/tmp/b.kar"));
        queue.add(make_song("C", "C1", "/tmp/c.kar"));
        queue.select(2); // select "C" at index 2

        queue.remove(0); // remove "A"
        assert_eq!(queue.playlist_index, Some(1)); // "C" is now at index 1
        assert_eq!(queue.current_song.as_ref().unwrap().title, "C");
    }

    #[test]
    fn test_remove_current_updates_current_song() {
        let mut queue = Queue::new();
        queue.add(make_song("A", "A1", "/tmp/a.kar"));
        queue.add(make_song("B", "B1", "/tmp/b.kar"));
        queue.add(make_song("C", "C1", "/tmp/c.kar"));
        queue.select(1);

        let removed = queue.remove(1).unwrap();
        assert_eq!(removed.title, "B");
        assert_eq!(queue.playlist_index, Some(1));
        assert_eq!(queue.current_song.as_ref().unwrap().title, "C");
    }

    #[test]
    fn test_remove_only_current_clears_current_song() {
        let mut queue = Queue::new();
        queue.add(make_song("A", "A1", "/tmp/a.kar"));
        queue.select(0);

        queue.remove(0);
        assert!(queue.playlist_index.is_none());
        assert!(queue.current_song.is_none());
    }

    #[test]
    fn test_move_item_keeps_current_song_selected() {
        let mut queue = Queue::new();
        queue.add(make_song("A", "A1", "/tmp/a.kar"));
        queue.add(make_song("B", "B1", "/tmp/b.kar"));
        queue.add(make_song("C", "C1", "/tmp/c.kar"));
        queue.select(0);

        assert!(queue.move_item(0, 2));
        assert_eq!(queue.playlist_index, Some(2));
        assert_eq!(queue.current_song.as_ref().unwrap().title, "A");
        assert_eq!(queue.playlist[2].title, "A");
    }

    #[test]
    fn test_summaries() {
        let mut queue = Queue::new();
        queue.add(make_song("Song 1", "Artist 1", "/tmp/1.kar"));
        queue.add(make_song("Song 2", "Artist 2", "/tmp/2.kar"));

        let summaries = queue.summaries();
        assert_eq!(summaries.len(), 2);
        assert_eq!(summaries[0].title, "Song 1");
        assert_eq!(summaries[1].artist, "Artist 2");
    }
}
