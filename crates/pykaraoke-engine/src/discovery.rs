//! Song discovery — file scanning and extension filtering.
//!
//! Mirrors the scanning logic from `SongDB.file_scan()`, `folder_scan()`,
//! and related methods in `src/pykaraoke/core/database.py`.

use crate::song::{SongStruct, SupportedExtensions};
use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};

/// Holds results from a scan operation.
#[derive(Debug, Clone)]
pub struct ScanResults {
    pub songs: Vec<SongStruct>,
    pub errors: Vec<String>,
}

/// Scans directories for karaoke files.
#[derive(Debug, Clone)]
pub struct SongScanner {
    pub extensions: SupportedExtensions,
    pub look_inside_zips: bool,
    pub read_titles_txt: bool,
    /// Set of already-scanned paths (prevents duplicates)
    scanned_paths: HashSet<PathBuf>,
}

impl Default for SongScanner {
    fn default() -> Self {
        Self {
            extensions: SupportedExtensions::default(),
            look_inside_zips: true,
            read_titles_txt: true,
            scanned_paths: HashSet::new(),
        }
    }
}

impl SongScanner {
    pub fn new() -> Self {
        Self::default()
    }

    /// Scan a list of root directories for karaoke files.
    pub fn scan_directories(&mut self, roots: &[String]) -> ScanResults {
        let mut songs = Vec::new();
        let mut errors = Vec::new();
        self.scanned_paths.clear();

        for root in roots {
            let path = Path::new(root);
            if !path.exists() {
                errors.push(format!("Directory not found: {}", root));
                continue;
            }
            self.scan_file(path, &mut songs, &mut errors);
        }

        ScanResults { songs, errors }
    }

    /// Scan a single file or directory entry.
    fn scan_file(&mut self, path: &Path, songs: &mut Vec<SongStruct>, errors: &mut Vec<String>) {
        let canonical = match fs::canonicalize(path) {
            Ok(p) => p,
            Err(e) => {
                errors.push(format!("Cannot access {}: {}", path.display(), e));
                return;
            }
        };

        if !self.scanned_paths.insert(canonical.clone()) {
            return; // Already scanned
        }

        if path.is_dir() {
            self.scan_folder(path, songs, errors);
        } else if let Some(ext) = path.extension() {
            let ext_str = format!(".{}", ext.to_string_lossy().to_lowercase());
            if self.extensions.is_valid(&ext_str) {
                match self.try_add_song(path) {
                    Some(song) => songs.push(song),
                    None => errors.push(format!("Failed to process: {}", path.display())),
                }
            } else if ext_str == ".zip" && self.look_inside_zips {
                self.scan_zip_file(path, songs, errors);
            }
        }
    }

    /// Recursively scan a directory.
    fn scan_folder(&mut self, dir: &Path, songs: &mut Vec<SongStruct>, errors: &mut Vec<String>) {
        let entries = match fs::read_dir(dir) {
            Ok(entries) => entries,
            Err(e) => {
                errors.push(format!("Cannot read directory {}: {}", dir.display(), e));
                return;
            }
        };

        for entry in entries {
            let entry = match entry {
                Ok(e) => e,
                Err(_) => continue,
            };

            let path = entry.path();
            let file_name = path
                .file_name()
                .map(|s| s.to_string_lossy().to_string())
                .unwrap_or_default();

            // Skip common VCS directories
            if path.is_dir() {
                if file_name == ".svn" || file_name == "CVS" {
                    continue;
                }
            }

            self.scan_file(&path, songs, errors);
        }
    }

    /// Try to add a single karaoke file as a song.
    fn try_add_song(&self, path: &Path) -> Option<SongStruct> {
        let filepath = path.to_string_lossy().to_string();
        let mut song = SongStruct::from_filepath(&filepath);

        // Determine the format type
        match song.extension.as_str() {
            ".cdg" => {
                // CD+G files often have a companion audio file
                song.audio_filepath = self.find_audio_for_cdg(path);
            }
            ".kar" | ".mid" => {
                // KAR/MIDI files are self-contained
            }
            _ => {
                // MPEG/other formats are self-contained
            }
        }

        Some(song)
    }

