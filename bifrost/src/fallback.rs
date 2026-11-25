//! Fallback router adapter (B1).
//!
//! Composes a primary router with a fallback router. At scaffold time the
//! primary is `BifrostBackend` (which always returns `BackendUnavailable`)
//! and the fallback is `InMemoryRouter`. The adapter's contract:
//!
//! 1. Call `primary.pick(request)`. If it returns `Ok(target)`, use it.
//! 2. If it returns `Err(Error::BackendUnavailable)` — the documented
//!    "use fallback" signal — call `fallback.pick(request)` instead.
//! 3. Any other error from the primary propagates unchanged; we never
//!    silently swallow upstream failures (R-omni-1 mitigation).
//!
//! The `record_outcome` call always flows to BOTH routers so adaptive
//! feedback is preserved across both implementations.
//!
//! This module is the v1.5 plumbing that unblocks D-omni-02 (the
//! router swap). No network IO happens here; the only async work is
//! the `pick` and `record_outcome` calls.

use async_trait::async_trait;

use crate::backend::BifrostBackend;
use crate::error::{Error, Result};
use crate::router::{InMemoryRouter, RouteOutcome, RouteRequest, RouteTarget, RouterPort};

/// Adapter that tries a primary router first and falls back on
/// `BackendUnavailable`.
#[derive(Debug, Clone)]
pub struct FallbackRouter<P, F>
where
    P: RouterPort,
    F: RouterPort,
{
    primary: P,
    fallback: F,
}

impl FallbackRouter<BifrostBackend, InMemoryRouter> {
    /// Construct the canonical B1 adapter: Bifrost primary with an
    /// in-memory fallback.
    #[must_use]
    pub fn bifrost_with_in_memory(primary: BifrostBackend, fallback: InMemoryRouter) -> Self {
        Self { primary, fallback }
    }
}

impl<P, F> FallbackRouter<P, F>
where
    P: RouterPort,
    F: RouterPort,
{
    /// Construct a custom adapter (used by tests + future pairings).
    #[must_use]
    pub fn new(primary: P, fallback: F) -> Self {
        Self { primary, fallback }
    }

    /// Borrow the primary router.
    #[must_use]
    pub fn primary(&self) -> &P {
        &self.primary
    }

    /// Borrow the fallback router.
    #[must_use]
    pub fn fallback(&self) -> &F {
        &self.fallback
    }
}

#[async_trait]
impl<P, F> RouterPort for FallbackRouter<P, F>
where
    P: RouterPort,
    F: RouterPort,
{
    async fn pick(&self, request: &RouteRequest) -> Result<RouteTarget> {
        match self.primary.pick(request).await {
            Ok(target) => Ok(target),
            Err(Error::BackendUnavailable(_)) => self.fallback.pick(request).await,
            Err(other) => Err(other),
        }
    }

    async fn record_outcome(&self, target: &RouteTarget, outcome: &RouteOutcome) -> Result<()> {
        // Flow to both; the first error is returned, but we attempt both
        // so a transient failure in the primary doesn't block feedback to
        // the fallback.
        let primary_err = self.primary.record_outcome(target, outcome).await.err();
        let fallback_err = self.fallback.record_outcome(target, outcome).await.err();
        primary_err.or(fallback_err).map_or(Ok(()), Err)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::error::Error;
    use crate::router::{InMemoryRouter, RouteOutcome, RouteRequest, RouteTarget};

    fn req(model: &str) -> RouteRequest {
        RouteRequest {
            requested_model: model.into(),
            tenant: None,
            kind: None,
        }
    }

    #[tokio::test]
    async fn bifrost_unavailable_falls_back_to_in_memory() {
        let primary = BifrostBackend::default();
        let mut fallback = InMemoryRouter::new();
        fallback.add_fallback(
            "gpt-4o",
            [RouteTarget::new("gpt-4o"), RouteTarget::new("gpt-4o-mini")],
        );

        let router = FallbackRouter::bifrost_with_in_memory(primary, fallback);

        // Bifrost is in scaffold-stub state -> BackendUnavailable ->
        // fallback wins.
        let target = router
            .pick(&req("gpt-4o"))
            .await
            .expect("fallback succeeded");
        assert_eq!(target.model_id, "gpt-4o");
    }

    #[tokio::test]
    async fn non_backend_unavailable_error_propagates() {
        // Build a primary that always returns NoMatch (not BackendUnavailable).
        // The adapter must NOT swallow it.
        #[derive(Debug)]
        struct NoMatchPrimary;
        #[async_trait]
        impl RouterPort for NoMatchPrimary {
            async fn pick(&self, request: &RouteRequest) -> Result<RouteTarget> {
                Err(Error::NoMatch(request.requested_model.clone()))
            }
            async fn record_outcome(
                &self,
                _target: &RouteTarget,
                _outcome: &RouteOutcome,
            ) -> Result<()> {
                Ok(())
            }
        }

        let mut fallback = InMemoryRouter::new();
        fallback.add_fallback("gpt-4o", [RouteTarget::new("gpt-4o")]);

        let router = FallbackRouter::new(NoMatchPrimary, fallback);

        let err = router.pick(&req("gpt-4o")).await.unwrap_err();
        assert!(matches!(err, Error::NoMatch(_)), "got {err:?}");
    }

    #[tokio::test]
    async fn record_outcome_attempts_both_routers() {
        // Primary succeeds, fallback succeeds -> no error.
        #[derive(Debug)]
        struct OkPrimary;
        #[async_trait]
        impl RouterPort for OkPrimary {
            async fn pick(&self, request: &RouteRequest) -> Result<RouteTarget> {
                Ok(RouteTarget::new(request.requested_model.clone()))
            }
            async fn record_outcome(
                &self,
                _target: &RouteTarget,
                _outcome: &RouteOutcome,
            ) -> Result<()> {
                Ok(())
            }
        }

        let primary = OkPrimary;
        let fallback = InMemoryRouter::new();
        let router = FallbackRouter::new(primary, fallback);

        router
            .record_outcome(
                &RouteTarget::new("gpt-4o"),
                &RouteOutcome {
                    success: true,
                    latency_ms: Some(50),
                    error: None,
                },
            )
            .await
            .expect("both routers reported ok");
    }

    #[tokio::test]
    async fn record_outcome_propagates_first_error() {
        // Primary errors, fallback succeeds -> primary error returned.
        #[derive(Debug)]
        struct ErrPrimary;
        #[async_trait]
        impl RouterPort for ErrPrimary {
            async fn pick(&self, _request: &RouteRequest) -> Result<RouteTarget> {
                unreachable!("record_outcome test does not call pick")
            }
            async fn record_outcome(
                &self,
                _target: &RouteTarget,
                _outcome: &RouteOutcome,
            ) -> Result<()> {
                Err(Error::BackendUnavailable("primary boom".into()))
            }
        }

        let primary = ErrPrimary;
        let fallback = InMemoryRouter::new();
        let router = FallbackRouter::new(primary, fallback);

        let err = router
            .record_outcome(
                &RouteTarget::new("gpt-4o"),
                &RouteOutcome {
                    success: false,
                    latency_ms: None,
                    error: Some("upstream 500".into()),
                },
            )
            .await
            .unwrap_err();
        assert!(matches!(err, Error::BackendUnavailable(_)));
    }
}
