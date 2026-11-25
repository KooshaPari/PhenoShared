//! Integration smoke test for `pheno-context`.
//!
//! Exercises the public API from an integration-test boundary
//! (outside-crate, linking against `pheno_context` as a consumer).

/// Verify the full builder API produces a valid Context.
#[test]
fn builder_roundtrip() {
    let ctx = pheno_context::Context::new()
        .with_request_id("req-42")
        .with_span_id("span-42")
        .with_trace_id("trace-42")
        .with_user_id("user-42")
        .with_org_id("org-42")
        .with_metadata("env", "prod")
        .with_metadata("region", "us-east-1")
        .build()
        .expect("builder with all required fields should succeed");

    assert_eq!(ctx.request_id, "req-42");
    assert_eq!(ctx.span_id, "span-42");
    assert_eq!(ctx.trace_id, "trace-42");
    assert_eq!(ctx.user_id, Some("user-42".to_string()));
    assert_eq!(ctx.org_id, Some("org-42".to_string()));
    assert_eq!(ctx.metadata.get("env"), Some(&"prod".to_string()));
    assert_eq!(ctx.metadata.get("region"), Some(&"us-east-1".to_string()));
}

/// Verify from_headers extracts headers correctly.
#[test]
fn from_headers() {
    let mut headers = http::HeaderMap::new();
    headers.insert("X-Request-ID", http::HeaderValue::from_static("req-1"));
    headers.insert("X-Trace-ID", http::HeaderValue::from_static("trace-1"));
    headers.insert("X-Span-ID", http::HeaderValue::from_static("span-1"));
    headers.insert("X-User-ID", http::HeaderValue::from_static("alice"));
    headers.insert("X-Org-ID", http::HeaderValue::from_static("acme-corp"));

    let ctx = pheno_context::Context::from_headers(&headers)
        .expect("from_headers with all required headers should succeed");

    assert_eq!(ctx.request_id, "req-1");
    assert_eq!(ctx.trace_id, "trace-1");
    assert_eq!(ctx.span_id, "span-1");
    assert_eq!(ctx.user_id, Some("alice".to_string()));
    assert_eq!(ctx.org_id, Some("acme-corp".to_string()));
    assert!(ctx.metadata.is_empty());
}

/// Verify that Context implements Clone and PartialEq.
#[test]
fn clone_and_eq() {
    let ctx = pheno_context::Context::new()
        .with_request_id("r")
        .with_span_id("s")
        .with_trace_id("t")
        .build()
        .unwrap();

    let cloned = ctx.clone();
    assert_eq!(ctx, cloned);
}

/// Verify that Display output contains all fields.
#[test]
fn display_contains_all_fields() {
    let ctx = pheno_context::Context::new()
        .with_request_id("r1")
        .with_span_id("s1")
        .with_trace_id("t1")
        .with_user_id("u1")
        .with_org_id("o1")
        .with_metadata("k", "v")
        .build()
        .unwrap();

    let display = ctx.to_string();
    assert!(display.contains("r1"), "display should contain request_id");
    assert!(display.contains("s1"), "display should contain span_id");
    assert!(display.contains("t1"), "display should contain trace_id");
    assert!(display.contains("u1"), "display should contain user_id");
    assert!(display.contains("o1"), "display should contain org_id");
}

/// Verify missing required headers produce an error.
#[test]
fn missing_required_headers() {
    let mut headers = http::HeaderMap::new();
    headers.insert("X-Trace-ID", http::HeaderValue::from_static("t"));
    headers.insert("X-Span-ID", http::HeaderValue::from_static("s"));

    let err = pheno_context::Context::from_headers(&headers).unwrap_err();
    assert!(
        matches!(err, pheno_context::ContextError::MissingHeader(ref h) if h == "X-Request-ID"),
        "expected MissingHeader for X-Request-ID, got {err}"
    );
}
