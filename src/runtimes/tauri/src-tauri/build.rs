use std::path::Path;

fn main() {
    // The "backend/**" resource glob in tauri.conf.json must match at least one
    // file or tauri_build::build() will fail.  The real backend tree is created
    // by the `beforeBuildCommand` (which only runs via the Tauri CLI).  When
    // building with plain `cargo test` / `cargo check` (e.g. in CI) the
    // directory may be empty, so we create a small placeholder to satisfy the
    // glob.  The file must NOT start with '.' because glob patterns skip hidden
    // files.
    let placeholder = Path::new("backend").join("PLACEHOLDER");
    let has_real_files = Path::new("backend")
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
        std::fs::create_dir_all("backend").ok();
        std::fs::write(&placeholder, "# placeholder so backend/** glob matches during cargo test\n").ok();
    }

    tauri_build::build()
}
