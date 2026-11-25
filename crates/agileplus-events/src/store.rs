//! EventStore trait — async append-only event storage.
//!
//! Uses phenotype-error-core::RepositoryError for canonical error handling.

use agileplus_domain::domain::event::Event;
use async_trait::async_trait;
use chrono::{DateTime, Utc};
pub use phenotype_error_core::RepositoryError as EventError;

#[async_trait]
pub trait EventStore: Send + Sync {
    /// Append a new event; returns the assigned sequence number.
    async fn append(&self, event: &Event) -> Result<i64, EventError>;

    /// All events for an entity, ascending by sequence.
    async fn get_events(&self, entity_type: &str, entity_id: i64)
        -> Result<Vec<Event>, EventError>;

    /// Events from a specific sequence onward (exclusive).
    async fn get_events_since(
        &self,
        entity_type: &str,
        entity_id: i64,
        sequence: i64,
    ) -> Result<Vec<Event>, EventError>;

    /// Events within a time range.
    async fn get_events_by_range(
        &self,
        entity_type: &str,
        entity_id: i64,
        from: DateTime<Utc>,
        to: DateTime<Utc>,
    ) -> Result<Vec<Event>, EventError>;

    /// Latest event sequence number for an entity (0 if none).
    async fn get_latest_sequence(
        &self,
        entity_type: &str,
        entity_id: i64,
    ) -> Result<i64, EventError>;
}
