//! Filename parser — extracts artist, title, disc, and track from karaoke files.
//!
//! This is a direct port of `src/pykaraoke/core/filename_parser.py`.
//! Behaviour should be byte-identical for every input.
//!
//! Supported patterns:
//!   - `"Artist - Title.mp3"`                (space-dash-space separator)
//!   - `"Artist - Title - Live.mp3"`         (multiple space-dash-space segments)
//!   - `"Artist - Title (Remix).cdg"`        (parenthetical modifiers)
//!   - `"SC1234-05-John Doe-My Song.cdg"`    (legacy Disc-Track-Artist-Title)
//!   - `"SC123405-John Doe-My Song.cdg"`     (legacy DiscTrack-Artist-Title)
//!   - `"SC1234-John Doe-My Song.cdg"`       (legacy Disc-Artist-Title)
//!   - `"John Doe-My Song.cdg"`              (legacy Artist-Title)

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::path::Path;

/// Legacy filename naming conventions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FileNameType {
    /// Disc-Track-Artist-Title.ext  (e.g. `SC1234-05-John Doe-My Song.cdg`)
    DiscTrackArtistTitle = 0,
    /// DiscTrack-Artist-Title.ext  (e.g. `SC123405-John Doe-My Song.cdg`)
    DisctrackArtistTitle = 1,
    /// Disc-Artist-Title.ext  (e.g. `SC1234-John Doe-My Song.cdg`)
    DiscArtistTitle = 2,
    /// Artist-Title.ext  (e.g. `John Doe-My Song.cdg`)
    ArtistTitle = 3,
}

/// Result of parsing a karaoke filename.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ParsedSong {
    pub artist: String,
    pub title: String,
    pub disc: String,
    pub track: String,
}

impl Default for ParsedSong {
    fn default() -> Self {
        Self {
            artist: String::new(),
            title: String::new(),
            disc: String::new(),
            track: String::new(),
        }
    }
}

use once_cell::sync::Lazy;

/// Regex matching `" - "` with optional surrounding whitespace
static SPACE_DASH_RE: Lazy<Regex> = Lazy::new(|| Regex::new(r"\s+-\s+").unwrap());

/// Return `true` if `part` looks like a short all-caps abbreviation
/// (e.g. "AC", "DC", "DJ", "MC", "ZZ").
///
/// A part qualifies when it has at least one alphabetic character,
/// every cased character is uppercase, and the total length ≤ 3.
fn is_abbreviation_part(part: &str) -> bool {
    if part.is_empty() || part.len() > 3 {
        return false;
    }
    // Every alphabetic character must be uppercase
    part.chars().any(|c| c.is_alphabetic())
        && part.chars().all(|c| !c.is_lowercase())
}

/// Parses karaoke filenames to extract artist, title, disc, and track.
///
/// Strategy:
/// 1. Extracts only the basename so directory dashes are ignored.
/// 2. Strips the file extension.
/// 3. If the basename contains `" - "` (space-dash-space), the modern
///    split strategy is used: first segment = artist, rest = title.
/// 4. Otherwise the legacy dash-split strategy is applied according
///    to `file_name_type`.
#[derive(Debug, Clone)]
pub struct FilenameParser {
    file_name_type: FileNameType,
}

impl Default for FilenameParser {
    fn default() -> Self {
        Self {
            file_name_type: FileNameType::ArtistTitle,
        }
    }
}

impl FilenameParser {
    pub fn new(file_name_type: FileNameType) -> Self {
        Self { file_name_type }
    }

    /// Parse `filepath` and return a `ParsedSong`.
    pub fn parse(&self, filepath: &str) -> ParsedSong {
        // Normalise path separators, extract basename
        let normalized = filepath.replace('\\', "/");
        let filename = Path::new(&normalized)
            .file_name()
            .map(|s| s.to_string_lossy().to_string())
            .unwrap_or_default();

        // Remove file extension.
        // If the only dot is at position 0 (e.g. ".cdg") treat it as no
        // extension (matching Python's os.path.splitext behaviour).
        let stem = match filename.rfind('.') {
            Some(pos) if pos > 0 => filename[..pos].to_string(),
            _ => filename.clone(),
        };

        if SPACE_DASH_RE.is_match(&stem) {
            return self.parse_space_dash(&stem);
        }

        self.parse_legacy(&stem)
    }

