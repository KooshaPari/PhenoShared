//! Trace - Domain Entity

use chrono::{DateTime, Utc};
use uuid::Uuid;

use super::Span;

/// Trace - collection of spans
#[derive(Debug, Clone)]
pub struct Trace {
    pub id: Uuid,
    pub spans: Vec<Span>,
    pub start_time: DateTime<Utc>,
    pub end_time: Option<DateTime<Utc>>,
}

impl Trace {
    pub fn new() -> Self {
        Self {
            id: Uuid::new_v4(),
            spans: Vec::new(),
            start_time: Utc::now(),
            end_time: None,
        }
    }

    pub fn add_span(&mut self, span: Span) {
        self.spans.push(span);
    }

    pub fn end(&mut self) {
        self.end_time = Some(Utc::now());
    }

    pub fn span_count(&self) -> usize {
        self.spans.len()
    }

    pub fn root_span(&self) -> Option<&Span> {
        self.spans.iter().find(|s| s.parent_id.is_none())
    }
}

impl Default for Trace {
    fn default() -> Self {
        Self::new()
    }
}
