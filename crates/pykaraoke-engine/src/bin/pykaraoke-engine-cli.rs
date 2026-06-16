//! CLI binary for the PyKaraoke engine.
//!
//! Used by the Python compatibility test suite to invoke the Rust engine
//! and retrieve JSON-formatted results for comparison.
//!
//! Subcommands:
//!   parse-filename  -- Parse a karaoke filename and output ParsedSong JSON
//!   player          -- Player state machine operations
//!   queue           -- Queue management operations
//!   backend         -- Backend command dispatch

use pykaraoke_engine::backend::{Backend, CommandRequest};
use pykaraoke_engine::filename_parser::{FileNameType, FilenameParser};
use pykaraoke_engine::database::Persistence;
use pykaraoke_engine::player::Player;
use pykaraoke_engine::queue::Queue;
use pykaraoke_engine::song::SongStruct;
use serde_json::Value;
use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: pykaraoke-engine-cli <subcommand> [args...]");
        std::process::exit(1);
    }

    let result = match args[1].as_str() {
        "parse-filename" => cmd_parse_filename(&args[2..]),
        "player" => cmd_player(&args[2..]),
        "queue" => cmd_queue(&args[2..]),
        "backend" => cmd_backend(&args[2..]),
        _ => {
            eprintln!("Unknown subcommand: {}", args[1]);
            std::process::exit(1);
        }
    };

    println!("{}", serde_json::to_string(&result).unwrap());
}

// ── parse-filename ─────────────────────────────────────────────────

fn cmd_parse_filename(args: &[String]) -> Value {
    let mut filepath = String::new();
    let mut name_type = String::from("ArtistTitle");

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--filepath" => {
                i += 1;
                if i < args.len() {
                    filepath = args[i].clone();
                }
            }
            "--name-type" => {
                i += 1;
                if i < args.len() {
                    name_type = args[i].clone();
                }
            }
            _ => {}
        }
        i += 1;
    }

    let nt = match name_type.as_str() {
        "DiscTrackArtistTitle" => FileNameType::DiscTrackArtistTitle,
        "DisctrackArtistTitle" => FileNameType::DisctrackArtistTitle,
        "DiscArtistTitle" => FileNameType::DiscArtistTitle,
        _ => FileNameType::ArtistTitle,
    };

    let parser = FilenameParser::new(nt);
    let result = parser.parse(&filepath);
    serde_json::to_value(result).unwrap()
}

// ── player ─────────────────────────────────────────────────────────

fn cmd_player(args: &[String]) -> Value {
    if args.is_empty() {
        return serde_json::json!({"error": "No player subcommand"});
    }

    let mut player = Player::new();
    let mut current_time_ms: u64 = 0;

    // Parse optional --current-time-ms
    let mut i = 0;
    while i < args.len() {
        if args[i] == "--current-time-ms" {
            i += 1;
            if i < args.len() {
                current_time_ms = args[i].parse().unwrap_or(0);
            }
        }
        i += 1;
    }

    let command = if !args.is_empty() && !args[0].starts_with("--") {
        args[0].as_str()
    } else {
        "state"
    };

    match command {
        "state" => {
            serde_json::json!({
                "state": format!("{:?}", player.state),
            })
        }
        "play" => {
            player.play(current_time_ms);
            serde_json::json!({
                "state": format!("{:?}", player.state),
                "play_start_time": player.timing.play_start_time,
            })
        }
        "pause" => {
            player.pause(current_time_ms);
            serde_json::json!({
                "state": format!("{:?}", player.state),
                "play_time": player.timing.play_time,
                "play_start_time": player.timing.play_start_time,
            })
        }
        "rewind" => {
            player.rewind();
            serde_json::json!({
                "state": format!("{:?}", player.state),
            })
        }
        "seek" => {
            let pos = args.iter()
                .position(|a| a == "--position-ms")
                .and_then(|p| args.get(p + 1))
                .and_then(|v| v.parse().ok())
                .unwrap_or(0);
            player.seek(pos, current_time_ms);
            serde_json::json!({
                "state": format!("{:?}", player.state),
                "seek_pos_ms": player.timing.seek_pos_ms,
            })
        }
        "close" => {
            player.close();
            serde_json::json!({
                "state": format!("{:?}", player.state),
            })
        }
        "shutdown" => {
            player.shutdown();
            serde_json::json!({
                "state": format!("{:?}", player.state),
            })
        }
        "get_pos" => {
            let pos = player.get_pos(current_time_ms);
            serde_json::json!({
                "state": format!("{:?}", player.state),
                "position_ms": pos,
            })
        }
        _ => {
            serde_json::json!({"error": format!("Unknown player command: {}", command)})
        }
    }
}