    /// Parse a ZIP member path, using directory structure as fallback.
    ///
    /// First tries regular parsing on the basename.  If that yields
    /// no artist, uses the parent directory component as the artist.
    /// This supports layouts like:
    ///   - `Language/Artist/Title.kar`
    ///   - `Artist/Title.kar`
    pub fn parse_zip_path(&self, zip_stored_name: &str) -> ParsedSong {
        let mut result = self.parse(zip_stored_name);

        if result.artist.is_empty() {
            let normalized = zip_stored_name.replace('\\', "/");
            let components: Vec<&str> = normalized.split('/').collect();
            if components.len() >= 2 {
                let artist = components[components.len() - 2].trim();
                if !artist.is_empty() {
                    result.artist = artist.to_string();
                }
            }
        }

        result
    }

    // ------------------------------------------------------------------
    // Private helpers
    // ------------------------------------------------------------------

    /// Handle the modern `"Artist - Title"` family of patterns.
    ///
    /// All text before the first `" - "` separator becomes the artist;
    /// everything after (including additional `" - "` segments) becomes
    /// the title.
    fn parse_space_dash(&self, stem: &str) -> ParsedSong {
        let parts: Vec<&str> = SPACE_DASH_RE.splitn(stem, 2).collect();
        if parts.len() == 2 {
            ParsedSong {
                artist: parts[0].trim().to_string(),
                title: parts[1].trim().to_string(),
                ..Default::default()
            }
        } else {
            // Only one part means the regex found nothing useful
            ParsedSong {
                title: stem.trim().to_string(),
                ..Default::default()
            }
        }
    }

    /// Handle the legacy `"Disc-Track-Artist-Title"` family of patterns.
    fn parse_legacy(&self, stem: &str) -> ParsedSong {
        let parts: Vec<&str> = stem.split('-').collect();

        match self.file_name_type {
            FileNameType::DiscTrackArtistTitle => {
                if parts.len() >= 4 {
                    ParsedSong {
                        disc: parts[0].trim().to_string(),
                        track: parts[1].trim().to_string(),
                        artist: parts[2].trim().to_string(),
                        title: parts[3..].join("-").trim().to_string(),
                    }
                } else {
                    ParsedSong {
                        title: stem.trim().to_string(),
                        ..Default::default()
                    }
                }
            }
            FileNameType::DisctrackArtistTitle | FileNameType::DiscArtistTitle => {
                if parts.len() >= 3 {
                    ParsedSong {
                        disc: parts[0].trim().to_string(),
                        artist: parts[1].trim().to_string(),
                        title: parts[2..].join("-").trim().to_string(),
                        ..Default::default()
                    }
                } else {
                    ParsedSong {
                        title: stem.trim().to_string(),
                        ..Default::default()
                    }
                }
            }
            FileNameType::ArtistTitle => self.parse_artist_title(&parts),
        }
    }

