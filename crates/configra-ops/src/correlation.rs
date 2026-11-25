//! Correlation ID generation and propagation through tracing spans.

use std::sync::Arc;

use tracing::Span;
use uuid::Uuid;

/// Request-scoped correlation identifier (UUID v4).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct CorrelationId(Arc<str>);

impl std::fmt::Display for CorrelationId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl CorrelationId {
    /// Generate a new random correlation ID.
    pub fn new() -> Self {
        Self(Uuid::new_v4().to_string().into())
    }

    /// Parse from an existing header / log field value.
    pub fn parse(value: &str) -> Option<Self> {
        let trimmed = value.trim();
        if trimmed.is_empty() {
            return None;
        }
        Uuid::parse_str(trimmed)
            .ok()
            .map(|u| Self(u.to_string().into()))
            .or_else(|| Some(Self(trimmed.to_owned().into())))
    }

    /// Read from `CONFIGRA_CORRELATION_ID` or generate a new ID.
    pub fn from_env_or_new() -> Self {
        std::env::var("CONFIGRA_CORRELATION_ID")
            .ok()
            .and_then(|v| Self::parse(&v))
            .unwrap_or_default()
    }

    /// Header name for HTTP propagation (default `X-Correlation-ID`).
    pub fn header_name() -> &'static str {
        static HEADER: std::sync::OnceLock<String> = std::sync::OnceLock::new();
        HEADER
            .get_or_init(|| {
                std::env::var("CONFIGRA_CORRELATION_ID_HEADER")
                    .unwrap_or_else(|_| "X-Correlation-ID".into())
            })
            .as_str()
    }

    /// Correlation ID string value.
    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// Attach this ID to the current tracing span.
    pub fn attach_to_span(&self) {
        Span::current().record("correlation_id", tracing::field::display(self.0.as_ref()));
    }

    /// Create a child span tagged with this correlation ID.
    pub fn span(&self, name: &'static str) -> tracing::Span {
        tracing::info_span!("correlation", name = name, correlation_id = %self)
    }
}

impl Default for CorrelationId {
    fn default() -> Self {
        Self::new()
    }
}

/// Install correlation ID on every new root span when absent.
#[derive(Debug, Clone, Default)]
pub struct CorrelationLayer;

impl CorrelationLayer {
    /// Ensure the active span carries `correlation_id`, generating one if needed.
    pub fn ensure_active() -> CorrelationId {
        let id = CorrelationId::from_env_or_new();
        id.attach_to_span();
        id
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_uuid_correlation_id() {
        let raw = "550e8400-e29b-41d4-a716-446655440000";
        let id = CorrelationId::parse(raw).expect("valid uuid");
        assert_eq!(id.as_str(), raw);
    }

    #[test]
    fn parse_opaque_correlation_id() {
        let id = CorrelationId::parse("req-abc-123").expect("opaque id");
        assert_eq!(id.as_str(), "req-abc-123");
    }
}
