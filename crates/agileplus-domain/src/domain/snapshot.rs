//! Snapshot domain type — periodic materialized state for fast reads.
//!
//! Traceability: FR-022 / WP01-T002

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

pub trait Versioned {
    fn version(&self) -> String;
    fn set_version(&mut self, v: String);
}

/// A snapshot of an entity's current state at a given event sequence.
///
/// Created every N events or every T minutes per entity for fast state
/// reconstruction without replaying the full event stream.
///
/// Implements `Versioned` for state migrations via phenotype-migrations.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Snapshot {
    pub id: i64,
    pub entity_type: String,
    pub entity_id: i64,
    pub state: serde_json::Value,
    pub event_sequence: i64,
    pub created_at: DateTime<Utc>,
    /// Schema version for state migration. Defaults to "1.0".
    #[serde(default = "default_version")]
    pub version: String,
}

fn default_version() -> String {
    "1.0".to_string()
}

impl Versioned for Snapshot {
    fn version(&self) -> String {
        self.version.clone()
    }

    fn set_version(&mut self, v: String) {
        self.version = v;
    }
}

impl Snapshot {
    pub fn new(
        entity_type: impl Into<String>,
        entity_id: i64,
        state: serde_json::Value,
        event_sequence: i64,
    ) -> Self {
        Self {
            id: 0,
            entity_type: entity_type.into(),
            entity_id,
            state,
            event_sequence,
            created_at: Utc::now(),
            version: default_version(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_snapshot() {
        let s = Snapshot::new(
            "feature",
            1,
            serde_json::json!({"state": "implementing"}),
            100,
        );
        assert_eq!(s.entity_type, "feature");
        assert_eq!(s.event_sequence, 100);
    }

    #[test]
    fn snapshot_serde_roundtrip() {
        let s = Snapshot::new("wp", 3, serde_json::json!({"state": "doing"}), 50);
        let json = serde_json::to_string(&s).unwrap();
        let s2: Snapshot = serde_json::from_str(&json).unwrap();
        assert_eq!(s2.entity_id, 3);
        assert_eq!(s2.event_sequence, 50);
    }
}
