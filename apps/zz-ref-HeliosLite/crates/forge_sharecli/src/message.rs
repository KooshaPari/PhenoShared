//! ShareCLI message envelope — topic-addressed payload with identity and timestamp.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// A topic-addressed message relayed through ShareCLI channels and queues.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ShareMessage {
    /// Stable message id (v4 UUID).
    pub id: String,
    /// Topic / channel name this message was published to.
    pub topic: String,
    /// JSON payload.
    pub payload: serde_json::Value,
    /// Creation timestamp (UTC).
    pub created_at: DateTime<Utc>,
    /// Monotonic sequence assigned by the sender (per-channel/queue).
    pub seq: u64,
}

impl ShareMessage {
    /// Create a new message with a fresh UUID and current timestamp.
    pub fn new(topic: impl Into<String>, payload: serde_json::Value) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            topic: topic.into(),
            payload,
            created_at: Utc::now(),
            seq: 0,
        }
    }

    /// Create a message with an explicit sequence number (assigned by the channel/queue).
    pub fn with_seq(mut self, seq: u64) -> Self {
        self.seq = seq;
        self
    }

    /// Convenience: create from a string payload.
    pub fn text(topic: impl Into<String>, text: impl Into<String>) -> Self {
        Self::new(topic, serde_json::Value::String(text.into()))
    }

    /// Convenience: create from any serializable payload.
    pub fn json<T: Serialize>(topic: impl Into<String>, value: &T) -> Self {
        let payload = serde_json::to_value(value).unwrap_or(serde_json::Value::Null);
        Self::new(topic, payload)
    }
}
