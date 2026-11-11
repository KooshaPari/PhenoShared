//! SessionLedger L14 — typed row structs for the schema.
//!
//! These map 1:1 onto the SQLite tables defined in
//! `migrations/0001_initial.sql`. They are deliberately thin: no derives
//! beyond what callers need (Serialize for OKF bundles, Copy for ids).
//!
//! If you add a column to the schema, add it here too and update the
//! corresponding loader in `sl-daemon/src/store/sqlite.rs`.

use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

/// One recorded daemon session.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SessionRow {
    pub id: String,
    pub started_at_ms: i64,
    pub ended_at_ms: Option<i64>,
    pub source_kind: String,
    pub label: Option<String>,
    pub metadata_json: Option<String>,
}

/// One captured event within a session.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IngestEventRow {
    pub id: i64,
    pub session_id: String,
    pub occurred_at_ms: i64,
    pub kind: String,
    pub payload_json: String,
}

/// Metadata about a stored OKF bundle.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OkfBundleRow {
    pub id: String,
    pub session_id: String,
    pub schema_version: String,
    pub created_at_ms: i64,
    pub byte_size: i64,
    pub digest: String,
    pub location: String,
}

/// Bookkeeping for one replay attempt of an OKF bundle.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReplayRunRow {
    pub id: String,
    pub bundle_id: String,
    pub started_at_ms: i64,
    pub ended_at_ms: Option<i64>,
    pub status: ReplayStatus,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ReplayStatus {
    Pending,
    Running,
    Completed,
    Failed,
}

impl ReplayStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            ReplayStatus::Pending => "pending",
            ReplayStatus::Running => "running",
            ReplayStatus::Completed => "completed",
            ReplayStatus::Failed => "failed",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "pending" => Some(ReplayStatus::Pending),
            "running" => Some(ReplayStatus::Running),
            "completed" => Some(ReplayStatus::Completed),
            "failed" => Some(ReplayStatus::Failed),
            _ => None,
        }
    }
}

impl SessionRow {
    /// Convenience constructor: stamp `started_at_ms` to wall-clock now.
    pub fn new(id: impl Into<String>, source_kind: impl Into<String>) -> Self {
        SessionRow {
            id: id.into(),
            started_at_ms: now_ms(),
            ended_at_ms: None,
            source_kind: source_kind.into(),
            label: None,
            metadata_json: None,
        }
    }
}

impl IngestEventRow {
    pub fn new(session_id: impl Into<String>, kind: impl Into<String>, payload: impl Into<String>) -> Self {
        IngestEventRow {
            id: 0,
            session_id: session_id.into(),
            occurred_at_ms: now_ms(),
            kind: kind.into(),
            payload_json: payload.into(),
        }
    }
}

fn now_ms() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn replay_status_roundtrip() {
        for s in [
            ReplayStatus::Pending,
            ReplayStatus::Running,
            ReplayStatus::Completed,
            ReplayStatus::Failed,
        ] {
            assert_eq!(ReplayStatus::parse(s.as_str()), Some(s));
        }
        assert_eq!(ReplayStatus::parse("nope"), None);
    }

    #[test]
    fn session_row_defaults() {
        let s = SessionRow::new("sess-1", "claude_code");
        assert_eq!(s.id, "sess-1");
        assert_eq!(s.source_kind, "claude_code");
        assert!(s.ended_at_ms.is_none());
        assert!(s.label.is_none());
        assert!(s.started_at_ms > 0);
    }

    #[test]
    fn ingest_event_defaults() {
        let e = IngestEventRow::new("sess-1", "tool_call", "{\"x\":1}");
        assert_eq!(e.session_id, "sess-1");
        assert_eq!(e.kind, "tool_call");
        assert_eq!(e.payload_json, "{\"x\":1}");
        assert_eq!(e.id, 0);
    }
}
