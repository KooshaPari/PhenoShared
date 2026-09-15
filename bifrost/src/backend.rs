//! Bifrost backend stub for v1.5.
//!
//! At scaffold time this crate contains only the failure stub. The real
//! implementation is sequenced as items B1-B9 of the v8.1 plan
//! (`PLAN.md` § 2.5.2). Until then, every `dispatch()` call returns
//! [`Error::BackendUnavailable`] so callers must fall back to the v1
//! `omni-router` placeholder.
//!
//! Once B1 lands, this module will be replaced with a `reqwest`-based
//! client that forwards chat completions to
//! `BIFROST_BASE_URL/v1/chat/completions` per `docs/frameworks/BIFROST-BACKEND.md`.
//!
//! As a `RouterPort` (B1 wiring), `pick()` is implemented as
//! `Err(BackendUnavailable)` so the dispatch loop routes through the
//! fallback. `record_outcome()` is a no-op because there is no live
//! gateway yet to feedback against.

use async_trait::async_trait;

use crate::error::{unavailable, Error, Result};
use crate::router::{RouteOutcome, RouteRequest, RouteTarget, RouterPort};

/// Stub client for the Bifrost gateway. Every operation fails until the
/// real implementation lands.
#[derive(Debug, Clone)]
pub struct BifrostBackend {
    base_url: String,
}

impl BifrostBackend {
    /// Construct a backend pinned to `base_url` (e.g.
    /// `http://127.0.0.1:8080`). The constructor never errors; runtime
    /// calls do.
    #[must_use]
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into(),
        }
    }

    /// The configured Bifrost gateway URL.
    #[must_use]
    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    /// Dispatch a request to the Bifrost gateway.
    ///
    /// # Errors
    ///
    /// Always returns `Err(Error::BackendUnavailable)` at scaffold time.
    /// When B1 lands, this will be the network or protocol-level error
    /// from the live gateway.
    pub fn dispatch(
        &self,
        _request: &RouteRequest,
        _target: &RouteTarget,
    ) -> std::future::Ready<Result<RouteOutcome>> {
        std::future::ready(Err(unavailable(format!(
            "bifrost backend stub at {} (B1-B9 not yet landed; \
             caller must fall back to omni-router)",
            self.base_url
        ))))
    }

    /// Health probe. Returns `Ok(true)` only when the real backend is wired;
    /// scaffold stub returns `Err(BackendUnavailable)` so health checks
    /// correctly report "not ready".
    ///
    /// # Errors
    ///
    /// Returns `Err(Error::BackendUnavailable)` because the gateway
    /// stub is not yet wired to a live endpoint.
    pub fn health(&self) -> std::future::Ready<Result<bool>> {
        std::future::ready(Err(Error::BackendUnavailable(format!(
            "{} (stub, not yet implemented)",
            self.base_url
        ))))
    }
}

impl Default for BifrostBackend {
    fn default() -> Self {
        Self::new("http://127.0.0.1:8080")
    }
}

#[async_trait]
impl RouterPort for BifrostBackend {
    async fn pick(&self, request: &RouteRequest) -> Result<RouteTarget> {
        // Scaffold-stub: the real B1 implementation will issue an HTTP
        // request to {base_url}/v1/models to resolve the target. Until
        // then we fail with BackendUnavailable so the FallbackRouter
        // adapter routes through the v1 placeholder.
        Err(unavailable(format!(
            "bifrost scaffold stub at {} (model={}, B1-B9 not yet landed)",
            self.base_url, request.requested_model
        )))
    }

    async fn record_outcome(&self, _target: &RouteTarget, _outcome: &RouteOutcome) -> Result<()> {
        // No live gateway to feedback against.
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_base_url_is_loopback_8080() {
        let b = BifrostBackend::default();
        assert_eq!(b.base_url(), "http://127.0.0.1:8080");
    }

    #[test]
    fn custom_base_url_is_held() {
        let b = BifrostBackend::new("http://bifrost.internal:9999");
        assert_eq!(b.base_url(), "http://bifrost.internal:9999");
    }

    #[tokio::test]
    async fn dispatch_returns_backend_unavailable() {
        let b = BifrostBackend::default();
        let req = RouteRequest {
            requested_model: "gpt-4o".into(),
            tenant: None,
            kind: None,
        };
        let tgt = RouteTarget::new("gpt-4o");
        let err = b.dispatch(&req, &tgt).await.unwrap_err();
        assert!(matches!(err, Error::BackendUnavailable(_)));
        assert!(err.is_retryable(), "BackendUnavailable must be retryable");
    }

    #[tokio::test]
    async fn health_returns_backend_unavailable() {
        let b = BifrostBackend::default();
        let err = b.health().await.unwrap_err();
        assert!(matches!(err, Error::BackendUnavailable(_)));
    }
}
