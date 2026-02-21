// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::process::{Child, Command, Stdio};
use std::io::{BufRead, BufReader, Write};
use std::sync::{Arc, Mutex};
use tauri::{Manager, State};

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
    
    // Get the path to the Python backend script
    let resource_path = app_handle.path_resolver()
        .resource_dir()
        .unwrap_or_else(|| std::env::current_dir().unwrap());
    
    // Navigate to the src/pykaraoke/core directory from project root
    let backend_script = resource_path
        .join("..")
        .join("..")
        .join("..")
        .join("src")
        .join("pykaraoke")
        .join("core")
        .join("backend.py");
    
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
}
