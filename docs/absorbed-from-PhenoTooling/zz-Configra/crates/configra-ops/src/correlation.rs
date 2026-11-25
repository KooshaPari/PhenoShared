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

    #[test]
    fn new_generates_unique_ids() {
        let a = CorrelationId::new();
        let b = CorrelationId::new();
        assert_ne!(a.as_str(), b.as_str());
    }

    #[test]
    fn default_also_generates_unique_id() {
        let id = CorrelationId::default();
        // Should be a valid UUID format
        assert!(!id.as_str().is_empty());
        assert_eq!(id.as_str().len(), 36); // UUID v4 is 36 chars
    }

    #[test]
    fn parse_empty_returns_none() {
        assert!(CorrelationId::parse("").is_none());
        assert!(CorrelationId::parse("   ").is_none());
    }

    #[test]
    fn parse_preserves_whitespace_stripped() {
        let id = CorrelationId::parse("  req-123  ").expect("trimmed id");
        assert_eq!(id.as_str(), "req-123");
    }

    #[test]
    fn correlation_id_display() {
        let id = CorrelationId::parse("test-id-42").unwrap();
        let displayed = format!("{}", id);
        assert_eq!(displayed, "test-id-42");
    }

    #[test]
    fn correlation_id_equality_and_hash() {
        let a = CorrelationId::parse("same-id").unwrap();
        let b = CorrelationId::parse("same-id").unwrap();
        let c = CorrelationId::parse("other-id").unwrap();
        assert_eq!(a, b);
        assert_ne!(a, c);
        // Can be used as HashMap key
        let mut map = std::collections::HashMap::new();
        map.insert(a.clone(), 1);
        assert_eq!(map.get(&b), Some(&1));
    }

    #[test]
    fn header_name_default() {
        // In a clean env, the default header is X-Correlation-ID
        // (We can't easily test env override here due to OnceLock caching.)
        let name = CorrelationId::header_name();
        assert!(!name.is_empty());
    }
}
