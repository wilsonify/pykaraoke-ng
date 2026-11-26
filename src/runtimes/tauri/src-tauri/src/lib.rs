//! PyKaraoke NG — thin Tauri shell.
//!
//! The whole application is the static `web/` frontend (HTML/CSS/JS +
//! PyScript/Pyodide).  Rust exists only for the three things a browser
//! cannot do: picking a folder, listing it recursively, and reading
//! files by path (so the song library survives restarts).  Playback,
//! decoding, search and rendering all happen in the webview.

use serde::Serialize;
use std::path::{Path, PathBuf};

#[derive(Serialize)]
struct FileEntry {
    name: String,
    path: String,
    size: u64,
}

/// Open the native folder dialog and return the chosen path, if any.
#[tauri::command]
fn pick_folder() -> Option<String> {
    rfd::FileDialog::new()
        .set_title("Add karaoke folder")
        .pick_folder()
        .map(|p| p.to_string_lossy().into_owned())
}

/// Recursively list a folder as flat file entries with absolute paths.
#[tauri::command]
fn list_folder(path: String) -> Result<Vec<FileEntry>, String> {
    let root = Path::new(&path);
    if !root.is_dir() {
        return Err(format!("not a directory: {path}"));
    }
    // An unreadable root is a real failure the operator must see; trouble
    // deeper in the tree is tolerated by `walk`.
    std::fs::read_dir(root).map_err(|e| format!("read_dir {path}: {e}"))?;
    let mut entries = Vec::new();
    let mut seen = Vec::new();
    walk(root, &mut entries, &mut seen);
    Ok(entries)
}

/// Collect the files under *dir*, visiting each directory at most once.
///
/// A library can contain a symlink that points back up the tree, or a folder
/// the current user cannot read. Neither may abort the whole listing: cycles
/// are cut by canonical path, and an unreadable subfolder contributes nothing
/// while its siblings still appear.
fn walk(dir: &Path, out: &mut Vec<FileEntry>, seen: &mut Vec<PathBuf>) {
    let canonical = match dir.canonicalize() {
        Ok(path) => path,
        Err(_) => return,
    };
    if seen.iter().any(|seen_path| *seen_path == canonical) {
        return;
    }
    seen.push(canonical);
    let read = match std::fs::read_dir(dir) {
        Ok(read) => read,
        Err(_) => return,
    };
    for item in read.flatten() {
        let entry_path = item.path();
        // `is_dir()` follows symlinks, so a linked folder is walked (once).
        if entry_path.is_dir() {
            walk(&entry_path, out, seen);
        } else {
            // A file whose metadata cannot be read is still listed, with an
            // unknown size, rather than being dropped from the library.
            let size = std::fs::metadata(&entry_path).map(|m| m.len()).unwrap_or(0);
            out.push(FileEntry {
                name: item.file_name().to_string_lossy().into_owned(),
                path: entry_path.to_string_lossy().into_owned(),
                size,
            });
        }
    }
}

/// Read a file's bytes (raw IPC transfer; the webview gets an ArrayBuffer).
#[tauri::command]
fn read_file(path: String) -> Result<tauri::ipc::Response, String> {
    let bytes = std::fs::read(&path).map_err(|e| format!("read {path}: {e}"))?;
    Ok(tauri::ipc::Response::new(bytes))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![pick_folder, list_folder, read_file])
        .run(tauri::generate_context!())
        .expect("error while running PyKaraoke NG");
}