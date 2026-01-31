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
    
    let backend_script = resource_path.join("pykbackend.py");
    
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
