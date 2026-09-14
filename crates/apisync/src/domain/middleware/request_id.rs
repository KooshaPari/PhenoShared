//! Request-id middleware.
//!
//! Inspects the `X-Request-Id` header on incoming requests. If present, it is
//! echoed back on the response. If absent, a fresh id is generated. This is
//! the minimal observability hook expected by the v37 audit (L5/L27 — no
//! request-id propagation in the original transport).

use std::sync::atomic::{AtomicU64, Ordering};

use async_trait::async_trait;

use super::{Middleware, Next};
use crate::domain::{Request, Response};

const HEADER_NAME: &str = "X-Request-Id";

static COUNTER: AtomicU64 = AtomicU64::new(0);

/// Generate a fresh request id. The format is intentionally compact and
/// human-readable so it is easy to grep in logs.
fn fresh_id() -> String {
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let seq = COUNTER.fetch_add(1, Ordering::Relaxed);
    format!("req-{nanos:x}-{seq:x}")
}

fn extract(req: &Request) -> Option<String> {
    req.headers.iter().find(|(k, _)| k.eq_ignore_ascii_case(HEADER_NAME)).map(|(_, v)| v.clone())
}

/// Middleware that attaches a request id to every response.
pub struct RequestIdMiddleware;

#[async_trait]
impl<F> Middleware<F> for RequestIdMiddleware
where
    F: Fn(Request) -> std::pin::Pin<Box<dyn std::future::Future<Output = Response> + Send>>
        + Send
        + Sync
        + 'static,
{
    async fn handle(&self, request: Request, next: Next<F>) -> Response {
        let id = extract(&request).unwrap_or_else(fresh_id);
        let mut response = next.run(request).await;
        response.headers.push((HEADER_NAME.to_string(), id));
        response
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn echoes_inbound_request_id() {
        let req = Request::new("/items", "GET").with_header(HEADER_NAME, "abc-123");
        let id = extract(&req).unwrap();
        assert_eq!(id, "abc-123");
    }

    #[tokio::test]
    async fn stamps_response_with_request_id() {
        let middleware = RequestIdMiddleware;
        let req = Request::new("/items", "GET").with_header(HEADER_NAME, "abc-123");
        let next = Next::new(|_req| Box::pin(async { Response::ok() }));

        let resp = middleware.handle(req, next).await;

        assert_eq!(
            resp.headers.iter().find(|(k, _)| k == HEADER_NAME).map(|(_, v)| v.as_str()),
            Some("abc-123")
        );
    }

    #[tokio::test]
    async fn extract_returns_none_when_header_absent() {
        let req = Request::new("/items", "GET");
        assert!(extract(&req).is_none());
    }

    #[tokio::test]
    async fn extract_is_case_insensitive() {
        let req = Request::new("/items", "GET").with_header("x-request-id", "abc-123");
        assert_eq!(extract(&req), Some("abc-123".to_string()));
    }

    #[tokio::test]
    async fn stamps_response_with_generated_id_when_absent() {
        let middleware = RequestIdMiddleware;
        let req = Request::new("/items", "GET");
        let next = Next::new(|_req| Box::pin(async { Response::ok() }));

        let resp = middleware.handle(req, next).await;

        let id = resp.headers.iter().find(|(k, _)| k == HEADER_NAME).map(|(_, v)| v.as_str());
        assert!(id.is_some());
        assert!(id.unwrap().starts_with("req-"));
    }

    #[tokio::test]
    async fn fresh_id_is_unique() {
        let a = fresh_id();
        let b = fresh_id();
        assert_ne!(a, b);
        assert!(a.starts_with("req-"));
    }
}
