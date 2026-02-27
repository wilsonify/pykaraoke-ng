use std::path::PathBuf;

fn main() {
    // The "backend/**" resource glob in tauri.conf.json must match at least one
    // file or tauri_build::build() will fail.  The real backend tree is created
    // by the `beforeBuildCommand` (which only runs via the Tauri CLI).  When
    // building with plain `cargo test` / `cargo check` (e.g. in CI) the
    // directory may be empty, so we create a minimal placeholder tree that
    // satisfies the glob.  The path must include a subdirectory because Tauri's
    // glob implementation requires `**` to match at least one directory level.
    let manifest_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let backend_dir = manifest_dir.join("backend");
    let placeholder_dir = backend_dir.join("pykaraoke");
    let placeholder = placeholder_dir.join("PLACEHOLDER");

    let has_real_files = backend_dir
        .read_dir()
        .ok()
        .and_then(|mut d| d.find(|e| {
            e.as_ref()
                .map(|e| {
                    let name = e.file_name();
                    let s = name.to_string_lossy();
                    !s.starts_with('.') && s != "PLACEHOLDER"
                })
                .unwrap_or(false)
        }))
        .is_some();

    if !has_real_files {
        std::fs::create_dir_all(&placeholder_dir).ok();
        std::fs::write(&placeholder, "# placeholder so backend/** glob matches during cargo test\n").ok();
    }

    tauri_build::build()
}
