#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod tauri_event_bus;

use commands::AppEngine;
use pykaraoke_engine::Engine;
use pykaraoke_engine::EngineImpl;
use pykaraoke_engine::views::*;
use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use std::path::PathBuf;
use tauri::State;
use tauri_event_bus::TauriEventBus;

/// Command response structure (matches what the frontend expects).
#[derive(Debug, Serialize, Deserialize)]
struct CommandResponseWrapper {
    status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    message: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    data: Option<serde_json::Value>,
}

/// Resolve the data directory for settings/song database.
fn resolve_data_dir(app_handle: &tauri::AppHandle) -> PathBuf {
    app_handle
        .path_resolver()
        .app_data_dir()
        .unwrap_or_else(|| {
            dirs::data_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join(".pykaraoke")
        })
}

/// Start the native Rust engine (backward-compat).
#[tauri::command]
fn start_backend(state: State<AppEngine>, app_handle: tauri::AppHandle) -> Result<String, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;

    if let Some(engine) = guard.as_ref() {
        if engine.status() == pykaraoke_engine::EngineStatus::Running {
            return Ok("Backend already running".to_string());
        }
    }

    let data_dir = resolve_data_dir(&app_handle);
    let event_bus = TauriEventBus::new(app_handle.clone());
    let mut engine = EngineImpl::new(Some(data_dir), Box::new(event_bus));
    engine.start().map_err(|e| e.to_string())?;
    *guard = Some(engine);

    Ok("Native Rust backend started".to_string())
}

/// Send a command to the engine (backward-compat adapter).
#[tauri::command]
fn send_command(
    state: State<'_, AppEngine>,
    action: String,
    params: Option<serde_json::Value>,
) -> Result<CommandResponseWrapper, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;

    let params = params.unwrap_or(serde_json::Value::Null);

    let result = match action.as_str() {
        "play" => {
            let song_id = params.get("playlist_index").and_then(|v| v.as_u64());
            engine.play(song_id.map(SongId))
                .map(|_| CommandResponseWrapper { status: "ok".to_string(), message: None, data: None })
                .unwrap_or_else(|e| CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None })
        }
        "pause" => {
            engine.pause()
                .map(|_| CommandResponseWrapper { status: "ok".to_string(), message: None, data: None })
                .unwrap_or_else(|e| CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None })
        }
        "stop" => {
            engine.stop_playback()
                .map(|_| CommandResponseWrapper { status: "ok".to_string(), message: None, data: None })
                .unwrap_or_else(|e| CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None })
        }
        "next" => {
            engine.next()
                .map(|_| CommandResponseWrapper { status: "ok".to_string(), message: None, data: None })
                .unwrap_or_else(|e| CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None })
        }
        "previous" => {
            engine.previous()
                .map(|_| CommandResponseWrapper { status: "ok".to_string(), message: None, data: None })
                .unwrap_or_else(|e| CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None })
        }
        "seek" => {
            let pos = params.get("position_ms").and_then(|v| v.as_u64()).unwrap_or(0);
            engine.seek(pos)
                .map(|_| CommandResponseWrapper { status: "ok".to_string(), message: None, data: None })
                .unwrap_or_else(|e| CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None })
        }
        "set_volume" => {
            let vol = params.get("volume").and_then(|v| v.as_f64()).unwrap_or(0.8);
            engine.set_volume(vol)
                .map(|_| CommandResponseWrapper { status: "ok".to_string(), message: None, data: None })
                .unwrap_or_else(|e| CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None })
        }
        "add_to_playlist" => {
            let filepath = params.get("filepath").and_then(|v| v.as_str()).unwrap_or("");
            engine.enqueue(filepath)
                .map(|_| CommandResponseWrapper { status: "ok".to_string(), message: None, data: None })
                .unwrap_or_else(|e| CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None })
        }
        "remove_from_playlist" => {
            let idx = params.get("index").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
            engine.remove_from_queue(idx)
                .map(|_| CommandResponseWrapper { status: "ok".to_string(), message: None, data: None })
                .unwrap_or_else(|e| CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None })
        }
        "clear_playlist" => {
            engine.clear_queue()
                .map(|_| CommandResponseWrapper { status: "ok".to_string(), message: None, data: None })
                .unwrap_or_else(|e| CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None })
        }
        "get_state" => {
            let state_val = serde_json::json!({
                "playback_state": serde_json::to_value(engine.status()).unwrap_or_default(),
                "volume": 0.8,
                "playlist": [],
                "playlist_index": null,
            });
            CommandResponseWrapper { status: "ok".to_string(), message: None, data: Some(state_val) }
        }
        "search_songs" => {
            let query = params.get("query").and_then(|v| v.as_str()).unwrap_or("");
            let results = engine.search(query);
            let state_val = serde_json::json!({
                "results": results.results,
                "count": results.total_count,
            });
            CommandResponseWrapper { status: "ok".to_string(), message: None, data: Some(state_val) }
        }
        "get_library" => {
            CommandResponseWrapper { status: "ok".to_string(), message: None, data: Some(serde_json::json!({"songs": [], "count": 0})) }
        }
        "scan_library" => {
            match engine.scan_library() {
                Ok(progress) => {
                    let data = serde_json::json!({"songs_found": progress.songs_found, "song_count": progress.songs_found});
                    CommandResponseWrapper { status: "ok".to_string(), message: None, data: Some(data) }
                }
                Err(e) => CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None }
            }
        }
        "add_folder" => {
            let folder = params.get("folder").and_then(|v| v.as_str()).unwrap_or("");
            engine.add_library_folder(folder)
                .map(|_| CommandResponseWrapper { status: "ok".to_string(), message: None, data: None })
                .unwrap_or_else(|e| CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None })
        }
        "get_settings" => {
            let settings = engine.settings();
            let data = serde_json::to_value(&settings).unwrap_or_default();
            CommandResponseWrapper { status: "ok".to_string(), message: None, data: Some(data) }
        }
        "update_settings" => {
            let delta: SettingsDelta = serde_json::from_value(params).unwrap_or(SettingsDelta {
                fullscreen: None, width: None, height: None, always_on_top: None,
                volume: None, sync_delay_ms: None, show_lyrics: None,
                font_size: None, font_bold: None, font_italic: None,
                lyrics_color: None, lyrics_outline_color: None, lyrics_sweep_color: None,
            });
            engine.update_settings(delta)
                .map(|_| CommandResponseWrapper { status: "ok".to_string(), message: None, data: None })
                .unwrap_or_else(|e| CommandResponseWrapper { status: "error".to_string(), message: Some(e.to_string()), data: None })
        }
        _ => CommandResponseWrapper {
            status: "error".to_string(),
            message: Some(format!("Unknown action: {}", action)),
            data: None,
        },
    };

    Ok(result)
}

