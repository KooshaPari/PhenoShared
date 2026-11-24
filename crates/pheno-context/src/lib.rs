//! `pheno-context` — canonical request context substrate for the pheno-* fleet.
//!
//! Carries identifiers (request / span / trace), user / org metadata, and an
//! extensible key-value bag through every layer of a request lifecycle.
//! Builders (`ContextBuilder`) construct immutable `Context` values; helpers
//! in this crate integrate with HTTP headers via the `http` crate.
//!
//! # Feature flags
//! - `oidc`: enables [`oidc::OidcClaims`] OIDC header extraction.
//! - `tracing`: enables `tracing` span instrumentation on [`Context::new`]
//!   and [`Context::from_headers`].

#![warn(missing_docs)]

#[cfg(feature = "oidc")]
pub mod oidc;

use std::collections::HashMap;
use std::fmt;

use http::HeaderMap;

/// Error type for [`Context`] construction.
#[derive(Debug, thiserror::Error)]
pub enum ContextError {
    /// A required field or header was missing.
    #[error("missing header: {0}")]
    MissingHeader(String),
}

/// Canonical request context carrying identifiers, user/org metadata,
/// and an extensible key-value bag.
#[derive(Clone, Debug, PartialEq)]
pub struct Context {
    /// Unique request identifier (required). Maps from `X-Request-ID`.
    pub request_id: String,
    /// Span identifier for observability (required). Maps from `X-Span-ID`.
    pub span_id: String,
    /// Trace identifier for distributed tracing (required). Maps from `X-Trace-ID`.
    pub trace_id: String,
    /// Authenticated user identifier (optional). Maps from `X-User-ID`.
    pub user_id: Option<String>,
    /// Organisation / tenant identifier (optional). Maps from `X-Org-ID`.
    pub org_id: Option<String>,
    /// Extensible key-value metadata bag (optional). Populated via builder.
    pub metadata: HashMap<String, String>,
}

/// Builder for [`Context`].
#[derive(Clone, Debug, Default)]
pub struct ContextBuilder {
    request_id: Option<String>,
    span_id: Option<String>,
    trace_id: Option<String>,
    user_id: Option<String>,
    org_id: Option<String>,
    metadata: HashMap<String, String>,
}

impl Context {
    /// Start building a new [`Context`].
    #[allow(clippy::new_ret_no_self)]
    pub fn new() -> ContextBuilder {
        ContextBuilder::default()
    }

    /// Extract a [`Context`] from known HTTP headers.
    ///
    /// Required headers:
    /// - `X-Request-ID`
    /// - `X-Trace-ID`
    /// - `X-Span-ID`
    ///
    /// Optional headers:
    /// - `X-User-ID`
    /// - `X-Org-ID`
    pub fn from_headers(headers: &HeaderMap) -> Result<Self, ContextError> {
        let request_id = extract_header(headers, "X-Request-ID")?;
        let trace_id = extract_header(headers, "X-Trace-ID")?;
        let span_id = extract_header(headers, "X-Span-ID")?;
        let user_id = extract_header_optional(headers, "X-User-ID");
        let org_id = extract_header_optional(headers, "X-Org-ID");

        Ok(Self {
            request_id,
            span_id,
            trace_id,
            user_id,
            org_id,
            metadata: HashMap::new(),
        })
    }
}

impl fmt::Display for Context {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "request_id={request_id}, span_id={span_id}, trace_id={trace_id}, user_id={user_id}, org_id={org_id}, metadata={metadata:?}",
            request_id = self.request_id,
            span_id = self.span_id,
            trace_id = self.trace_id,
            user_id = self.user_id.as_deref().unwrap_or("None"),
            org_id = self.org_id.as_deref().unwrap_or("None"),
            metadata = self.metadata,
        )
    }
}

impl ContextBuilder {
    /// Set the request identifier.
    pub fn with_request_id(mut self, request_id: impl Into<String>) -> Self {
        self.request_id = Some(request_id.into());
        self
    }

