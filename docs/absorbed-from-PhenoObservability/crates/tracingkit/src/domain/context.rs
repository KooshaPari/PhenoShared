//! Trace Context

use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// W3C Trace Context
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct W3CTraceContext {
    pub traceparent: String,
}

impl W3CTraceContext {
    pub fn new(trace_id: Uuid, span_id: Uuid, sampled: bool) -> Self {
        let flags = if sampled { "01" } else { "00" };
        let traceparent = format!("00-{}-{}-{}", trace_id, span_id, flags);
        Self { traceparent }
    }

    pub fn trace_id(&self) -> Option<Uuid> {
        let parts: Vec<&str> = self.traceparent.split('-').collect();
        if parts.len() >= 2 {
            Uuid::parse_str(parts[1]).ok()
        } else {
            None
        }
    }
}

/// B3 Propagation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct B3Context {
    pub trace_id: Option<String>,
    pub span_id: Option<String>,
    pub sampled: Option<bool>,
}

impl B3Context {
    pub fn new(trace_id: Uuid, span_id: Uuid, sampled: bool) -> Self {
        Self {
            trace_id: Some(trace_id.to_string().replace("-", "")),
            span_id: Some(format!("{:016x}", span_id.as_u128())),
            sampled: Some(sampled),
        }
    }
}
