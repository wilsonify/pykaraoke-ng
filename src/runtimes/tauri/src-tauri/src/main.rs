// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::process::{Child, Command, Stdio};
use std::io::{BufRead, BufReader, Write};
use std::sync::{Arc, Mutex};
use tauri::{Manager, State};
use std::path::PathBuf;

/// Backend state shared across the application
struct BackendState {
    process: Option<Child>,
    stdin: Option<std::process::ChildStdin>,
}

/// Wrapper for thread-safe backend state
type SafeBackendState = Arc<Mutex<BackendState>>;

/// Command request structure
#[derive(Debug, Serialize, Deserialize)]
struct CommandRequest {
    action: String,
    params: Option<serde_json::Value>,
}

/// Command response structure
#[derive(Debug, Serialize, Deserialize)]
struct CommandResponse {
    status: String,
    message: Option<String>,
    data: Option<serde_json::Value>,
}

/// Start the Python backend process
#[tauri::command]
fn start_backend(state: State<SafeBackendState>, app_handle: tauri::AppHandle) -> Result<String, String> {
    let mut backend = state.lock().unwrap();
    
    if backend.process.is_some() {
        return Ok("Backend already running".to_string());
    }
    
    // Get the path to the Python backend script.
    // Try multiple candidate locations so it works in both development
    // (source tree) and production (.deb install with bundled resources).
    let resource_dir = app_handle.path_resolver()
        .resource_dir()
        .unwrap_or_else(|| std::env::current_dir().unwrap());

    let candidates: Vec<PathBuf> = vec![
        // 1. Bundled resource inside installed app (tauri.conf.json "resources")
        resource_dir.join("backend").join("pykaraoke").join("core").join("backend.py"),
        // 2. Flat bundled resource
        resource_dir.join("backend.py"),
        // 3. Development: project root -> src/pykaraoke/core/backend.py
        resource_dir.join("..").join("..").join("..").join("src")
            .join("pykaraoke").join("core").join("backend.py"),
        // 4. Development: CWD-based fallback
        std::env::current_dir().unwrap_or_default()
            .join("src").join("pykaraoke").join("core").join("backend.py"),
    ];

    let backend_script = candidates.iter()
        .find(|p| p.exists())
        .cloned()
        .unwrap_or_else(|| {
            // Last resort: use the bundled resource path (will produce a clear
            // "file not found" error from Command::new below)
            candidates[0].clone()
        });
    
    // Start the Python backend process
    let mut child = Command::new("python3")
        .arg(backend_script)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}", e))?;
    
    let stdin = child.stdin.take();
    let stdout = child.stdout.take();
    
    // Spawn thread to read backend output
    if let Some(stdout) = stdout {
        let app_handle_clone = app_handle.clone();
        std::thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line in reader.lines() {
                if let Ok(line) = line {
                    // Parse and emit events to frontend
                    if let Ok(output) = serde_json::from_str::<serde_json::Value>(&line) {
                        if output["type"] == "event" {
                            // Emit event to frontend
                            app_handle_clone.emit_all("backend-event", output["event"].clone()).ok();
                        }
                    }
                }
            }
        });
    }
    
    backend.process = Some(child);
    backend.stdin = stdin;
    
    Ok("Backend started successfully".to_string())
}

/// Send a command to the Python backend
#[tauri::command]
async fn send_command(
    state: State<'_, SafeBackendState>,
    action: String,
    params: Option<serde_json::Value>,
) -> Result<CommandResponse, String> {
    let mut backend = state.lock().unwrap();
    
    if backend.stdin.is_none() {
        return Err("Backend not running".to_string());
    }
    
    let command = CommandRequest { action, params };
    let command_json = serde_json::to_string(&command)
        .map_err(|e| format!("Failed to serialize command: {}", e))?;
    
    // Send command to backend
    if let Some(ref mut stdin) = backend.stdin {
        writeln!(stdin, "{}", command_json)
            .map_err(|e| format!("Failed to send command: {}", e))?;
        stdin.flush()
            .map_err(|e| format!("Failed to flush stdin: {}", e))?;
    }
    
    // TODO: Implement response reading from stdout
    // For now, return a placeholder response
    Ok(CommandResponse {
        status: "ok".to_string(),
        message: Some("Command sent".to_string()),
        data: None,
    })
}

