//! Log Entry

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use super::Level;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub id: Uuid,
    pub level: Level,
    pub message: String,
    pub timestamp: DateTime<Utc>,
    pub fields: Vec<(String, serde_json::Value)>,
}

impl LogEntry {
    pub fn new(level: Level, message: impl Into<String>) -> Self {
        Self {
            id: Uuid::new_v4(),
            level,
            message: message.into(),
            timestamp: Utc::now(),
            fields: Vec::new(),
        }
    }

    pub fn with_field(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.fields.push((key.into(), value));
        self
    }
}
