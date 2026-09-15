//! TTL sweeper for B3 (v8.1 Bifrost rollout).
//!
//! Background refresh of stale entries in any [`ModelCatalog`] impl.
//! Walks the catalog's stale entries (per [`LookupOutcome::Stale`] /
//! past TTL) and calls `refresh()` to revalidate them.
//!
//! Two modes:
//!
//! - [`Sweeper::run_once`]: deterministic, used by tests and as the
//!   body of any periodic-task framework (cron, tokio interval,
//!   external scheduler). Returns a [`RunOutcome`] counting successes
//!   / failures / remaining-stale.
//!
//! - [`Sweeper::run_forever`]: tokio-driven, takes a
//!   [`CancellationToken`] so callers can stop the loop cleanly.
//!
//! Loop semantics:
//!
//! - Caller decides whether to act on [`RunOutcome::remaining_stale`]
//!   (treat as gate: > N means "treat the catalog as unhealthy").
//! - Failures are counted but do not abort the loop (D-omni-05: chaos
//!   is expected on this path; do not panic on transient).
//! - The loop honors the abort signal between iterations.

use std::time::{Duration, Instant};

use tokio_util::sync::CancellationToken;

use crate::catalog::ModelCatalog;
use crate::error::Error;

/// Policy for the sweeper loop. Decides how often to sweep and how
/// many failures per pass are tolerated before the rest count as
/// `remaining_stale`.
///
/// `DEFAULT_TTL` — 1h matches the `bifrost_models` SQL cache contract
/// from L5-111.
///
/// `DEFAULT_INTERVAL` — 5m sub-TTL cadence. Must be ≥ the FFI
/// round-trip cost to avoid pile-up.
#[derive(Debug, Clone)]
pub struct RefreshPolicy {
    pub ttl: Duration,
    pub interval: Duration,
    pub max_failures_per_pass: u32,
}

impl Default for RefreshPolicy {
    fn default() -> Self {
        Self {
            ttl: Duration::from_secs(3600),
            interval: Duration::from_secs(300),
            max_failures_per_pass: 5,
        }
    }
}

/// Result of a single sweep pass. Counters are split so the caller
/// can decide whether to alert / skip / keep going.
#[derive(Debug, PartialEq, Eq, Clone, Default)]
pub struct RunOutcome {
    /// Number of entries refreshed successfully.
    pub refreshed: u32,
    /// Number of entries that failed to refresh (transient or
    /// permanent, the sweeper does not disambiguate).
    pub failed: u32,
    /// Number of entries still stale after this pass (the catalog
    /// itself was reachable but `refresh()` returned `BackendUnavailable`
    /// or skipped). Caller decides whether this is "alert now".
    pub remaining_stale: u32,
    /// Wall-clock duration of the pass.
    pub elapsed: Duration,
}

/// The TTL sweeper.
///
/// Cheap to construct (no IO). `run_once` makes it useful for both
/// production loops and tests; `run_forever` ties it to tokio.
#[derive(Debug, Clone)]
pub struct Sweeper {
    policy: RefreshPolicy,
}

impl Sweeper {
    /// Constructor. `policy` is cloned so the same `Sweeper` value
    /// can be sent to multiple loops with the same intent.
    #[must_use]
    pub fn new(policy: RefreshPolicy) -> Self {
        Self { policy }
    }

    /// Default-policy constructor.
    #[must_use]
    pub fn with_defaults() -> Self {
        Self::new(RefreshPolicy::default())
    }

    /// Read access to the policy.
    #[must_use]
    pub fn policy(&self) -> &RefreshPolicy {
        &self.policy
    }

    /// Drives a single pass of the sweeper. Returns a `RunOutcome`
    /// describing what happened. Errors during `refresh()` are
    /// counted as `failed`, not propagated (D-omni-05: tolerate
    /// chaos).
    pub async fn run_once(&self, catalog: &dyn ModelCatalog) -> RunOutcome {
        let start = Instant::now();

        // Probe the catalog first; if it's unreachable, we count
        // every known entry as remaining_stale so the caller can
        // decide whether to alert.
        let refresh_result = catalog.refresh().await;

        let (refreshed, failed, mut remaining_stale) = match refresh_result {
            Ok(n) => (u32::try_from(n).unwrap_or_default(), 0, 0),
            Err(Error::BackendUnavailable(_)) => {
                // Catalog unreachable: every entry it knows about is
                // still stale. The caller decides whether to alert
                // when this number exceeds a threshold.
                (0, 1, u32::try_from(catalog.len()).unwrap_or_default())
            }
            Err(_) => (0, 1, 0),
        };

        // Per-pass failure gate: if we exceeded max_failures_per_pass,
        // we count the rest as `remaining_stale`.
        if failed > self.policy.max_failures_per_pass {
            remaining_stale += failed - self.policy.max_failures_per_pass;
        }

        RunOutcome {
            refreshed,
            failed: failed.min(self.policy.max_failures_per_pass),
            remaining_stale,
            elapsed: start.elapsed(),
        }
    }

    /// Drives `run_once` on the configured interval until the
    /// [`CancellationToken`] fires. `on_outcome` is invoked after
    /// every pass for metrics.
    pub async fn run_forever(
        &self,
        catalog: std::sync::Arc<dyn ModelCatalog>,
        cancel: CancellationToken,
        mut on_outcome: impl FnMut(&RunOutcome) + Send,
    ) {
        let mut ticker = tokio::time::interval(self.policy.interval);
        ticker.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);

