// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use pykaraoke_engine::backend::{Backend, CommandRequest, CommandResponse};
use pykaraoke_engine::database::Persistence;
use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use std::path::PathBuf;
use tauri::{Manager, State};

/// The Rust-native backend instance, thread-safe.
struct AppBackend {
    backend: Mutex<Option<Backend>>,
}

/// Command response structure (matches what the frontend expects).
#[derive(Debug, Serialize, Deserialize)]
struct CommandResponseWrapper {
    status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    message: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    data: Option<serde_json::Value>,
}

impl From<CommandResponse> for CommandResponseWrapper {
    fn from(r: CommandResponse) -> Self {
        CommandResponseWrapper {
            status: r.status,
            message: r.message,
            data: r.data,
        }
    }
}

/// Resolve the data directory for settings/song database.
fn resolve_data_dir(app_handle: &tauri::AppHandle) -> PathBuf {
    // Use Tauri's app data directory, falling back to ~/.pykaraoke
    app_handle
        .path_resolver()
        .app_data_dir()
        .unwrap_or_else(|| {
            dirs::data_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join(".pykaraoke")
        })
}

/// Start the native Rust backend.
#[tauri::command]
fn start_backend(state: State<AppBackend>, app_handle: tauri::AppHandle) -> Result<String, String> {
    let mut backend_guard = state.backend.lock().map_err(|e| format!("Lock error: {}", e))?;

    if backend_guard.is_some() {
        return Ok("Backend already running".to_string());
    }

    let data_dir = resolve_data_dir(&app_handle);
    let persistence = Persistence::new(Some(data_dir));

    // Load existing settings (if any)
    let mut pers = persistence.clone();
    pers.load_settings().ok();
    pers.load_database().ok();

    let backend = Backend::new(pers);
    *backend_guard = Some(backend);

    Ok("Native Rust backend started".to_string())
}

/// Send a command to the Rust backend engine.
#[tauri::command]
async fn send_command(
    state: State<'_, AppBackend>,
    action: String,
    params: Option<serde_json::Value>,
) -> Result<CommandResponseWrapper, String> {
    let mut backend_guard = state.backend.lock().map_err(|e| format!("Lock error: {}", e))?;

    let backend = backend_guard.as_mut().ok_or("Backend not running")?;

    let request = CommandRequest {
        action,
        params: params.unwrap_or(serde_json::Value::Null),
    };

    let response = backend.handle_command(request);
    Ok(response.into())
}

