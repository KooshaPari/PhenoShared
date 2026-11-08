//! Structured logging with context propagation (helix-logging patterns).

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogContext {
    pub trace_id: String,
    pub span_id: String,
    pub service: String,
}

pub struct StructuredLogger {
    #[allow(dead_code)]
    context: LogContext,
}

impl StructuredLogger {
    pub fn new(context: LogContext) -> Self {
        Self { context }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_log_context_creation() {
        let ctx = LogContext {
            trace_id: "trace-1".to_string(),
            span_id: "span-1".to_string(),
            service: "api".to_string(),
        };
        assert_eq!(ctx.service, "api");
    }
}