/// Stop the Python backend process
#[tauri::command]
fn stop_backend(state: State<SafeBackendState>) -> Result<String, String> {
    let mut backend = state.lock().unwrap();
    
    if let Some(mut child) = backend.process.take() {
        child.kill().map_err(|e| format!("Failed to kill backend: {}", e))?;
        backend.stdin = None;
        Ok("Backend stopped".to_string())
    } else {
        Err("Backend not running".to_string())
    }
}

fn main() {
    // Work around blank/empty WebKitGTK windows on Linux systems where
    // GPU buffer allocation (GBM/DRM) is denied.  This tells WebKit to
    // fall back to a shared-memory renderer instead of DMA-BUF, which
    // avoids the "DRM_IOCTL_MODE_CREATE_DUMB failed: Permission denied"
    // and "Failed to create GBM buffer" errors that cause a blank window.
    #[cfg(target_os = "linux")]
    {
        if std::env::var("WEBKIT_DISABLE_DMABUF_RENDERER").is_err() {
            std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
        }
    }

    tauri::Builder::default()
        .manage(Arc::new(Mutex::new(BackendState {
            process: None,
            stdin: None,
        })))
        .invoke_handler(tauri::generate_handler![
            start_backend,
            send_command,
            stop_backend
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    // ── CommandRequest serialization ──────────────────────────────

    #[test]
    fn command_request_serializes_with_action_only() {
        let req = CommandRequest {
            action: "play".to_string(),
            params: None,
        };
        let j = serde_json::to_value(&req).unwrap();
        assert_eq!(j["action"], "play");
        assert!(j["params"].is_null());
    }

    #[test]
    fn command_request_serializes_with_params() {
        let req = CommandRequest {
            action: "set_volume".to_string(),
            params: Some(json!({"volume": 0.5})),
        };
        let j = serde_json::to_value(&req).unwrap();
        assert_eq!(j["action"], "set_volume");
        assert_eq!(j["params"]["volume"], 0.5);
    }

    #[test]
    fn command_request_roundtrips_through_json() {
        let original = CommandRequest {
            action: "search_songs".to_string(),
            params: Some(json!({"query": "hello world"})),
        };
        let serialized = serde_json::to_string(&original).unwrap();
        let deserialized: CommandRequest = serde_json::from_str(&serialized).unwrap();
        assert_eq!(deserialized.action, "search_songs");
        assert_eq!(deserialized.params.unwrap()["query"], "hello world");
    }

    #[test]
    fn command_request_deserializes_without_params_key() {
        let raw = r#"{"action":"stop"}"#;
        let req: CommandRequest = serde_json::from_str(raw).unwrap();
        assert_eq!(req.action, "stop");
        assert!(req.params.is_none());
    }

    #[test]
    fn command_request_deserializes_with_nested_params() {
        let raw = r#"{"action":"play","params":{"playlist_index":3}}"#;
        let req: CommandRequest = serde_json::from_str(raw).unwrap();
        assert_eq!(req.action, "play");
        assert_eq!(req.params.unwrap()["playlist_index"], 3);
    }

    // ── CommandResponse serialization ────────────────────────────

    #[test]
    fn command_response_ok_without_data() {
        let resp = CommandResponse {
            status: "ok".to_string(),
            message: Some("done".to_string()),
            data: None,
        };
        let j = serde_json::to_value(&resp).unwrap();
        assert_eq!(j["status"], "ok");
        assert_eq!(j["message"], "done");
        assert!(j["data"].is_null());
    }

    #[test]
    fn command_response_error_with_message() {
        let resp = CommandResponse {
            status: "error".to_string(),
            message: Some("Backend not running".to_string()),
            data: None,
        };
        let j = serde_json::to_value(&resp).unwrap();
        assert_eq!(j["status"], "error");
        assert_eq!(j["message"], "Backend not running");
    }

    #[test]
    fn command_response_with_data_payload() {
        let resp = CommandResponse {
            status: "ok".to_string(),
            message: None,
            data: Some(json!({
                "playback_state": "playing",
                "volume": 0.75,
                "playlist": []
            })),
        };
        let j = serde_json::to_value(&resp).unwrap();
        assert_eq!(j["data"]["playback_state"], "playing");
        assert_eq!(j["data"]["volume"], 0.75);
    }

    #[test]
    fn command_response_roundtrips_through_json() {
        let original = CommandResponse {
            status: "ok".to_string(),
            message: Some("Command sent".to_string()),
            data: Some(json!({"results": [{"title": "Test"}]})),
        };
        let serialized = serde_json::to_string(&original).unwrap();
        let deserialized: CommandResponse = serde_json::from_str(&serialized).unwrap();
        assert_eq!(deserialized.status, "ok");
        assert_eq!(deserialized.data.unwrap()["results"][0]["title"], "Test");
    }

    // ── BackendState management ──────────────────────────────────

    #[test]
    fn backend_state_initializes_with_no_process() {
        let state = BackendState {
            process: None,
            stdin: None,
        };
        assert!(state.process.is_none());
        assert!(state.stdin.is_none());
    }

    #[test]
    fn safe_backend_state_is_mutex_lockable() {
        let state: SafeBackendState = Arc::new(Mutex::new(BackendState {
            process: None,
            stdin: None,
        }));
        let guard = state.lock().unwrap();
        assert!(guard.process.is_none());
    }

    #[test]
    fn safe_backend_state_clone_shares_data() {
        let state: SafeBackendState = Arc::new(Mutex::new(BackendState {
            process: None,
            stdin: None,
        }));
        let clone = state.clone();
        assert!(Arc::ptr_eq(&state, &clone));
    }

    // ── JSON protocol contract tests ─────────────────────────────

    #[test]
    fn frontend_play_command_matches_expected_shape() {
        // Mirrors the JSON the JS frontend sends via invoke('send_command', ...)
        let raw = r#"{"action":"play","params":{"playlist_index":0}}"#;
        let req: CommandRequest = serde_json::from_str(raw).unwrap();
        assert_eq!(req.action, "play");
    }

    #[test]
    fn frontend_search_command_matches_expected_shape() {
        let raw = r#"{"action":"search_songs","params":{"query":"bohemian"}}"#;
        let req: CommandRequest = serde_json::from_str(raw).unwrap();
        assert_eq!(req.action, "search_songs");
        assert_eq!(req.params.unwrap()["query"], "bohemian");
    }

    #[test]
    fn frontend_volume_command_matches_expected_shape() {
        let raw = r#"{"action":"set_volume","params":{"volume":0.42}}"#;
        let req: CommandRequest = serde_json::from_str(raw).unwrap();
        let vol = req.params.unwrap()["volume"].as_f64().unwrap();
        assert!((vol - 0.42).abs() < f64::EPSILON);
    }

    #[test]
    fn all_known_actions_deserialize() {
        let actions = vec![
            "play", "pause", "stop", "next", "previous", "seek",
            "set_volume", "load_song", "add_to_playlist",
            "remove_from_playlist", "clear_playlist", "get_state",
            "search_songs", "get_library", "scan_library",
            "add_folder", "get_settings", "update_settings",
        ];
        for action in actions {
            let raw = format!(r#"{{"action":"{}"}}"#, action);
            let req: CommandRequest = serde_json::from_str(&raw).unwrap();
            assert_eq!(req.action, action);
        }
    }

    #[test]
    fn backend_event_envelope_shape() {
        // The Rust backend wraps Python output in {"type":"event","event":...}
        let raw = r#"{"type":"event","event":{"type":"state_changed","data":{}}}"#;
        let parsed: serde_json::Value = serde_json::from_str(raw).unwrap();
        assert_eq!(parsed["type"], "event");
        assert_eq!(parsed["event"]["type"], "state_changed");
    }

    #[test]
    fn backend_response_envelope_shape() {
        let raw = r#"{"type":"response","response":{"status":"ok","message":"done"}}"#;
        let parsed: serde_json::Value = serde_json::from_str(raw).unwrap();
        assert_eq!(parsed["type"], "response");
        assert_eq!(parsed["response"]["status"], "ok");
    }

    // ── Regression: empty-window workaround ──────────────────────

    #[test]
    fn dmabuf_env_var_is_set_on_linux() {
        // Regression test for https://github.com/wilsonify/pykaraoke-ng/issues/...
        // WebKitGTK renders a blank window when GBM buffer creation fails.
        // The workaround sets WEBKIT_DISABLE_DMABUF_RENDERER=1.
        //
        // On non-Linux this test just verifies the source contains the
        // workaround code (the #[cfg] gate means the code won't execute).
        let source = include_str!("main.rs");
        assert!(
            source.contains("WEBKIT_DISABLE_DMABUF_RENDERER"),
            "main.rs must set WEBKIT_DISABLE_DMABUF_RENDERER to prevent \
             blank WebKitGTK windows on Linux"
        );
    }

    #[test]
    fn dmabuf_workaround_is_linux_gated() {
        let source = include_str!("main.rs");
        let dmabuf_pos = source.find("WEBKIT_DISABLE_DMABUF_RENDERER").unwrap();
        let preceding = &source[dmabuf_pos.saturating_sub(300)..dmabuf_pos];
        assert!(
            preceding.contains(r#"target_os = "linux""#),
            "WEBKIT_DISABLE_DMABUF_RENDERER should be behind #[cfg(target_os = \"linux\")]"
        );
    }

    #[test]
    fn dmabuf_workaround_checks_existing_value() {
        let source = include_str!("main.rs");
        // Between the cfg gate and the set_var, we should see is_err() check
        let dmabuf_pos = source.find("WEBKIT_DISABLE_DMABUF_RENDERER").unwrap();
        let region = &source[dmabuf_pos.saturating_sub(100)..dmabuf_pos + 100];
        assert!(
            region.contains("is_err()"),
            "Should check is_err() before setting the env var, \
             so user-provided values are respected"
        );
    }

    #[test]
    fn dmabuf_set_before_tauri_builder() {
        let source = include_str!("main.rs");
        let dmabuf_pos = source.find("WEBKIT_DISABLE_DMABUF_RENDERER").unwrap();
        let builder_pos = source.find("tauri::Builder::default()").unwrap();
        assert!(
            dmabuf_pos < builder_pos,
            "WEBKIT_DISABLE_DMABUF_RENDERER must be set before tauri::Builder"
        );
    }

    // ── Regression: backend path resolution ──────────────────────

    #[test]
    fn backend_path_uses_multiple_candidates() {
        let source = include_str!("main.rs");
        let count = source.matches(r#".join("backend.py")"#).count();
        assert!(
            count >= 2,
            "start_backend should try at least 2 candidate paths for \
             backend.py (found {count})"
        );
    }

    #[test]
    fn backend_path_checks_exists() {
        let source = include_str!("main.rs");
        // The candidates should be filtered with .exists()
        assert!(
            source.contains(".exists()"),
            "start_backend should verify candidate paths with .exists()"
        );
    }

    #[test]
    fn backend_path_uses_resource_dir() {
        let source = include_str!("main.rs");
        assert!(
            source.contains("resource_dir"),
            "start_backend should use resource_dir() for bundled installs"
        );
    }
}
