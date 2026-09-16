// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 KooshaPari <kooshapari@gmail.com>

//! Serialization port for Pine process state.
//!
//! The process snapshot/restore path needs to persist and rehydrate a
//! process image: the asset table, the syscall counters, the exit code,
//! and any custom state the kernel wants to round-trip.  The port
//! abstracts the concrete wire format (JSON, postcard, bincode) and
//! storage backend (file, mmap, network blob).
//!
//! Reference: kmobile/crates/kmobile-core/src/ports/serialization.rs (Rust port),
//! phenotype-voxel/src/ports/serialization.rs (Rust port).

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Engine-agnostic snapshot of a Pine process.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProcessSnapshot {
    /// Format version of this snapshot.  Bumped on breaking changes.
    pub version: u32,
    /// Identifier of the process this snapshot describes.
    pub process_id: u32,
    /// Ids of the assets attached to the process.
    pub asset_ids: Vec<String>,
    /// Number of syscalls the process has issued.
    pub syscall_count: u64,
    /// Exit code, or <c>None</c> if the process is still running.
    pub exit_code: Option<i32>,
}

impl ProcessSnapshot {
    /// Convenience constructor for tests and adapter code.
    pub fn new(process_id: u32) -> Self {
        Self {
            version: 1,
            process_id,
            asset_ids: Vec::new(),
            syscall_count: 0,
            exit_code: None,
        }
    }
}

/// Port-level errors raised by the serialization port and its adapters.
#[derive(Debug, Error)]
pub enum SerializationError {
    /// The destination is empty or otherwise unusable.
    #[error("invalid destination: {0}")]
    InvalidDestination(String),
    /// The destination is empty (no bytes read) or whitespace-only.
    #[error("empty payload: {0}")]
    Empty(String),
    /// The payload could not be parsed.
    #[error("parse error: {0}")]
    Parse(String),
    /// Underlying storage backend failed (file, mmap, network, …).
    #[error("io error: {0}")]
    Io(String),
}

/// Stable format identifier exposed by every adapter implementation.
/// Domain code uses this to refuse to load cross-version snapshots
/// before they hit the parser.
pub trait SerializationPort {
    /// Serializes <c>snapshot</c> to <c>destination</c>.
    fn save(&self, snapshot: &ProcessSnapshot, destination: &str)
        -> Result<(), SerializationError>;

    /// Loads and deserializes a snapshot from <c>destination</c>.
    fn load(&self, destination: &str) -> Result<ProcessSnapshot, SerializationError>;

    /// Stable format identifier (e.g. <c>"pine-json-v1"</c>).
    fn format_id(&self) -> &'static str;
}

/// Default JSON-on-disk adapter.  Used by the process inspector and
/// the CLI save/restore subcommand.
pub struct JsonFileSerializationPort;

impl SerializationPort for JsonFileSerializationPort {
    fn format_id(&self) -> &'static str {
        "pine-json-v1"
    }

    fn save(
        &self,
        snapshot: &ProcessSnapshot,
        destination: &str,
    ) -> Result<(), SerializationError> {
        if destination.is_empty() {
            return Err(SerializationError::InvalidDestination(
                destination.to_owned(),
            ));
        }
        let json = serde_json::to_string_pretty(snapshot)
            .map_err(|e| SerializationError::Parse(e.to_string()))?;
        std::fs::write(destination, json).map_err(|e| SerializationError::Io(e.to_string()))
    }

    fn load(&self, destination: &str) -> Result<ProcessSnapshot, SerializationError> {
        if destination.is_empty() {
            return Err(SerializationError::InvalidDestination(
                destination.to_owned(),
            ));
        }
        let body = std::fs::read_to_string(destination)
            .map_err(|e| SerializationError::Io(e.to_string()))?;
        if body.trim().is_empty() {
            return Err(SerializationError::Empty(destination.to_owned()));
        }
        serde_json::from_str(&body).map_err(|e| SerializationError::Parse(e.to_string()))
    }
}

impl Default for JsonFileSerializationPort {
    fn default() -> Self {
        Self
    }
}

/// In-memory mock for domain tests.  Records the most recent save and
/// replays a pre-loaded snapshot on load.  Implements the port directly
/// without touching the filesystem.
pub struct MockSerializationPort {
    last_saved: std::cell::RefCell<Option<ProcessSnapshot>>,
    staged: std::cell::RefCell<Option<ProcessSnapshot>>,
}

impl Default for MockSerializationPort {
    fn default() -> Self {
        Self::new()
    }
}

impl MockSerializationPort {
    /// Creates a new mock with no staged snapshot.
    pub fn new() -> Self {
        Self {
            last_saved: std::cell::RefCell::new(None),
            staged: std::cell::RefCell::new(None),
        }
    }

    /// Stages a snapshot to be returned by the next <c>load</c> call.
    pub fn stage_load(&self, snapshot: ProcessSnapshot) {
        *self.staged.borrow_mut() = Some(snapshot);
    }

    /// Returns the snapshot captured by the most recent <c>save</c> call.
    pub fn last_saved(&self) -> Option<ProcessSnapshot> {
        self.last_saved.borrow().clone()
    }
}

impl SerializationPort for MockSerializationPort {
    fn format_id(&self) -> &'static str {
        "mock-v0"
    }

    fn save(
        &self,
        snapshot: &ProcessSnapshot,
        _destination: &str,
    ) -> Result<(), SerializationError> {
        *self.last_saved.borrow_mut() = Some(snapshot.clone());
        Ok(())
    }

    fn load(&self, _destination: &str) -> Result<ProcessSnapshot, SerializationError> {
        self.staged.borrow().clone().ok_or_else(|| {
            SerializationError::Empty("MockSerializationPort: no snapshot staged.".to_owned())
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mock_captures_save_and_replays_load() {
        let port = MockSerializationPort::new();
        let snap = ProcessSnapshot {
            version: 1,
            process_id: 42,
            asset_ids: vec!["libc.so".to_owned(), "main.bin".to_owned()],
            syscall_count: 7,
            exit_code: None,
        };
        port.save(&snap, "anywhere").unwrap();
        assert_eq!(port.last_saved().as_ref(), Some(&snap));
        port.stage_load(snap.clone());
        let loaded = port.load("anywhere").unwrap();
        assert_eq!(loaded, snap);
    }

    #[test]
    fn mock_load_without_stage_returns_error() {
        let port = MockSerializationPort::new();
        match port.load("anywhere") {
            Err(SerializationError::Empty(msg)) => assert!(msg.contains("no snapshot staged")),
            other => panic!("expected Empty, got {:?}", other),
        }
    }
}