// ── queue ──────────────────────────────────────────────────────────

fn cmd_queue(args: &[String]) -> Value {
    if args.is_empty() {
        return serde_json::json!({"error": "No queue subcommand"});
    }

    let mut queue = Queue::new();

    let command = args[0].as_str();
    match command {
        "add" => {
            let filepath = args.iter()
                .position(|a| a == "--filepath")
                .and_then(|p| args.get(p + 1))
                .cloned()
                .unwrap_or_default();
            let song = SongStruct::from_filepath(&filepath);
            queue.add(song);
            serde_json::json!({
                "len": queue.len(),
            })
        }
        "remove" => {
            let index = args.iter()
                .position(|a| a == "--index")
                .and_then(|p| args.get(p + 1))
                .and_then(|v| v.parse().ok())
                .unwrap_or(0);
            let removed = queue.remove(index);
            serde_json::json!({
                "len": queue.len(),
                "removed": removed.is_some(),
            })
        }
        "clear" => {
            queue.clear();
            serde_json::json!({
                "len": queue.len(),
            })
        }
        "select" => {
            let index = args.iter()
                .position(|a| a == "--index")
                .and_then(|p| args.get(p + 1))
                .and_then(|v| v.parse().ok())
                .unwrap_or(0);
            let selected = queue.select(index);
            serde_json::json!({
                "selected": selected.is_some(),
                "playlist_index": queue.playlist_index,
            })
        }
        "advance" => {
            let next = queue.advance();
            serde_json::json!({
                "advanced": next.is_some(),
                "playlist_index": queue.playlist_index,
            })
        }
        "previous" => {
            let prev = queue.previous();
            serde_json::json!({
                "went_previous": prev.is_some(),
                "playlist_index": queue.playlist_index,
            })
        }
        "summaries" => {
            let summaries = queue.summaries();
            serde_json::json!({
                "len": queue.len(),
                "summaries": summaries,
            })
        }
        _ => {
            serde_json::json!({"error": format!("Unknown queue command: {}", command)})
        }
    }
}

// ── backend ────────────────────────────────────────────────────────

fn cmd_backend(args: &[String]) -> Value {
    if args.is_empty() {
        return serde_json::json!({"error": "No backend subcommand"});
    }

    let dir = std::env::temp_dir().join("pykaraoke_compat_cli");
    let persistence = Persistence::new(Some(dir));
    let mut backend = Backend::new(persistence);

    match args[0].as_str() {
        "command" => {
            if args.len() < 2 {
                return serde_json::json!({"error": "No action specified"});
            }
            let action = args[1].clone();
            let mut params = Value::Null;

            let params_pos = args.iter().position(|a| a == "--params");
            if let Some(pos) = params_pos {
                if pos + 1 < args.len() {
                    if let Ok(p) = serde_json::from_str::<Value>(&args[pos + 1]) {
                        params = p;
                    }
                }
            }

            let request = CommandRequest { action, params };
            let response = backend.handle_command(request);
            serde_json::to_value(response).unwrap()
        }
        "state" => {
            let state = backend.get_state();
            serde_json::to_value(state).unwrap()
        }
        _ => {
            serde_json::json!({"error": format!("Unknown backend command: {}", args[0])})
        }
    }
}
