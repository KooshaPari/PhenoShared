use crate::input::{PointerInput, TextInput};
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};
use uuid::Uuid;

/// Unified automation event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutomationEvent {
    /// Event identifier.
    pub id: String,
    /// Event type: "pointer", "text", "screenshot", "assertion", "navigate".
    pub event_type: String,
    /// Platform: "desktop", "mobile", "sandbox".
    pub platform: String,
    /// Event payload.
    pub payload: EventPayload,
    /// Timestamp (Unix seconds).
    pub timestamp: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum EventPayload {
    Pointer(PointerInput),
    Text(TextInput),
    Screenshot { path: String },
    Assertion { condition: String, expected: String },
    Navigate { url: String },
    Custom { data: serde_json::Value },
}

impl AutomationEvent {
    /// Create a new pointer event.
    pub fn pointer(platform: &str, input: PointerInput) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            event_type: "pointer".to_string(),
            platform: platform.to_string(),
            payload: EventPayload::Pointer(input),
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
        }
    }

    /// Create a new text input event.
    pub fn text(platform: &str, input: TextInput) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            event_type: "text".to_string(),
            platform: platform.to_string(),
            payload: EventPayload::Text(input),
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
        }
    }

    /// Create a screenshot event.
    pub fn screenshot(platform: &str, path: impl Into<String>) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            event_type: "screenshot".to_string(),
            platform: platform.to_string(),
            payload: EventPayload::Screenshot { path: path.into() },
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
        }
    }
}
