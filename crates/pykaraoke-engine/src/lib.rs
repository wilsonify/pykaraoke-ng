//! PyKaraoke NG — Native Rust karaoke engine.
//!
//! This crate implements the core karaoke engine that was previously
//! written in Python.  It is designed as an incremental, drop-in
//! replacement: module by module, the Rust implementation mirrors
//! the Python reference in `src/pykaraoke/`.

pub mod filename_parser;
pub mod song;
pub mod discovery;
pub mod library;
pub mod queue;
pub mod player;
pub mod database;
pub mod backend;
pub mod format;