/// Stop the backend (persist state before shutdown).
#[tauri::command]
fn stop_backend(state: State<AppBackend>) -> Result<String, String> {
    let mut backend_guard = state.backend.lock().map_err(|e| format!("Lock error: {}", e))?;

    if let Some(backend) = backend_guard.take() {
        // Persist state on shutdown
        backend.persistence.save_settings().ok();
        backend.persistence.save_database().ok();
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
        // Suppress "Couldn't connect to accessibility bus" warnings from
        // WebKitGTK / at-spi2 when the D-Bus a11y socket is unavailable.
        if std::env::var("NO_AT_BRIDGE").is_err() {
            std::env::set_var("NO_AT_BRIDGE", "1");
        }
    }

    tauri::Builder::default()
        .manage(AppBackend {
            backend: Mutex::new(None),
        })
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

    // ── CommandRequest serialization ──────────────────────────────

    #[test]
    fn command_request_serializes_with_action_only() {
        let req = CommandRequest {
            action: "play".to_string(),
            params: serde_json::Value::Null,
        };
        let j = serde_json::to_value(&req).unwrap();
        assert_eq!(j["action"], "play");
        assert!(j["params"].is_null());
    }

    #[test]
    fn command_request_serializes_with_params() {
        let req = CommandRequest {
            action: "set_volume".to_string(),
            params: serde_json::json!({"volume": 0.5}),
        };
        let j = serde_json::to_value(&req).unwrap();
        assert_eq!(j["action"], "set_volume");
        assert_eq!(j["params"]["volume"], 0.5);
    }

    #[test]
    fn command_request_roundtrips_through_json() {
        let original = CommandRequest {
            action: "search_songs".to_string(),
            params: Some(serde_json::json!({"query": "hello world"})),
        };
        let serialized = serde_json::to_string(&original).unwrap();
        let deserialized: CommandRequest = serde_json::from_str(&serialized).unwrap();
        assert_eq!(deserialized.action, "search_songs");
        assert_eq!(deserialized.params.as_object().unwrap()["query"], "hello world");
    }

    #[test]
    fn command_request_deserializes_without_params_key() {
        let raw = r#"{"action":"stop"}"#;
        let req: CommandRequest = serde_json::from_str(raw).unwrap();
        assert_eq!(req.action, "stop");
        assert!(req.params.is_null() || req.params.as_object().map_or(true, |o| o.is_empty()));
    }

    #[test]
    fn command_request_deserializes_with_nested_params() {
        let raw = r#"{"action":"play","params":{"playlist_index":3}}"#;
        let req: CommandRequest = serde_json::from_str(raw).unwrap();
        assert_eq!(req.action, "play");
        assert_eq!(req.params["playlist_index"], 3);
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
            data: Some(serde_json::json!({
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
            data: Some(serde_json::json!({"results": [{"title": "Test"}]})),
        };
        let serialized = serde_json::to_string(&original).unwrap();
        let deserialized: CommandResponse = serde_json::from_str(&serialized).unwrap();
        assert_eq!(deserialized.status, "ok");
        assert_eq!(deserialized.data.unwrap()["results"][0]["title"], "Test");
    }

    // ── BackendState management ──────────────────────────────────

    #[test]
    fn backend_state_initializes_with_no_backend() {
        let app = AppBackend {
            backend: Mutex::new(None),
        };
        let guard = app.backend.lock().unwrap();
        assert!(guard.is_none());
    }

    // ── Backend integration ──────────────────────────────────────

    fn test_backend() -> Backend {
        let dir = std::env::temp_dir().join("pykaraoke_test_tauri_main");
        let _ = std::fs::remove_dir_all(&dir);
        let persistence = Persistence::new(Some(dir));
        Backend::new(persistence)
    }

    #[test]
    fn backend_responds_to_get_state() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "get_state".to_string(),
            params: serde_json::Value::Null,
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
        let data = resp.data.unwrap();
        assert_eq!(data["playback_state"], "idle");
        assert!(data["playlist"].is_array());
    }

    #[test]
    fn backend_handles_unknown_command() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "nonexistent_action".to_string(),
            params: serde_json::Value::Null,
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "error");
        assert!(resp.message.unwrap().contains("Unknown action"));
    }

    #[test]
    fn backend_enqueue_and_play() {
        let mut backend = test_backend();
        let req = CommandRequest {
            action: "add_to_playlist".to_string(),
            params: serde_json::json!({"filepath": "/tmp/test.kar"}),
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");

        let req = CommandRequest {
            action: "play".to_string(),
            params: serde_json::Value::Null,
        };
        let resp = backend.handle_command(req);
        assert_eq!(resp.status, "ok");
    }

    // ── JSON protocol contract tests ─────────────────────────────

    #[test]
    fn frontend_play_command_matches_expected_shape() {
        let raw = r#"{"action":"play","params":{"playlist_index":0}}"#;
        let req: CommandRequest = serde_json::from_str(raw).unwrap();
        assert_eq!(req.action, "play");
    }

    #[test]
    fn frontend_search_command_matches_expected_shape() {
        let raw = r#"{"action":"search_songs","params":{"query":"bohemian"}}"#;
        let req: CommandRequest = serde_json::from_str(raw).unwrap();
        assert_eq!(req.action, "search_songs");
        assert_eq!(req.params["query"], "bohemian");
    }

    #[test]
    fn frontend_volume_command_matches_expected_shape() {
        let raw = r#"{"action":"set_volume","params":{"volume":0.42}}"#;
        let req: CommandRequest = serde_json::from_str(raw).unwrap();
        let vol = req.params["volume"].as_f64().unwrap();
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

    // ── Regression: empty-window workaround ──────────────────────

    #[test]
    fn dmabuf_env_var_is_set_on_linux() {
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
}
