//! PyKaraoke NG — thin Tauri shell.
//!
//! The whole application is the static `web/` frontend (HTML/CSS/JS +
//! PyScript/Pyodide).  Rust exists only for the three things a browser
//! cannot do: picking a folder, listing it recursively, and reading
//! files by path (so the song library survives restarts).  Playback,
//! decoding, search and rendering all happen in the webview.

use serde::Serialize;
use std::path::Path;

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
    let mut entries = Vec::new();
    walk(root, &mut entries)?;
    Ok(entries)
}

fn walk(dir: &Path, out: &mut Vec<FileEntry>) -> Result<(), String> {
    let read = std::fs::read_dir(dir).map_err(|e| format!("read_dir {}: {e}", dir.display()))?;
    for item in read {
        let item = item.map_err(|e| e.to_string())?;
        let entry_path = item.path();
        let file_type = item.file_type().map_err(|e| e.to_string())?;
        if file_type.is_dir() {
            walk(&entry_path, out)?;
        } else {
            let size = std::fs::metadata(&entry_path).map(|m| m.len()).unwrap_or(0);
            out.push(FileEntry {
                name: item.file_name().to_string_lossy().into_owned(),
                path: entry_path.to_string_lossy().into_owned(),
                size,
            });
        }
    }
    Ok(())
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