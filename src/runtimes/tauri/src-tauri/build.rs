// Build script for the PyKaraoke NG Tauri desktop application.
// The Rust native backend (pykaraoke-engine) is a workspace member and
// is compiled alongside this crate. The beforeBuildCommand is intentionally
// empty because there is no Python backend to stage.
 
fn main() {
    tauri_build::build()
}
