//! Library scanning and management — mirrors `SongDB` search, sort, and
//! folder management from `src/pykaraoke/core/database.py`.

use crate::discovery::{ScanResults, SongScanner};
use crate::filename_parser::FilenameParser;
use crate::song::{SongStruct, SupportedExtensions};
use sha2::{Digest, Sha256};
use std::collections::HashSet;

/// Search result entry with match information.
#[derive(Debug, Clone)]
pub struct SearchResult {
    pub song: SongStruct,
    pub score: u32,
}

/// Library/song database — in-memory collection of songs with search/sort.
#[derive(Debug, Clone)]
pub struct Library {
    /// All songs discovered during scanning.
    pub full_song_list: Vec<SongStruct>,
    /// Deduplicated list of songs.
    pub unique_song_list: Vec<SongStruct>,
    /// Configured folders to scan.
    pub folder_list: Vec<String>,
    /// Supported file extensions.
    pub extensions: SupportedExtensions,
    /// Filename parser configuration.
    pub filename_parser: FilenameParser,
    /// Whether to derive song info from filename.
    pub derive_from_filename: bool,
}

impl Default for Library {
    fn default() -> Self {
        Self {
            full_song_list: Vec::new(),
            unique_song_list: Vec::new(),
            folder_list: Vec::new(),
            extensions: SupportedExtensions::default(),
            filename_parser: FilenameParser::default(),
            derive_from_filename: true,
        }
    }
}

impl Library {
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a folder to the scan list.
    pub fn add_folder(&mut self, folder: String) {
        if !self.folder_list.contains(&folder) {
            self.folder_list.push(folder);
        }
    }

    /// Remove a folder from the scan list.
    pub fn remove_folder(&mut self, folder: &str) -> bool {
        if let Some(pos) = self.folder_list.iter().position(|f| f == folder) {
            self.folder_list.remove(pos);
            true
        } else {
            false
        }
    }

    /// Scan all configured folders and rebuild the song database.
    pub fn scan(&mut self) -> ScanResults {
        let mut scanner = SongScanner::new();
        scanner.extensions = self.extensions.clone();
        scanner.look_inside_zips = true;

        let mut results = scanner.scan_directories(&self.folder_list);

        // If configured, derive artist/title from filenames
        if self.derive_from_filename {
            for song in &mut results.songs {
                let parsed = self.filename_parser.parse(&song.filepath);
                if song.artist.is_empty() {
                    song.artist = parsed.artist;
                }
                if song.title.is_empty() {
                    song.title = parsed.title;
                }
                if song.disc.is_empty() {
                    song.disc = parsed.disc;
                }
                if song.track.is_empty() {
                    song.track = parsed.track;
                }
            }
        }

        self.full_song_list = results.songs.clone();
        self.unique_song_list = self.build_unique_list(&results.songs);

        results
    }

    /// Build a deduplicated list of songs (by filepath).
    fn build_unique_list(&self, songs: &[SongStruct]) -> Vec<SongStruct> {
        let mut seen = HashSet::new();
        let mut unique = Vec::new();

        for song in songs {
            if seen.insert(song.filepath.clone()) {
                unique.push(song.clone());
            }
        }

        unique
    }

    /// Full-text search across title, artist, and filename.
    ///
    /// Performs case-insensitive multi-term matching, mirroring the
    /// Python `SongDB.search_database()` method.
    pub fn search(&self, query: &str) -> Vec<SearchResult> {
        if query.trim().is_empty() {
            return self
                .unique_song_list
                .iter()
                .map(|s| SearchResult {
                    song: s.clone(),
                    score: 0,
                })
                .collect();
        }

        let terms: Vec<String> = query
            .to_lowercase()
            .split_whitespace()
            .map(|s| s.to_string())
            .collect();

        let mut results: Vec<SearchResult> = self
            .unique_song_list
            .iter()
            .filter(|song| {
                let haystack = format!(
                    "{} {} {} {}",
                    song.title.to_lowercase(),
                    song.artist.to_lowercase(),
                    song.display_filename.to_lowercase(),
                    song.filepath.to_lowercase()
                );
                terms.iter().all(|term| haystack.contains(term))
            })
            .map(|song| SearchResult {
                song: song.clone(),
                score: 0,
            })
            .collect();

        // Sort by title alphabetically (mirrors Python default)
        results.sort_by(|a, b| a.song.title.cmp(&b.song.title));

        results
    }

    /// Sort the unique song list by a given key.
    pub fn sort_by(&mut self, key: &str) {
        match key {
            "title" => {
                self.unique_song_list.sort_by(|a, b| a.title.cmp(&b.title));
            }
            "artist" => {
                self.unique_song_list.sort_by(|a, b| a.artist.cmp(&b.artist));
            }
            "filename" => {
                self.unique_song_list
                    .sort_by(|a, b| a.display_filename.cmp(&b.display_filename));
            }
            _ => {}
        }
    }

