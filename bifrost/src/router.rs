//! Router port — the trait that any v1 / v1.5 router must satisfy.
//!
//! The v1 placeholder (`omni-router`) and the v1.5 Bifrost backend both
//! implement this trait. The dispatch loop in `omni-server` is therefore
//! router-agnostic; flipping D-omni-02 from "v1 placeholder" to "v1.5
//! Bifrost" is a single wiring change.

use async_trait::async_trait;
use serde::{Deserialize, Serialize};

use crate::error::Result;

/// Identifier of the upstream model to dispatch to (e.g. `gpt-4o-mini`,
/// `claude-sonnet-4-5`, `gemini-2.0-flash`). Provider is implied by the
/// registry; the model id is the routing key.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct RouteTarget {
    pub model_id: String,
    /// Free-form metadata (e.g. account id, region) preserved across
    /// router hops for tracing + cost attribution.
    #[serde(default)]
    pub metadata: std::collections::BTreeMap<String, String>,
}

impl RouteTarget {
    #[must_use]
    pub fn new(model_id: impl Into<String>) -> Self {
        Self {
            model_id: model_id.into(),
            metadata: std::collections::BTreeMap::new(),
        }
    }
}

/// The router contract used by the dispatch loop.
#[async_trait]
pub trait RouterPort: Send + Sync {
    /// Choose the next target for the request. Returns
    /// `Err(Error::NoMatch)` when no target matches.
    async fn pick(&self, request: &RouteRequest) -> Result<RouteTarget>;

    /// Record the outcome of a previous `pick`. Used by adaptive routing
    /// (latency / failure / cost feedback). May be a no-op for stateless
    /// implementations.
    async fn record_outcome(&self, target: &RouteTarget, outcome: &RouteOutcome) -> Result<()>;
}

/// Minimal request shape the router needs to make a decision.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouteRequest {
    pub requested_model: String,
    /// Optional tenant / API-key scoping for per-tenant routing rules.
    #[serde(default)]
    pub tenant: Option<String>,
    /// Optional hint from the classifier: `chat`, `embedding`, `image`,
    /// `audio`, etc. Routers may treat this as a tie-breaker.
    #[serde(default)]
    pub kind: Option<String>,
}

/// Outcome of a dispatch. Recorded for adaptive feedback.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouteOutcome {
    pub success: bool,
    #[serde(default)]
    pub latency_ms: Option<u64>,
    #[serde(default)]
    pub error: Option<String>,
}

/// Deterministic in-memory router. Used by v1 placeholder and by tests
/// when they need reproducible target selection without a live Bifrost.
#[derive(Debug, Clone, Default)]
pub struct InMemoryRouter {
    /// Map of `requested_model` -> ordered candidate `model_id`s.
    routes: std::collections::BTreeMap<String, Vec<RouteTarget>>,
    /// Round-robin cursors keyed by `requested_model`.
    cursors: std::collections::BTreeMap<String, usize>,
}

impl InMemoryRouter {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Register a fallback chain for `requested_model`. Candidates are
    /// tried in order; the first one whose `record_outcome(success=true)`
    /// was last seen becomes the preferred target.
    pub fn add_fallback(
        &mut self,
        requested_model: impl Into<String>,
        candidates: impl IntoIterator<Item = RouteTarget>,
    ) -> &mut Self {
        self.routes
            .entry(requested_model.into())
            .or_default()
            .extend(candidates);
        self
    }

    /// Bump the round-robin cursor for `requested_model`.
    fn rotate(&mut self, key: &str) {
        let entry = self.cursors.entry(key.to_string()).or_insert(0);
        *entry = entry.wrapping_add(1);
    }
}

#[async_trait]
impl RouterPort for InMemoryRouter {
    async fn pick(&self, request: &RouteRequest) -> Result<RouteTarget> {
        let key = &request.requested_model;
        let candidates = self
            .routes
            .get(key)
            .ok_or_else(|| crate::error::Error::NoMatch(key.clone()))?;
        if candidates.is_empty() {
            return Err(crate::error::Error::NoMatch(key.clone()));
        }
        let cursor = self.cursors.get(key).copied().unwrap_or(0);
        let idx = cursor % candidates.len();
        Ok(candidates[idx].clone())
    }

    async fn record_outcome(&self, _target: &RouteTarget, _outcome: &RouteOutcome) -> Result<()> {
        // Stateless; v1 placeholder never adjusts. The cursor is bumped in
        // a separate method to keep this trait impl pure.
        Ok(())
    }
}

impl InMemoryRouter {
    /// Manual round-robin advance; not part of the trait because it
    /// requires `&mut self`.
    pub fn advance(&mut self, key: &str) {
        self.rotate(key);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Error;

    #[tokio::test]
    async fn pick_returns_first_candidate_initially() {
        let mut r = InMemoryRouter::new();
        r.add_fallback(
            "gpt-4o",
            [RouteTarget::new("gpt-4o"), RouteTarget::new("gpt-4o-mini")],
        );
        let req = RouteRequest {
            requested_model: "gpt-4o".into(),
            tenant: None,
            kind: None,
        };
        let t = r.pick(&req).await.expect("first pick");
        assert_eq!(t.model_id, "gpt-4o");
    }

    #[tokio::test]
    async fn advance_rotates_candidates() {
        let mut r = InMemoryRouter::new();
        r.add_fallback(
            "claude-sonnet",
            [
                RouteTarget::new("claude-sonnet-4-5"),
                RouteTarget::new("claude-sonnet-4"),
                RouteTarget::new("claude-haiku-3-5"),
            ],
        );
        let req = RouteRequest {
            requested_model: "claude-sonnet".into(),
            tenant: None,
            kind: None,
        };
        let a = r.pick(&req).await.expect("a");
        r.advance("claude-sonnet");
        let b = r.pick(&req).await.expect("b");
        r.advance("claude-sonnet");
        let c = r.pick(&req).await.expect("c");
        assert_eq!(a.model_id, "claude-sonnet-4-5");
        assert_eq!(b.model_id, "claude-sonnet-4");
        assert_eq!(c.model_id, "claude-haiku-3-5");
    }

    #[tokio::test]
    async fn unknown_request_returns_no_match() {
        let r = InMemoryRouter::new();
        let req = RouteRequest {
            requested_model: "totally-unknown".into(),
            tenant: None,
            kind: None,
        };
        let err = r.pick(&req).await.unwrap_err();
        assert!(matches!(err, Error::NoMatch(_)));
    }

    #[tokio::test]
    async fn record_outcome_is_noop() {
        let r = InMemoryRouter::new();
        let outcome = RouteOutcome {
            success: true,
            latency_ms: Some(120),
            error: None,
        };
        r.record_outcome(&RouteTarget::new("gpt-4o"), &outcome)
            .await
            .expect("noop must succeed");
    }
}
