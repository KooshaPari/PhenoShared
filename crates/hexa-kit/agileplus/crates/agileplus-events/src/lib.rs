//! Event sourcing engine for AgilePlus.
//!
//! Provides append-only event storage with SHA-256 hash chain verification,
//! snapshot management, aggregate replay, and query filtering.
//! Traceability: FR-008 / WP02

pub mod hash;
pub mod query;
pub mod replay;
pub mod snapshot;
pub mod store;

pub use hash::{HashError, compute_hash, verify_chain};
pub use query::{EventQuery, QueryError};
pub use replay::{Aggregate, ReplayError, replay_events, replay_events_since};
pub use snapshot::{SnapshotConfig, SnapshotError, SnapshotStore, should_snapshot};
pub use store::{EventError, EventStore};

/// Top-level error type for the event sourcing subsystem.
///
/// Composes the per-module errors (`EventError`, `HashError`, `ReplayError`,
/// `SnapshotError`, `QueryError`) plus a discriminating `From<std::io::Error>`
/// and `From<serde_json::Error>` so callers can lift raw I/O or JSON failures
/// into the structured error envelope without an extra `.map_err`.
#[derive(Debug, thiserror::Error)]
pub enum EventSourcingError {
    #[error("Store error: {0}")]
    Store(#[from] EventError),
    #[error("Hash error: {0}")]
    Hash(#[from] HashError),
    #[error("Replay error: {0}")]
    Replay(#[from] ReplayError),
    #[error("Snapshot error: {0}")]
    Snapshot(#[from] SnapshotError),
    #[error("Query error: {0}")]
    Query(#[from] QueryError),
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Serialization error: {0}")]
    Serde(#[from] serde_json::Error),
}

impl From<std::io::Error> for EventError {
    fn from(err: std::io::Error) -> Self {
        match err.kind() {
            std::io::ErrorKind::NotFound => Self::StorageError(format!("not found: {err}")),
            std::io::ErrorKind::PermissionDenied => {
                Self::StorageError(format!("permission denied: {err}"))
            }
            _ => Self::StorageError(err.to_string()),
        }
    }
}

impl From<std::io::Error> for SnapshotError {
    fn from(err: std::io::Error) -> Self {
        match err.kind() {
            std::io::ErrorKind::NotFound => Self::StorageError(format!("not found: {err}")),
            std::io::ErrorKind::PermissionDenied => {
                Self::StorageError(format!("permission denied: {err}"))
            }
            _ => Self::StorageError(err.to_string()),
        }
    }
}

impl From<serde_json::Error> for EventError {
    fn from(err: serde_json::Error) -> Self {
        Self::StorageError(format!("serialization: {err}"))
    }
}

impl From<serde_json::Error> for SnapshotError {
    fn from(err: serde_json::Error) -> Self {
        Self::StorageError(format!("serialization: {err}"))
    }
}

impl From<serde_json::Error> for QueryError {
    fn from(err: serde_json::Error) -> Self {
        Self::Error(format!("serialization: {err}"))
    }
}

impl From<serde_json::Error> for ReplayError {
    fn from(err: serde_json::Error) -> Self {
        Self::InvalidState(format!("serialization: {err}"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn from_io_not_found_maps_to_storage() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "missing");
        let e: EventError = io_err.into();
        assert!(
            matches!(e, EventError::StorageError(ref m) if m.contains("not found")),
            "expected StorageError for NotFound, got {e:?}"
        );
    }

    #[test]
    fn from_io_permission_denied_maps_to_storage() {
        let io_err = std::io::Error::new(std::io::ErrorKind::PermissionDenied, "nope");
        let e: EventError = io_err.into();
        assert!(
            matches!(e, EventError::StorageError(ref m) if m.contains("permission denied")),
            "expected StorageError for PermissionDenied, got {e:?}"
        );
    }

    #[test]
    fn from_io_other_maps_to_storage() {
        let io_err = std::io::Error::new(std::io::ErrorKind::BrokenPipe, "pipe");
        let e: EventError = io_err.into();
        assert!(matches!(e, EventError::StorageError(_)));
    }

    #[test]
    fn from_serde_for_event_error() {
        let json_err = serde_json::from_str::<i32>("not-json").unwrap_err();
        let e: EventError = json_err.into();
        assert!(matches!(e, EventError::StorageError(m) if m.contains("serialization")));
    }

    #[test]
    fn from_serde_for_snapshot_error() {
        let json_err = serde_json::from_str::<i32>("not-json").unwrap_err();
        let e: SnapshotError = json_err.into();
        assert!(matches!(e, SnapshotError::StorageError(m) if m.contains("serialization")));
    }

    #[test]
    fn from_serde_for_query_error() {
        let json_err = serde_json::from_str::<i32>("not-json").unwrap_err();
        let e: QueryError = json_err.into();
        assert!(matches!(e, QueryError::Error(m) if m.contains("serialization")));
    }

    #[test]
    fn from_serde_for_replay_error() {
        let json_err = serde_json::from_str::<i32>("not-json").unwrap_err();
        let e: ReplayError = json_err.into();
        assert!(matches!(e, ReplayError::InvalidState(m) if m.contains("serialization")));
    }

    #[test]
    fn from_io_into_top_level_event_sourcing_error() {
        let io_err = std::io::Error::new(std::io::ErrorKind::ConnectionReset, "reset");
        let e: EventSourcingError = io_err.into();
        assert!(matches!(e, EventSourcingError::Io(_)));
    }

    #[test]
    fn from_serde_into_top_level_event_sourcing_error() {
        let json_err = serde_json::from_str::<i32>("not-json").unwrap_err();
        let e: EventSourcingError = json_err.into();
        assert!(matches!(e, EventSourcingError::Serde(_)));
    }
}
