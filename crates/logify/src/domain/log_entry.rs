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

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn log_entry_new_creates_entry() {
        let entry = LogEntry::new(Level::Info, "test");
        assert_eq!(entry.level, Level::Info);
        assert_eq!(entry.message, "test");
        assert!(entry.fields.is_empty());
    }

    #[test]
    fn log_entry_with_field_adds_field() {
        let entry = LogEntry::new(Level::Warn, "with fields")
            .with_field("key1", json!("value1"))
            .with_field("count", json!(42));

        assert_eq!(entry.fields.len(), 2);
        assert_eq!(entry.fields[0].0, "key1");
        assert_eq!(entry.fields[0].1, json!("value1"));
        assert_eq!(entry.fields[1].0, "count");
        assert_eq!(entry.fields[1].1, json!(42));
    }

    #[test]
    fn log_entry_has_unique_ids() {
        let a = LogEntry::new(Level::Info, "a");
        let b = LogEntry::new(Level::Info, "b");
        assert_ne!(a.id, b.id);
    }

    #[test]
    fn log_entry_serde_roundtrip() {
        let entry = LogEntry::new(Level::Error, "boom").with_field("code", json!(500));
        let json = serde_json::to_string(&entry).unwrap();
        let back: LogEntry = serde_json::from_str(&json).unwrap();
        assert_eq!(back.level, Level::Error);
        assert_eq!(back.message, "boom");
        assert_eq!(back.fields.len(), 1);
    }

    #[test]
    fn log_entry_timestamp_is_recent() {
        let entry = LogEntry::new(Level::Info, "now");
        let now = Utc::now();
        let diff = now - entry.timestamp;
        // Should be no more than 1 second old
        assert!(diff.num_seconds() < 1);
    }

    #[test]
    fn log_entry_clone_preserves_data() {
        let entry = LogEntry::new(Level::Fatal, "critical").with_field("origin", json!("test"));
        let cloned = entry.clone();
        assert_eq!(cloned.id, entry.id);
        assert_eq!(cloned.message, entry.message);
        assert_eq!(cloned.fields, entry.fields);
    }
}