    /// For a CD+G file, look for a companion .mp3 or .ogg file.
    fn find_audio_for_cdg(&self, cdg_path: &Path) -> Option<String> {
        let stem = cdg_path.file_stem()?;
        let parent = cdg_path.parent()?;

        for ext in &[".mp3", ".ogg"] {
            let audio_path = parent.join(format!("{}{}", stem.to_string_lossy(), ext));
            if audio_path.exists() {
                return Some(audio_path.to_string_lossy().to_string());
            }
        }

        None
    }

    /// Scan a ZIP file for karaoke entries.
    fn scan_zip_file(&self, zip_path: &Path, songs: &mut Vec<SongStruct>, errors: &mut Vec<String>) {
        let filepath = zip_path.to_string_lossy().to_string();

        let file = match fs::File::open(zip_path) {
            Ok(f) => f,
            Err(e) => {
                errors.push(format!("Cannot open ZIP {}: {}", filepath, e));
                return;
            }
        };

        // Read ZIP central directory
        let zip_data = match unsafe { zip_safe_read(&file) } {
            Ok(data) => data,
            Err(e) => {
                errors.push(format!("Cannot read ZIP {}: {}", filepath, e));
                return;
            }
        };

        for stored_name in &zip_data.entries {
            let ext = Path::new(stored_name)
                .extension()
                .map(|s| format!(".{}", s.to_string_lossy().to_lowercase()))
                .unwrap_or_default();

            if self.extensions.is_valid(&ext) {
                let mut song = SongStruct::from_filepath(stored_name);
                song.zip_stored_name = Some(stored_name.clone());
                songs.push(song);
            }
        }
    }
}

/// Minimal ZIP entry information.
struct ZipData {
    entries: Vec<String>,
}

/// Read ZIP entries safely (no external crate dependency yet).
/// This is a placeholder that reads the central directory.
/// In production, use the `zip` crate.
unsafe fn zip_safe_read(_file: &fs::File) -> Result<ZipData, String> {
    // Placeholder: will be replaced with proper ZIP parsing via the `zip` crate
    Ok(ZipData {
        entries: Vec::new(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extension_filtering() {
        let exts = SupportedExtensions::default();
        assert!(exts.is_valid(".cdg"));
        assert!(exts.is_valid(".kar"));
        assert!(exts.is_valid(".mid"));
        assert!(exts.is_valid(".mpg"));
        assert!(exts.is_valid(".mpeg"));
        assert!(exts.is_valid(".mp3"));
        assert!(exts.is_valid(".ogg"));
        assert!(!exts.is_valid(".txt"));
        assert!(!exts.is_valid(".jpg"));
        assert!(!exts.is_valid(""));
    }

    #[test]
    fn test_all_extensions_non_empty() {
        let exts = SupportedExtensions::default();
        let all = exts.all();
        assert!(!all.is_empty());
        assert!(all.contains(&".cdg"));
        assert!(all.contains(&".kar"));
    }

    #[test]
    fn test_scan_nonexistent_directory() {
        let mut scanner = SongScanner::new();
        let results = scanner.scan_directories(&["/nonexistent/path/12345".to_string()]);
        assert!(results.songs.is_empty());
        assert!(!results.errors.is_empty());
        assert!(results.errors[0].contains("not found"));
    }

    #[test]
    fn test_cdg_audio_path() {
        // Create a temp dir with a .cdg and .mp3 pair
        let dir = std::env::temp_dir().join("pykaraoke_test_cdg");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();

        let cdg_path = dir.join("test_song.cdg");
        let mp3_path = dir.join("test_song.mp3");

        fs::write(&cdg_path, b"cdg data").unwrap();
        fs::write(&mp3_path, b"mp3 data").unwrap();

        let scanner = SongScanner::new();
        let audio = scanner.find_audio_for_cdg(&cdg_path);
        assert!(audio.is_some());
        assert!(audio.unwrap().ends_with("test_song.mp3"));

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_cdg_no_audio_path() {
        let dir = std::env::temp_dir().join("pykaraoke_test_cdg_no_audio");
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();

        let cdg_path = dir.join("test_song.cdg");
        fs::write(&cdg_path, b"cdg data").unwrap();

        let scanner = SongScanner::new();
        let audio = scanner.find_audio_for_cdg(&cdg_path);
        assert!(audio.is_none());

        let _ = fs::remove_dir_all(&dir);
    }
}
