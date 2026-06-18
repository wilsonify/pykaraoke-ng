use pykaraoke_engine::Engine;
use pykaraoke_engine::EngineImpl;
use pykaraoke_engine::views::*;
use std::sync::Mutex;
use tauri::State;

use crate::tauri_event_bus::TauriEventBus;
use crate::resolve_data_dir;

pub struct AppEngine {
    pub engine: Mutex<Option<EngineImpl>>,
}

#[tauri::command]
pub fn engine_start(state: State<'_, AppEngine>, app_handle: tauri::AppHandle) -> Result<(), String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;

    // Check if already running
    if let Some(engine) = guard.as_ref() {
        if engine.status() == pykaraoke_engine::EngineStatus::Running {
            return Ok(());
        }
    }

    let data_dir = resolve_data_dir(&app_handle);
    let event_bus = TauriEventBus::new(app_handle.clone());
    let mut engine = EngineImpl::new(Some(data_dir), Box::new(event_bus));
    engine.start().map_err(|e| e.to_string())?;
    *guard = Some(engine);
    Ok(())
}

#[tauri::command]
pub fn engine_stop(state: State<'_, AppEngine>) -> Result<(), String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not created")?;
    engine.stop().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn engine_status(state: State<'_, AppEngine>) -> Result<String, String> {
    let guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let status = match guard.as_ref() {
        Some(engine) => engine.status(),
        None => pykaraoke_engine::EngineStatus::Stopped,
    };
    Ok(serde_json::to_string(&status).unwrap_or_default())
}

#[tauri::command]
pub fn engine_tick(state: State<'_, AppEngine>) -> Result<(), String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.tick();
    Ok(())
}

#[tauri::command]
pub fn playback_play(
    state: State<'_, AppEngine>,
    song_id: Option<u64>,
) -> Result<PlaybackState, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    let sid = song_id.map(SongId);
    engine.play(sid).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn playback_pause(state: State<'_, AppEngine>) -> Result<PlaybackState, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.pause().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn playback_stop(state: State<'_, AppEngine>) -> Result<PlaybackState, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.stop_playback().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn playback_next(state: State<'_, AppEngine>) -> Result<PlaybackState, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.next().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn playback_previous(state: State<'_, AppEngine>) -> Result<PlaybackState, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.previous().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn playback_seek(
    state: State<'_, AppEngine>,
    position_ms: u64,
) -> Result<PlaybackState, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.seek(position_ms).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn playback_set_volume(
    state: State<'_, AppEngine>,
    volume: f64,
) -> Result<PlaybackState, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.set_volume(volume).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn queue_enqueue(
    state: State<'_, AppEngine>,
    filepath: String,
) -> Result<QueueView, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.enqueue(&filepath).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn queue_remove(
    state: State<'_, AppEngine>,
    index: usize,
) -> Result<QueueView, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.remove_from_queue(index).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn queue_clear(state: State<'_, AppEngine>) -> Result<QueueView, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.clear_queue().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn queue_move(
    state: State<'_, AppEngine>,
    from: usize,
    to: usize,
) -> Result<QueueView, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.move_in_queue(from, to).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn queue_list(state: State<'_, AppEngine>) -> Result<QueueView, String> {
    let guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_ref().ok_or("Engine not started")?;
    Ok(engine.queue())
}

#[tauri::command]
pub fn library_scan(state: State<'_, AppEngine>) -> Result<LibraryScanProgress, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.scan_library().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn library_add_folder(
    state: State<'_, AppEngine>,
    path: String,
) -> Result<(), String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.add_library_folder(&path).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn library_remove_folder(
    state: State<'_, AppEngine>,
    path: String,
) -> Result<(), String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.remove_library_folder(&path).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn library_folders(state: State<'_, AppEngine>) -> Result<Vec<String>, String> {
    let guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_ref().ok_or("Engine not started")?;
    Ok(engine.library_folders())
}

#[tauri::command]
pub fn search(
    state: State<'_, AppEngine>,
    query: String,
) -> Result<SearchResultsView, String> {
    let guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_ref().ok_or("Engine not started")?;
    Ok(engine.search(&query))
}

#[tauri::command]
pub fn settings_get(state: State<'_, AppEngine>) -> Result<SettingsView, String> {
    let guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_ref().ok_or("Engine not started")?;
    Ok(engine.settings())
}

#[tauri::command]
pub fn settings_update(
    state: State<'_, AppEngine>,
    delta: SettingsDelta,
) -> Result<SettingsView, String> {
    let mut guard = state.engine.lock().map_err(|e| format!("Lock error: {}", e))?;
    let engine = guard.as_mut().ok_or("Engine not started")?;
    engine.update_settings(delta).map_err(|e| e.to_string())
}