    /// Handle the `"Artist-Title"` legacy pattern with abbreviation heuristic.
    fn parse_artist_title(&self, parts: &[&str]) -> ParsedSong {
        if parts.len() < 2 {
            return ParsedSong {
                title: parts.join("-").trim().to_string(),
                ..Default::default()
            };
        }

        if is_abbreviation_part(parts[0]) {
            let mut i = 1;
            while i < parts.len() - 1 && is_abbreviation_part(parts[i]) {
                i += 1;
            }
            ParsedSong {
                artist: parts[..i].join("-").trim().to_string(),
                title: parts[i..].join("-").trim().to_string(),
                ..Default::default()
            }
        } else {
            ParsedSong {
                artist: parts[0].trim().to_string(),
                title: parts[1..].join("-").trim().to_string(),
                ..Default::default()
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parser(name_type: FileNameType) -> FilenameParser {
        FilenameParser::new(name_type)
    }

    // ── Space-dash-space pattern tests ─────────────────────────────

    #[test]
    fn test_basic_artist_title() {
        let result = parser(FileNameType::ArtistTitle).parse("Artist - Title.mp3");
        assert_eq!(result.artist, "Artist");
        assert_eq!(result.title, "Title");
    }

    #[test]
    fn test_title_with_spaces() {
        let result = parser(FileNameType::ArtistTitle).parse("John Doe - My Song.mp3");
        assert_eq!(result.artist, "John Doe");
        assert_eq!(result.title, "My Song");
    }

    #[test]
    fn test_title_with_parenthetical() {
        let result = parser(FileNameType::ArtistTitle).parse("Artist - Title (Remix).cdg");
        assert_eq!(result.artist, "Artist");
        assert_eq!(result.title, "Title (Remix)");
    }

    #[test]
    fn test_multiple_space_dash_segments() {
        let result = parser(FileNameType::ArtistTitle).parse("Artist - Title - Live.mp3");
        assert_eq!(result.artist, "Artist");
        assert_eq!(result.title, "Title - Live");
    }

    #[test]
    fn test_the_beatles() {
        let result = parser(FileNameType::ArtistTitle).parse("The Beatles - Let It Be - Live.kar");
        assert_eq!(result.artist, "The Beatles");
        assert_eq!(result.title, "Let It Be - Live");
    }

    #[test]
    fn test_kar_extension() {
        let result = parser(FileNameType::ArtistTitle).parse("Sinatra - My Way.kar");
        assert_eq!(result.artist, "Sinatra");
        assert_eq!(result.title, "My Way");
    }

    #[test]
    fn test_numbers_in_title() {
        let result = parser(FileNameType::ArtistTitle).parse("Artist - Song 2024.cdg");
        assert_eq!(result.artist, "Artist");
        assert_eq!(result.title, "Song 2024");
    }

    #[test]
    fn test_dashes_in_title_after_separator() {
        let result = parser(FileNameType::ArtistTitle).parse("Artist - A-B-C Song.cdg");
        assert_eq!(result.artist, "Artist");
        assert_eq!(result.title, "A-B-C Song");
    }

    #[test]
    fn test_leading_trailing_spaces() {
        let result = parser(FileNameType::ArtistTitle).parse("  Artist   -   Title  .mp3");
        assert_eq!(result.artist, "Artist");
        assert_eq!(result.title, "Title");
    }

    #[test]
    fn test_directory_dashes_ignored() {
        let result = parser(FileNameType::ArtistTitle).parse("/music/rock-band/best-of/Artist - Title.mp3");
        assert_eq!(result.artist, "Artist");
        assert_eq!(result.title, "Title");
    }

    #[test]
    fn test_windows_path_dashes_ignored() {
        let result = parser(FileNameType::ArtistTitle).parse(r"C:\my-music\rock-hits\Queen - Bohemian Rhapsody.cdg");
        assert_eq!(result.artist, "Queen");
        assert_eq!(result.title, "Bohemian Rhapsody");
    }

    #[test]
    fn test_disc_and_track_empty_for_space_dash() {
        let result = parser(FileNameType::ArtistTitle).parse("Artist - Title.mp3");
        assert_eq!(result.disc, "");
        assert_eq!(result.track, "");
    }

    // ── Legacy Disc-Track-Artist-Title ────────────────────────────

    #[test]
    fn test_disc_track_artist_title_four_part() {
        let result = parser(FileNameType::DiscTrackArtistTitle)
            .parse("SC1234-05-John Doe-My Song.cdg");
        assert_eq!(result.disc, "SC1234");
        assert_eq!(result.track, "05");
        assert_eq!(result.artist, "John Doe");
        assert_eq!(result.title, "My Song");
    }

    #[test]
    fn test_disc_track_artist_title_extra_dashes() {
        let result = parser(FileNameType::DiscTrackArtistTitle)
            .parse("SC1234-05-Artist-Title-With-Dashes.cdg");
        assert_eq!(result.disc, "SC1234");
        assert_eq!(result.track, "05");
        assert_eq!(result.artist, "Artist");
        assert_eq!(result.title, "Title-With-Dashes");
    }

    #[test]
    fn test_disc_track_artist_title_rolling_stones() {
        let result = parser(FileNameType::DiscTrackArtistTitle)
            .parse("SC1234-05-The Rolling Stones-Paint It Black.cdg");
        assert_eq!(result.disc, "SC1234");
        assert_eq!(result.track, "05");
        assert_eq!(result.artist, "The Rolling Stones");
        assert_eq!(result.title, "Paint It Black");
    }

    #[test]
    fn test_disc_track_artist_title_fewer_than_four() {
        let result = parser(FileNameType::DiscTrackArtistTitle).parse("OnePart.cdg");
        assert_eq!(result.title, "OnePart");
        assert_eq!(result.artist, "");
    }

    // ── Legacy DiscTrack-Artist-Title ─────────────────────────────

    #[test]
    fn test_disctrack_artist_title() {
        let result = parser(FileNameType::DisctrackArtistTitle)
            .parse("SC123405-John Doe-My Song.cdg");
        assert_eq!(result.disc, "SC123405");
        assert_eq!(result.artist, "John Doe");
        assert_eq!(result.title, "My Song");
    }

    #[test]
    fn test_disctrack_artist_title_ab9901() {
        let result = parser(FileNameType::DisctrackArtistTitle)
            .parse("AB9901-Queen-Bohemian Rhapsody.cdg");
        assert_eq!(result.disc, "AB9901");
        assert_eq!(result.artist, "Queen");
        assert_eq!(result.title, "Bohemian Rhapsody");
    }

    // ── Legacy Disc-Artist-Title ──────────────────────────────────

    #[test]
    fn test_disc_artist_title() {
        let result = parser(FileNameType::DiscArtistTitle)
            .parse("SC1234-John Doe-My Song.cdg");
        assert_eq!(result.disc, "SC1234");
        assert_eq!(result.artist, "John Doe");
        assert_eq!(result.title, "My Song");
    }

    #[test]
    fn test_disc_artist_title_adele() {
        let result = parser(FileNameType::DiscArtistTitle)
            .parse("DISC1-Adele-Hello.kar");
        assert_eq!(result.disc, "DISC1");
        assert_eq!(result.artist, "Adele");
        assert_eq!(result.title, "Hello");
    }

    // ── Legacy Artist-Title ────────────────────────────────────────

    #[test]
    fn test_legacy_artist_title() {
        let result = parser(FileNameType::ArtistTitle).parse("John Doe-My Song.cdg");
        assert_eq!(result.artist, "John Doe");
        assert_eq!(result.title, "My Song");
    }

    #[test]
    fn test_legacy_artist_title_queen() {
        let result = parser(FileNameType::ArtistTitle).parse("Queen-Bohemian Rhapsody.kar");
        assert_eq!(result.artist, "Queen");
        assert_eq!(result.title, "Bohemian Rhapsody");
    }

    #[test]
    fn test_legacy_artist_title_extra_dashes() {
        let result = parser(FileNameType::ArtistTitle).parse("Artist-Title-Extra.cdg");
        assert_eq!(result.artist, "Artist");
        assert_eq!(result.title, "Title-Extra");
    }

    #[test]
    fn test_legacy_single_part() {
        let result = parser(FileNameType::ArtistTitle).parse("JustTitle.cdg");
        assert_eq!(result.title, "JustTitle");
        assert_eq!(result.artist, "");
    }

    // ── Edge cases ────────────────────────────────────────────────

    #[test]
    fn test_extension_stripped() {
        let result = parser(FileNameType::ArtistTitle).parse("Artist - Title.cdg");
        assert!(!result.artist.contains(".cdg"));
        assert!(!result.title.contains(".cdg"));
    }

    #[test]
    fn test_multiple_extensions() {
        let result = parser(FileNameType::ArtistTitle).parse("Artist - Song.name.cdg");
        assert_eq!(result.title, "Song.name");
    }

    #[test]
    fn test_deep_directory_path() {
        let result = parser(FileNameType::ArtistTitle).parse("/a-b/c-d/e-f/Artist - Title.cdg");
        assert_eq!(result.artist, "Artist");
        assert_eq!(result.title, "Title");
    }

    #[test]
    fn test_empty_filepath() {
        let result = parser(FileNameType::ArtistTitle).parse("");
        assert_eq!(result.artist, "");
        assert_eq!(result.title, "");
    }

    #[test]
    fn test_only_extension() {
        // os.path.splitext treats ".cdg" as a dotfile with no extension,
        // so the stem is ".cdg" itself
        let result = parser(FileNameType::ArtistTitle).parse(".cdg");
        assert_eq!(result.artist, "");
        assert_eq!(result.title, ".cdg");
    }

    #[test]
    fn test_no_separator() {
        let result = parser(FileNameType::ArtistTitle).parse("JustATitle.mp3");
        assert_eq!(result.title, "JustATitle");
        assert_eq!(result.artist, "");
    }

    #[test]
    fn test_unicode_filenames() {
        let result = parser(FileNameType::ArtistTitle).parse("Björk - Jóga.cdg");
        assert_eq!(result.artist, "Björk");
        assert_eq!(result.title, "Jóga");
    }

    #[test]
    fn test_parenthetical_title() {
        let result = parser(FileNameType::ArtistTitle).parse("Artist - Title (feat. Someone).cdg");
        assert_eq!(result.title, "Title (feat. Someone)");
    }

    #[test]
    fn test_numbers_only_title() {
        let result = parser(FileNameType::ArtistTitle).parse("Artist - 99 Problems.cdg");
        assert_eq!(result.artist, "Artist");
        assert_eq!(result.title, "99 Problems");
    }

    // ── ParsedSong defaults ───────────────────────────────────────

    #[test]
    fn test_parsed_song_defaults() {
        let song = ParsedSong::default();
        assert_eq!(song.artist, "");
        assert_eq!(song.title, "");
        assert_eq!(song.disc, "");
        assert_eq!(song.track, "");
    }

    // ── Abbreviation heuristic ────────────────────────────────────

    #[test]
    fn test_abbreviation_artist_ac_dc() {
        // "AC-DC" should be treated as a single artist name
        let result = parser(FileNameType::ArtistTitle).parse("AC-DC-Highway to Hell.cdg");
        assert_eq!(result.artist, "AC-DC");
        assert_eq!(result.title, "Highway to Hell");
    }

    #[test]
    fn test_abbreviation_artist_zz_top() {
        let result = parser(FileNameType::ArtistTitle).parse("ZZ Top-La Grange.cdg");
        assert_eq!(result.artist, "ZZ Top");
        assert_eq!(result.title, "La Grange");
    }

    // ── ZIP path parsing ──────────────────────────────────────────

    #[test]
    fn test_zip_path_artist_fallback() {
        let result = parser(FileNameType::ArtistTitle)
            .parse_zip_path("Language/Elvis/My Way.kar");
        // "My Way.kar" doesn't have " - ", falls to legacy with single part
        // so artist will be empty from parse(), then derived from directory
        assert_eq!(result.artist, "Elvis");
        assert_eq!(result.title, "My Way");
    }

    #[test]
    fn test_zip_path_direct_artist() {
        // "Elvis - My Way.kar" has " - " so both are parsed directly
        let result = parser(FileNameType::ArtistTitle)
            .parse_zip_path("Language/Elvis - My Way.kar");
        assert_eq!(result.artist, "Elvis");
        assert_eq!(result.title, "My Way");
    }

    #[test]
    fn test_is_abbreviation_part() {
        assert!(is_abbreviation_part("AC"));
        assert!(is_abbreviation_part("DC"));
        assert!(is_abbreviation_part("DJ"));
        assert!(is_abbreviation_part("MC"));
        assert!(is_abbreviation_part("ZZ"));
        assert!(!is_abbreviation_part(""));
        assert!(is_abbreviation_part("A")); // Python: len≤3, isupper(), has alpha
        assert!(!is_abbreviation_part("abcd"));
        assert!(!is_abbreviation_part("AbC"));
        assert!(!is_abbreviation_part("123"));
    }
}
