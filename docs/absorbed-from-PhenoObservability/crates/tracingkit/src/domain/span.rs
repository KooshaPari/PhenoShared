//! Span - Domain Entity

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Span ID
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SpanId(Uuid);

impl SpanId {
    pub fn new() -> Self {
        Self(Uuid::new_v4())
    }
}

impl Default for SpanId {
    fn default() -> Self {
        Self::new()
    }
}

/// Span kind
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum SpanKind {
    Internal,
    Server,
    Client,
    Producer,
    Consumer,
}

/// Span status
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum SpanStatus {
    Unset,
    Ok,
    Error { code: u32, message: String },
}

/// Span - represents a unit of work
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Span {
    pub id: SpanId,
    pub trace_id: Uuid,
    pub parent_id: Option<SpanId>,
    pub name: String,
    pub kind: SpanKind,
    pub status: SpanStatus,
    pub start_time: DateTime<Utc>,
    pub end_time: Option<DateTime<Utc>>,
    pub attributes: Vec<(String, AttributeValue)>,
    pub events: Vec<SpanEvent>,
    pub links: Vec<SpanLink>,
}

impl Span {
    pub fn new(name: impl Into<String>, trace_id: Uuid) -> Self {
        Self {
            id: SpanId::new(),
            trace_id,
            parent_id: None,
            name: name.into(),
            kind: SpanKind::Internal,
            status: SpanStatus::Unset,
            start_time: Utc::now(),
            end_time: None,
            attributes: Vec::new(),
            events: Vec::new(),
            links: Vec::new(),
        }
    }

    pub fn with_parent(mut self, parent_id: SpanId) -> Self {
        self.parent_id = Some(parent_id);
        self
    }

    pub fn with_kind(mut self, kind: SpanKind) -> Self {
        self.kind = kind;
        self
    }

    pub fn set_attribute(&mut self, key: impl Into<String>, value: AttributeValue) {
        self.attributes.push((key.into(), value));
    }

    pub fn add_event(&mut self, name: impl Into<String>) {
        self.events.push(SpanEvent {
            name: name.into(),
            timestamp: Utc::now(),
            attributes: Vec::new(),
        });
    }

    pub fn end(&mut self) {
        self.end_time = Some(Utc::now());
    }

    pub fn is_ended(&self) -> bool {
        self.end_time.is_some()
    }
}

/// Attribute value
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum AttributeValue {
    String(String),
    Bool(bool),
    I64(i64),
    F64(f64),
}

impl From<String> for AttributeValue {
    fn from(s: String) -> Self {
        AttributeValue::String(s)
    }
}

impl From<&str> for AttributeValue {
    fn from(s: &str) -> Self {
        AttributeValue::String(s.to_string())
    }
}

impl From<i64> for AttributeValue {
    fn from(n: i64) -> Self {
        AttributeValue::I64(n)
    }
}

impl From<f64> for AttributeValue {
    fn from(f: f64) -> Self {
        AttributeValue::F64(f)
    }
}

impl From<bool> for AttributeValue {
    fn from(b: bool) -> Self {
        AttributeValue::Bool(b)
    }
}

/// Span event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpanEvent {
    pub name: String,
    pub timestamp: DateTime<Utc>,
    pub attributes: Vec<(String, AttributeValue)>,
}

/// Span link
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpanLink {
    pub span_context: SpanContext,
    pub attributes: Vec<(String, AttributeValue)>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpanContext {
    pub trace_id: Uuid,
    pub span_id: Uuid,
    pub sampled: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_span_creation() {
        let trace_id = Uuid::new_v4();
        let span = Span::new("test_operation", trace_id);

        assert_eq!(span.name, "test_operation");
        assert!(!span.is_ended());
    }

    #[test]
    fn test_span_end() {
        let span = &mut Span::new("test", Uuid::new_v4());
        span.end();
        assert!(span.is_ended());
    }
}