/// Stop the engine (backward-compat).
#[tauri::command]
fn stop_backend(state: State<AppEngine>) -> Result<String, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    if let Some(mut engine) = guard.take() {
        engine.stop().map_err(|e| e.to_string())?;
        Ok("Backend stopped".to_string())
    } else {
        Err("Backend not running".to_string())
    }
}

fn main() {
    #[cfg(target_os = "linux")]
    {
        if std::env::var("WEBKIT_DISABLE_DMABUF_RENDERER").is_err() {
            std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
        }
        if std::env::var("NO_AT_BRIDGE").is_err() {
            std::env::set_var("NO_AT_BRIDGE", "1");
        }
    }

    tauri::Builder::default()
        .manage(AppEngine {
            engine: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            // Backward-compat old commands
            start_backend,
            send_command,
            stop_backend,
            // New typed commands
            commands::engine_start,
            commands::engine_stop,
            commands::engine_status,
            commands::engine_tick,
            commands::playback_play,
            commands::playback_pause,
            commands::playback_stop,
            commands::playback_next,
            commands::playback_previous,
            commands::playback_seek,
            commands::playback_set_volume,
            commands::queue_enqueue,
            commands::queue_remove,
            commands::queue_clear,
            commands::queue_move,
            commands::queue_list,
            commands::library_scan,
            commands::library_add_folder,
            commands::library_remove_folder,
            commands::library_folders,
            commands::search,
            commands::settings_get,
            commands::settings_update,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_backend_setup() -> EngineImpl {
        let dir = std::env::temp_dir().join("pykaraoke_test_tauri_main_v2");
        let _ = std::fs::remove_dir_all(&dir);
        let event_bus = crate::tauri_event_bus::NoopEventBus;
        let mut engine = EngineImpl::new(Some(dir), Box::new(event_bus));
        engine.start().unwrap();
        engine
    }

    #[test]
    fn test_engine_start() {
        let engine = test_backend_setup();
        assert_eq!(engine.status(), pykaraoke_engine::EngineStatus::Running);
    }

    #[test]
    fn test_engine_enqueue_and_play() {
        let mut engine = test_backend_setup();
        engine.enqueue("/tmp/test_song.kar").unwrap();
        let state = engine.play(None).unwrap();
        assert_eq!(state.status, PlaybackStatus::Playing);
    }

    #[test]
    fn test_engine_get_state() {
        let engine = test_backend_setup();
        assert_eq!(engine.status(), pykaraoke_engine::EngineStatus::Running);
    }

    #[test]
    fn test_engine_unknown_action() {
        // Verify backward-compat send_command handles unknown action
        let mut engine = test_backend_setup();
        let request = pykaraoke_engine::backend::CommandRequest {
            action: "nonexistent".to_string(),
            params: serde_json::Value::Null,
        };
        if let Some(backend) = engine.backend_mut() {
            let resp = backend.handle_command(request);
            assert_eq!(resp.status, "error");
            assert!(resp.message.unwrap().contains("Unknown action"));
        } else {
            panic!("Backend not available");
        }
    }

    #[test]
    fn test_appengine_initial_state() {
        let app = AppEngine {
            engine: Mutex::new(None),
        };
        let guard = app.engine.lock().unwrap();
        assert!(guard.is_none());
    }

    #[test]
    fn test_dmabuf_env_var_is_set_on_linux() {
        let source = include_str!("main.rs");
        assert!(
            source.contains("WEBKIT_DISABLE_DMABUF_RENDERER"),
            "main.rs must set WEBKIT_DISABLE_DMABUF_RENDERER to prevent \
             blank WebKitGTK windows on Linux"
        );
    }

    #[test]
    fn test_dmabuf_workaround_is_linux_gated() {
        let source = include_str!("main.rs");
        let dmabuf_pos = source.find("WEBKIT_DISABLE_DMABUF_RENDERER").unwrap();
        let preceding = &source[dmabuf_pos.saturating_sub(300)..dmabuf_pos];
        assert!(
            preceding.contains(r#"target_os = "linux""#),
            "WEBKIT_DISABLE_DMABUF_RENDERER should be behind #[cfg(target_os = \"linux\")]"
        );
    }

    #[test]
    fn test_dmabuf_workaround_checks_existing_value() {
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
    fn test_dmabuf_set_before_tauri_builder() {
        let source = include_str!("main.rs");
        let dmabuf_pos = source.find("WEBKIT_DISABLE_DMABUF_RENDERER").unwrap();
        let builder_pos = source.find("tauri::Builder::default()").unwrap();
        assert!(
            dmabuf_pos < builder_pos,
            "WEBKIT_DISABLE_DMABUF_RENDERER must be set before tauri::Builder"
        );
    }
}