    /// Set the span identifier.
    pub fn with_span_id(mut self, span_id: impl Into<String>) -> Self {
        self.span_id = Some(span_id.into());
        self
    }

    /// Set the trace identifier.
    pub fn with_trace_id(mut self, trace_id: impl Into<String>) -> Self {
        self.trace_id = Some(trace_id.into());
        self
    }

    /// Set the user identifier.
    pub fn with_user_id(mut self, user_id: impl Into<String>) -> Self {
        self.user_id = Some(user_id.into());
        self
    }

    /// Set the organisation identifier.
    pub fn with_org_id(mut self, org_id: impl Into<String>) -> Self {
        self.org_id = Some(org_id.into());
        self
    }

    /// Insert a single key-value pair into the metadata bag.
    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self
    }

    /// Build the [`Context`], validating that all required fields are present.
    pub fn build(self) -> Result<Context, ContextError> {
        let request_id = self
            .request_id
            .ok_or_else(|| ContextError::MissingHeader("request_id".to_string()))?;
        let span_id = self
            .span_id
            .ok_or_else(|| ContextError::MissingHeader("span_id".to_string()))?;
        let trace_id = self
            .trace_id
            .ok_or_else(|| ContextError::MissingHeader("trace_id".to_string()))?;

        Ok(Context {
            request_id,
            span_id,
            trace_id,
            user_id: self.user_id,
            org_id: self.org_id,
            metadata: self.metadata,
        })
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn extract_header(headers: &HeaderMap, name: &str) -> Result<String, ContextError> {
    headers
        .get(name)
        .and_then(|v| v.to_str().ok())
        .map(String::from)
        .ok_or_else(|| ContextError::MissingHeader(name.to_string()))
}

fn extract_header_optional(headers: &HeaderMap, name: &str) -> Option<String> {
    headers
        .get(name)
        .and_then(|v| v.to_str().ok())
        .map(String::from)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use http::HeaderValue;
    use proptest::prelude::*;

    use super::*;

    #[test]
    fn builder_sets_all_fields() {
        let ctx = Context::new()
            .with_request_id("req-1")
            .with_span_id("span-1")
            .with_trace_id("trace-1")
            .with_user_id("user-1")
            .with_org_id("org-1")
            .with_metadata("key1", "val1")
            .with_metadata("key2", "val2")
            .build()
            .unwrap();

        assert_eq!(ctx.request_id, "req-1");
        assert_eq!(ctx.span_id, "span-1");
        assert_eq!(ctx.trace_id, "trace-1");
        assert_eq!(ctx.user_id, Some("user-1".to_string()));
        assert_eq!(ctx.org_id, Some("org-1".to_string()));
        assert_eq!(ctx.metadata.get("key1"), Some(&"val1".to_string()));
        assert_eq!(ctx.metadata.get("key2"), Some(&"val2".to_string()));
    }

    #[test]
    fn from_headers_extracts_known_headers() {
        let mut headers = HeaderMap::new();
        headers.insert("X-Request-ID", HeaderValue::from_static("req-42"));
        headers.insert("X-Trace-ID", HeaderValue::from_static("trace-42"));
        headers.insert("X-Span-ID", HeaderValue::from_static("span-42"));
        headers.insert("X-User-ID", HeaderValue::from_static("user-42"));
        headers.insert("X-Org-ID", HeaderValue::from_static("org-42"));

        let ctx = Context::from_headers(&headers).unwrap();
        assert_eq!(ctx.request_id, "req-42");
        assert_eq!(ctx.trace_id, "trace-42");
        assert_eq!(ctx.span_id, "span-42");
        assert_eq!(ctx.user_id, Some("user-42".to_string()));
        assert_eq!(ctx.org_id, Some("org-42".to_string()));
        assert!(ctx.metadata.is_empty());
    }

    #[test]
    fn from_headers_missing_request_id_returns_error() {
        let mut headers = HeaderMap::new();
        headers.insert("X-Trace-ID", HeaderValue::from_static("trace-42"));
        headers.insert("X-Span-ID", HeaderValue::from_static("span-42"));

        let err = Context::from_headers(&headers).unwrap_err();
        assert!(
            matches!(err, ContextError::MissingHeader(ref h) if h == "X-Request-ID"),
            "expected MissingHeader for X-Request-ID, got {err}"
        );
    }

    #[test]
    fn clone_preserves_all_fields() {
        let ctx = Context::new()
            .with_request_id("req-1")
            .with_span_id("span-1")
            .with_trace_id("trace-1")
            .with_user_id("user-1")
            .with_org_id("org-1")
            .with_metadata("k", "v")
            .build()
            .unwrap();

        let cloned = ctx.clone();
        assert_eq!(ctx, cloned);
    }

    #[test]
    fn display_renders_key_value_pairs() {
        let ctx = Context::new()
            .with_request_id("req-1")
            .with_span_id("span-1")
            .with_trace_id("trace-1")
            .with_user_id("user-1")
            .with_org_id("org-1")
            .with_metadata("k", "v")
            .build()
            .unwrap();

        let s = ctx.to_string();
        assert!(s.contains("request_id=req-1"), "display: {s}");
        assert!(s.contains("span_id=span-1"), "display: {s}");
        assert!(s.contains("trace_id=trace-1"), "display: {s}");
        assert!(s.contains("user_id=user-1"), "display: {s}");
        assert!(s.contains("org_id=org-1"), "display: {s}");
        assert!(s.contains("metadata={"), "display: {s}");
    }

    // -----------------------------------------------------------------------
    // Property-based tests (proptest)
    // -----------------------------------------------------------------------

    #[test]
    fn builder_roundtrip_property() {
        let config = ProptestConfig::with_cases(16);
        proptest!(config, |(request_id in "req-[0-9]{1,10}",
                            span_id in "span-[0-9]{1,10}",
                            trace_id in "trace-[0-9]{1,10}",
                            user_id in proptest::option::of("user-[0-9]{1,10}"),
                            org_id in proptest::option::of("org-[0-9]{1,10}"),
                            k1 in "key-[a-z]{1,5}",
                            v1 in "val-[a-z0-9]{1,10}")|
        {
            let mut builder = Context::new()
                .with_request_id(&request_id)
                .with_span_id(&span_id)
                .with_trace_id(&trace_id);

            if let Some(ref u) = user_id {
                builder = builder.with_user_id(u.as_str());
            }
            if let Some(ref o) = org_id {
                builder = builder.with_org_id(o.as_str());
            }

            let ctx = builder
                .with_metadata(k1.clone(), v1.clone())
                .build()
                .unwrap();

            assert_eq!(ctx.request_id, request_id);
            assert_eq!(ctx.span_id, span_id);
            assert_eq!(ctx.trace_id, trace_id);
            assert_eq!(ctx.user_id, user_id);
            assert_eq!(ctx.org_id, org_id);
            assert_eq!(ctx.metadata.get(&k1), Some(&v1));
        });
    }

    /// Building without a required field always returns an error.
    #[test]
    fn builder_missing_required_fields_errors() {
        // Missing request_id
        let err = Context::new()
            .with_span_id("s")
            .with_trace_id("t")
            .build()
            .unwrap_err();
        assert!(matches!(err, ContextError::MissingHeader(ref h) if h == "request_id"));

        // Missing span_id
        let err = Context::new()
            .with_request_id("r")
            .with_trace_id("t")
            .build()
            .unwrap_err();
        assert!(matches!(err, ContextError::MissingHeader(ref h) if h == "span_id"));

        // Missing trace_id
        let err = Context::new()
            .with_request_id("r")
            .with_span_id("s")
            .build()
            .unwrap_err();
        assert!(matches!(err, ContextError::MissingHeader(ref h) if h == "trace_id"));
    }
}
