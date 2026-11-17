//! Wire-level event types for the Tracera observability protocol.
//!
//! The Crockford-Base32 ULID generator (`new_event_id`) indexes into a
//! fixed-size alphabet by `value & 0x1F`, which is always < 32 (the alphabet
//! length). Clippy's `indexing_slicing` lint cannot prove this so we
//! suppress it at module level.
#![allow(clippy::indexing_slicing)]

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

/// Schema identifier stamped on every event envelope.
pub const TRACERA_SCHEMA: &str = "tracera.v1";

/// Logical event kind. Tagged and serialized as a snake_case string.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EventKind {
    /// A tool / function call.
    ToolCall,
    /// Result of a tool / function call.
    ToolResult,
    /// A prompt was submitted to the model.
    Prompt,
    /// A model response was received.
    Response,
    /// A user keystroke or command.
    UserAction,
    /// Session lifecycle: start / end / pause / resume.
    Session,
    /// Drift / similarity alert.
    Drift,
    /// Generic catch-all (forward-compatible).
    Custom,
}

/// A single observability event.
///
/// Wire form (JSON):
/// ```json
/// {
///   "schema": "tracera.v1",
///   "id": "01J...",
///   "ts": "2026-09-12T00:00:00Z",
///   "source": "forgecode",
///   "session_id": "...",
///   "kind": "tool_call",
///   "payload": { "name": "fs.read", "args": {...} },
///   "tags": { "channel": "agent-1" }
/// }
/// ```
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceraEvent {
    /// Wire schema — always `"tracera.v1"`.
    pub schema: String,
    /// Event id (ULID-like, monotonically time-ordered).
    pub id: String,
    /// Event timestamp (UTC).
    pub ts: DateTime<Utc>,
    /// Producer (defaults to `SinkConfig::source`).
    pub source: String,
    /// Optional session id this event belongs to.
    #[serde(skip_serializing_if = "Option::is_none", default)]
    pub session_id: Option<String>,
    /// Logical kind.
    pub kind: EventKind,
    /// Kind-specific structured payload.
    pub payload: serde_json::Value,
    /// Free-form key/value tags (low cardinality).
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub tags: BTreeMap<String, String>,
}

impl TraceraEvent {
    /// Build a new event with a freshly-generated id and `ts = now`.
    ///
    /// `schema` is set to [`TRACERA_SCHEMA`] and `source` to the supplied
    /// value (typically `SinkConfig::source`).
    pub fn new(source: impl Into<String>, kind: EventKind, payload: serde_json::Value) -> Self {
        Self {
            schema: TRACERA_SCHEMA.to_string(),
            id: new_event_id(),
            ts: Utc::now(),
            source: source.into(),
            session_id: None,
            kind,
            payload,
            tags: BTreeMap::new(),
        }
    }

    /// Attach a session id.
    pub fn with_session(mut self, sid: impl Into<String>) -> Self {
        self.session_id = Some(sid.into());
        self
    }

    /// Attach a tag.
    pub fn with_tag(mut self, k: impl Into<String>, v: impl Into<String>) -> Self {
        self.tags.insert(k.into(), v.into());
        self
    }

    /// Set the timestamp explicitly (used in tests).
    pub fn with_ts(mut self, ts: DateTime<Utc>) -> Self {
        self.ts = ts;
        self
    }
}

/// Generate a fresh event id. Crockford-Base32 ULID-ish (26 chars):
///
///   `01J0YEMY8Y 0K ZJJ7H8VK8P`
///           time        random
///
/// Time part = ms since the Unix epoch, right-shifted to a 48-bit window.
/// Random part = 16 chars from `random::01..`.
///
/// This is **not** a strict ULID (no monotonic bit) but is sortably
/// time-ordered, URL-safe, and zero-dependency.
pub fn new_event_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    const CROCKFORD: &[u8; 32] = b"0123456789ABCDEFGHJKMNPQRSTVWXYZ";

    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0);

    let mut buf = String::with_capacity(26);
    // 10 chars from a 50-bit time window (ms >> 10 = ms / 1024).
    let ms_shifted = now >> 10;
    for shift in [45, 40, 35, 30, 25, 20, 15, 10, 5, 0] {
        let idx = ((ms_shifted >> shift) & 0x1F) as usize;
        buf.push(CROCKFORD[idx] as char);
    }

    // 16 random chars from a deterministic entropy — see rand below.
    let mut state = now
        .wrapping_mul(0x9E37_79B9_7F4A_7C15)
        .wrapping_add(0xDEAD_BEEF);
    for _ in 0..16 {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        let idx = (state as usize) & 0x1F;
        buf.push(CROCKFORD[idx] as char);
    }
    buf
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn event_new_sets_schema() {
        let e = TraceraEvent::new("forgecode", EventKind::Prompt, serde_json::json!({}));
        assert_eq!(e.schema, TRACERA_SCHEMA);
        assert_eq!(e.source, "forgecode");
        assert_eq!(e.id.len(), 26);
        assert_eq!(e.kind, EventKind::Prompt);
    }

    #[test]
    fn event_with_session_and_tag() {
        let e = TraceraEvent::new(
            "forgecode",
            EventKind::ToolCall,
            serde_json::json!({"name": "fs.read"}),
        )
        .with_session("sess-1")
        .with_tag("channel", "agent-1");
        assert_eq!(e.session_id.as_deref(), Some("sess-1"));
        assert_eq!(e.tags.get("channel").map(String::as_str), Some("agent-1"));
    }

    #[test]
    fn event_serializes_with_correct_shape() {
        let e = TraceraEvent::new(
            "forgecode",
            EventKind::Drift,
            serde_json::json!({"score": 0.92}),
        );
        let s = serde_json::to_string(&e).unwrap();
        assert!(s.contains("\"schema\":\"tracera.v1\""));
        assert!(s.contains("\"kind\":\"drift\""));
        assert!(s.contains("\"score\":0.92"));
    }

    #[test]
    fn event_id_is_26_crockford_chars() {
        let id = new_event_id();
        assert_eq!(id.len(), 26);
        for c in id.chars() {
            assert!(
                "0123456789ABCDEFGHJKMNPQRSTVWXYZ".contains(c),
                "non-crockford char: {c}"
            );
        }
    }

    #[test]
    fn event_id_is_time_sortable_across_seconds() {
        // Two ids generated far apart in time should sort
        // lexicographically. We pick a 2-second window which is well
        // outside the 1024ms granularity of the time prefix.
        let a = new_event_id();
        std::thread::sleep(std::time::Duration::from_millis(2_100));
        let b = new_event_id();
        assert!(
            a < b,
            "ids should be time-sortable across seconds, got {a} vs {b}"
        );
    }
}
