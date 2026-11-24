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

pub use hash::{compute_hash, verify_chain, HashError};
pub use query::{EventQuery, QueryError};
pub use replay::{replay_events, replay_events_since, Aggregate, ReplayError};
pub use snapshot::{should_snapshot, SnapshotConfig, SnapshotError, SnapshotStore};
pub use store::{EventError, EventStore};

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
}