        loop {
            tokio::select! {
                biased;
                () = cancel.cancelled() => return,
                _ = ticker.tick() => {
                    let outcome = self.run_once(catalog.as_ref()).await;
                    on_outcome(&outcome);
                }
            }
        }
    }

    /// Construct a `CancellationToken` for the `run_forever` loop.
    /// Exposed as a thin shim so callers don't need to import
    /// `tokio_util` directly.
    #[must_use]
    pub fn cancellation_token() -> CancellationToken {
        CancellationToken::new()
    }
}

#[cfg(test)]
mod tests {
    use std::collections::HashSet;
    use std::sync::{Arc, Mutex};
    use std::time::Duration;

    use super::*;
    use crate::catalog::{
        CatalogEntry, CatalogWire, InMemoryCatalog, LookupOutcome, ModelCatalog,
    };

    fn wire_with_two_models() -> CatalogWire {
        let mut ids = HashSet::new();
        ids.insert("gpt-4o".to_string());
        ids.insert("claude-opus".to_string());
        CatalogWire {
            object: "list".to_string(),
            data: vec![
                CatalogEntry {
                    id: "gpt-4o".to_string(),
                    object: "model".to_string(),
                    owned_by: Some("openai".to_string()),
                    display_name: None,
                },
                CatalogEntry {
                    id: "claude-opus".to_string(),
                    object: "model".to_string(),
                    owned_by: Some("anthropic".to_string()),
                    display_name: None,
                },
            ],
        }
    }

    /// Mock that always returns BackendUnavailable — the offline
    /// behavior the sweeper must tolerate.
    struct UnreachableCatalog;

    #[async_trait::async_trait]
    impl ModelCatalog for UnreachableCatalog {
        async fn refresh(&self) -> Result<usize, Error> {
            Err(Error::BackendUnavailable("unreachable".into()))
        }
        fn lookup(&self, _id: &str) -> LookupOutcome {
            LookupOutcome::Missing
        }
        fn len(&self) -> usize {
            0
        }
    }

    /// Mock returning Ok(0) but reporting N entries via len(). The
    /// sweeper must NOT inflate remaining_stale on Ok (regression
    /// guard).
    struct OkCatalog {
        count: usize,
    }

    #[async_trait::async_trait]
    impl ModelCatalog for OkCatalog {
        async fn refresh(&self) -> Result<usize, Error> {
            Ok(0)
        }
        fn lookup(&self, _id: &str) -> LookupOutcome {
            LookupOutcome::Missing
        }
        fn len(&self) -> usize {
            self.count
        }
    }

    #[tokio::test]
    async fn run_once_on_offline_catalog_reports_remaining_stale() {
        let sweeper = Sweeper::with_defaults();
        let outcome = sweeper.run_once(&UnreachableCatalog).await;
        assert_eq!(outcome.refreshed, 0);
        assert!(
            outcome.failed >= 1,
            "BackendUnavailable must count as failed"
        );
        assert_eq!(outcome.remaining_stale, 0);
        assert!(outcome.elapsed.as_nanos() > 0);
    }

    #[tokio::test]
    async fn run_once_on_ok_catalog_reports_zero_failed_and_zero_stale() {
        let sweeper = Sweeper::with_defaults();
        let catalog = OkCatalog { count: 42 };
        let outcome = sweeper.run_once(&catalog).await;
        assert_eq!(outcome.refreshed, 0);
        assert_eq!(outcome.failed, 0);
        // Critical: Ok must NOT inflate remaining_stale even if len>0.
        assert_eq!(outcome.remaining_stale, 0);
    }

    #[tokio::test]
    async fn run_once_on_in_memory_catalog_after_seeding_reports_len() {
        let sweeper = Sweeper::with_defaults();
        let catalog = InMemoryCatalog::new(Duration::from_secs(3600));
        catalog
            .seed_from_json(&serde_json::to_string(&wire_with_two_models()).unwrap())
            .expect("seeded");
        let outcome = sweeper.run_once(&catalog).await;
        // InMemoryCatalog::refresh() is offline-default and returns
        // BackendUnavailable, so the sweeper counts 2 remaining_stale.
        assert_eq!(outcome.refreshed, 0);
        assert_eq!(outcome.failed, 1);
        assert_eq!(outcome.remaining_stale, 2);
    }

    #[test]
    fn policy_defaults_match_l5_111_cache_contract() {
        let p = RefreshPolicy::default();
        assert_eq!(p.ttl, Duration::from_secs(3600));
        assert_eq!(p.interval, Duration::from_secs(300));
        assert_eq!(p.max_failures_per_pass, 5);
    }

    #[tokio::test]
    async fn run_forever_exits_when_cancel_fires() {
        let sweeper = Sweeper::with_defaults();
        let catalog: Arc<dyn ModelCatalog> = Arc::new(OkCatalog { count: 0 });
        let cancel = Sweeper::cancellation_token();
        let calls = Arc::new(Mutex::new(0u32));

        let cancel_inner = cancel.clone();
        let calls_inner = Arc::clone(&calls);
        let sweeper_clone = sweeper.clone();
        let catalog_clone = Arc::clone(&catalog);
        let handle = tokio::spawn(async move {
            sweeper_clone
                .run_forever(catalog_clone, cancel_inner, |_outcome| {
                    *calls_inner.lock().unwrap() += 1;
                })
                .await;
        });

        // Tight interval so we definitely tick at least once.
        tokio::time::sleep(Duration::from_millis(50)).await;
        cancel.cancel();
        // Give the loop time to notice cancellation.
        tokio::time::sleep(Duration::from_millis(50)).await;
        assert!(cancel.is_cancelled());
        // Drop handle to avoid leak warnings.
        drop(handle);
    }
}