    /// Compute the SHA-256 hash of a song file for duplicate detection.
    /// Returns `None` if the file cannot be read.
    pub fn compute_hash(&self, song: &SongStruct) -> Option<String> {
        let path = std::path::Path::new(&song.filepath);
        let data = std::fs::read(path).ok()?;
        let mut hasher = Sha256::new();
        hasher.update(&data);
        let result = hasher.finalize();
        Some(format!("{:x}", result))
    }

    /// Find duplicates in the song list based on file hashes.
    pub fn find_duplicates(&self) -> Vec<Vec<SongStruct>> {
        let mut hash_map: std::collections::BTreeMap<String, Vec<SongStruct>> =
            std::collections::BTreeMap::new();

        for song in &self.unique_song_list {
            if let Some(hash) = self.compute_hash(song) {
                hash_map.entry(hash).or_default().push(song.clone());
            }
        }

        hash_map
            .into_values()
            .filter(|group| group.len() > 1)
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::song::SongStruct;

    fn make_song(title: &str, artist: &str, filepath: &str) -> SongStruct {
        SongStruct {
            title: title.to_string(),
            artist: artist.to_string(),
            filepath: filepath.to_string(),
            display_filename: filepath
                .rsplit_once('/')
                .map(|(_, f)| f.to_string())
                .unwrap_or_else(|| filepath.to_string()),
            extension: filepath
                .rsplit_once('.')
                .map(|(_, e)| format!(".{}", e))
                .unwrap_or_default(),
            ..Default::default()
        }
    }

    fn library_with_songs() -> Library {
        let mut lib = Library::new();
        lib.unique_song_list = vec![
            make_song("Bohemian Rhapsody", "Queen", "/music/queen/bohemian.kar"),
            make_song("Stairway to Heaven", "Led Zeppelin", "/music/led/stairway.kar"),
            make_song("Hotel California", "Eagles", "/music/eagles/hotel.kar"),
        ];
        lib.full_song_list = lib.unique_song_list.clone();
        lib
    }

    #[test]
    fn test_empty_library() {
        let lib = Library::new();
        assert!(lib.unique_song_list.is_empty());
        assert!(lib.full_song_list.is_empty());
    }

    #[test]
    fn test_add_folder() {
        let mut lib = Library::new();
        lib.add_folder("/music".to_string());
        assert_eq!(lib.folder_list.len(), 1);
        // Adding same folder again should not duplicate
        lib.add_folder("/music".to_string());
        assert_eq!(lib.folder_list.len(), 1);
    }

    #[test]
    fn test_remove_folder() {
        let mut lib = Library::new();
        lib.add_folder("/music".to_string());
        assert!(lib.remove_folder("/music"));
        assert!(!lib.remove_folder("/nonexistent"));
    }

    #[test]
    fn test_search_empty_query() {
        let lib = library_with_songs();
        let results = lib.search("");
        assert_eq!(results.len(), 3);
    }

    #[test]
    fn test_search_by_title() {
        let lib = library_with_songs();
        let results = lib.search("bohemian");
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].song.title, "Bohemian Rhapsody");
    }

    #[test]
    fn test_search_by_artist() {
        let lib = library_with_songs();
        let results = lib.search("queen");
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].song.artist, "Queen");
    }

    #[test]
    fn test_search_multi_term() {
        let lib = library_with_songs();
        let results = lib.search("led heaven");
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].song.title, "Stairway to Heaven");
    }

    #[test]
    fn test_search_case_insensitive() {
        let lib = library_with_songs();
        let results = lib.search("BOHEMIAN");
        assert_eq!(results.len(), 1);
    }

    #[test]
    fn test_search_no_match() {
        let lib = library_with_songs();
        let results = lib.search("nonexistent_song_xyz");
        assert!(results.is_empty());
    }

    #[test]
    fn test_sort_by_title() {
        let mut lib = library_with_songs();
        lib.sort_by("title");
        assert_eq!(lib.unique_song_list[0].title, "Bohemian Rhapsody");
        assert_eq!(lib.unique_song_list[1].title, "Hotel California");
        assert_eq!(lib.unique_song_list[2].title, "Stairway to Heaven");
    }

    #[test]
    fn test_sort_by_artist() {
        let mut lib = library_with_songs();
        lib.sort_by("artist");
        assert_eq!(lib.unique_song_list[0].artist, "Eagles");
        assert_eq!(lib.unique_song_list[1].artist, "Led Zeppelin");
        assert_eq!(lib.unique_song_list[2].artist, "Queen");
    }

    #[test]
    fn test_build_unique_list() {
        let lib = Library::new();
        let songs = vec![
            make_song("A", "A1", "/same/path.kar"),
            make_song("B", "B1", "/same/path.kar"), // same filepath
            make_song("C", "C1", "/different.kar"),
        ];
        let unique = lib.build_unique_list(&songs);
        assert_eq!(unique.len(), 2); // duplicate removed
    }
}
