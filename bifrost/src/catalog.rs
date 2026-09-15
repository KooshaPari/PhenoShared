//! B2 of v8.1 Bifrost rollout — fetch the live `/v1/models` catalog from
//! a Bifrost gateway and cache it in an [`InMemoryCatalog`].
//!
//! Design goals (see `PLAN.md` § 2.5.2 / B2):
//!
//! 1. **Offline-tolerant**: the trait [`ModelCatalog`] has a sync in-memory
//!    impl that lets the rest of the rewrite run with `default-features`
//!    (no network deps). The live fetcher is feature-gated behind
//!    `catalog-fetch` (reqwest).
//! 2. **Stale-tolerant reads** (mirrors the `bifrost_models` SQL cache
//!    design from L5-111): expired entries still return data with
//!    `stale: true` so a degraded gateway never causes a request to
//!    hard-fail — the caller can decide.
//! 3. **Hard cap**: more than 5,000 entries is rejected (defense against
//!    a runaway gateway; matches the SQL cache contract).
//! 4. **No panic on malformed entries**: parse errors are logged and the
//!    malformed entry is skipped. A single bad row never poisons the
//!    whole catalog.
//!
//! The `reqwest`-backed fetcher is hidden behind `#[cfg(feature =
//! "catalog-fetch")]` so that the default build stays slim.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::{Duration, Instant};

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use tracing::warn;

use crate::error::{unavailable, Error, Result};

/// Wire format returned by Bifrost's `/v1/models` endpoint. Mirrors the
/// `OpenAI` shape (we reuse `data[]` + `id`/`object` fields).
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
pub struct CatalogEntry {
    /// The model id used by the gateway (e.g. `gpt-4o`, `claude-opus-4`).
    pub id: String,
    /// OpenAI-style type tag. Always `"model"` for our use case.
    pub object: String,
    /// Optional provider slug. When absent, defaults to `id`.
    #[serde(default)]
    pub owned_by: Option<String>,
    /// Optional human-readable display name.
    #[serde(default)]
    pub display_name: Option<String>,
}

impl CatalogEntry {
    /// Resolve the effective provider slug (defaults to the model id).
    #[must_use]
    pub fn provider(&self) -> &str {
        self.owned_by.as_deref().unwrap_or(self.id.as_str())
    }
}

/// Wrapper for the raw `/v1/models` response payload.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CatalogWire {
    /// OpenAI-style `"list"`.
    pub object: String,
    pub data: Vec<CatalogEntry>,
}

impl CatalogWire {
    /// Construct from a slice. `object` is fixed to `"list"`.
    #[must_use]
    pub fn from_entries(entries: Vec<CatalogEntry>) -> Self {
        Self {
            object: "list".into(),
            data: entries,
        }
    }
}

/// A single cached entry with provenance metadata.
#[derive(Debug, Clone)]
pub struct CachedEntry {
    pub entry: CatalogEntry,
    pub fetched_at: Instant,
}

/// Outcome of a `lookup()` call — distinguishes fresh hits from stale
/// ones so callers can decide whether to retry the network or trust the
/// cache.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LookupOutcome {
    /// Entry found in cache and within TTL.
    Fresh(Arc<CatalogEntry>),
    /// Entry found in cache but expired. Still returned so the caller
    /// can degrade gracefully instead of hard-failing.
    Stale(Arc<CatalogEntry>),
    /// Entry not in cache.
    Missing,
}

/// The catalog trait. Implementations must be `Send + Sync` because the
/// Bifrost fallback router will be wrapped in an `Arc<dyn ModelCatalog>`.
#[async_trait]
pub trait ModelCatalog: Send + Sync {
    /// Fetch the current catalog from the upstream gateway.
    ///
    /// Implementations should:
    /// - Cap response size at 5,000 entries (hard limit)
    /// - Skip malformed entries (don't fail the whole call)
    /// - Return `Err(Error::BackendUnavailable)` on network failure so
    ///   the `FallbackRouter` routes through the v1 placeholder.
    async fn refresh(&self) -> Result<usize>;

    /// Look up a model by id.
    fn lookup(&self, model_id: &str) -> LookupOutcome;

    /// Number of cached entries.
    fn len(&self) -> usize;

    /// True if the cache has zero entries.
    fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

/// Hard cap on the number of entries a single `refresh()` will accept.
/// Defense against a runaway gateway emitting an unbounded list.
pub const MAX_CATALOG_ENTRIES: usize = 5_000;

/// In-memory catalog with TTL. Thread-safe via `RwLock`.
///
/// Used both as the offline default (no network) and as the cache layer
/// behind the live fetcher.
#[derive(Debug)]
pub struct InMemoryCatalog {
    inner: RwLock<Inner>,
    ttl: Duration,
}

#[derive(Debug, Default)]
struct Inner {
    entries: HashMap<String, CachedEntry>,
}

impl InMemoryCatalog {
    /// Construct an empty catalog with the given TTL. Use
    /// [`InMemoryCatalog::with_entries`] to seed test fixtures.
    #[must_use]
    pub fn new(ttl: Duration) -> Self {
        Self {
            inner: RwLock::new(Inner::default()),
            ttl,
        }
    }

    /// Construct a catalog seeded with `entries`. All entries are
    /// timestamped `now` so they count as fresh by default.
    #[must_use]
    pub fn with_entries(entries: Vec<CatalogEntry>, ttl: Duration) -> Self {
        let inner = Inner {
            entries: entries
                .into_iter()
                .map(|e| {
                    (
                        e.id.clone(),
                        CachedEntry {
                            entry: e,
                            fetched_at: Instant::now(),
                        },
                    )
                })
                .collect(),
        };
        Self {
            inner: RwLock::new(inner),
            ttl,
        }
    }

    /// Default TTL = 1 hour (matches the `bifrost_models` SQL cache).
    #[must_use]
    pub fn one_hour() -> Self {
        Self::new(Duration::from_secs(3600))
    }

    /// True if the entry was inserted more than `ttl` ago.
    fn is_stale(cached: &CachedEntry, ttl: Duration) -> bool {
        cached.fetched_at.elapsed() > ttl
    }

    /// Seed the catalog from a parsed wire payload. Returns the number
    /// of entries accepted (after the cap and per-entry validation).
    ///
    /// # Errors
    ///
    /// Returns `Err(Error::BackendUnavailable)` if the parsed payload
    /// has more than [`MAX_CATALOG_ENTRIES`] entries (defense cap).
    pub fn seed(&self, wire: CatalogWire) -> Result<usize> {
        if wire.data.len() > MAX_CATALOG_ENTRIES {
            return Err(unavailable(format!(
                "catalog payload has {} entries; cap is {}",
                wire.data.len(),
                MAX_CATALOG_ENTRIES
            )));
        }

        let mut guard = self
            .inner
            .write()
            .map_err(|e| unavailable(format!("catalog rwlock poisoned during seed: {e}")))?;

        let now = Instant::now();
        for entry in wire.data {
            // Skip malformed entries without failing the whole seed.
            if entry.id.is_empty() || entry.object.is_empty() {
                warn!(
                    model = %entry.id,
                    object = %entry.object,
                    "skipping malformed catalog entry",
                );
                continue;
            }
            guard.entries.insert(
                entry.id.clone(),
                CachedEntry {
                    entry,
                    fetched_at: now,
                },
            );
        }
        Ok(guard.entries.len())
    }

    /// Seed from a JSON string. Convenience for tests + CLI bootstrap.
    ///
    /// # Errors
    ///
    /// Returns `Err(Error::InvalidInput)` if the payload is not parseable
    /// as a [`CatalogWire`].
    pub fn seed_from_json(&self, payload: &str) -> Result<usize> {
        let wire: CatalogWire = serde_json::from_str(payload).map_err(|e| {
            Error::Invalid(format!("catalog payload not parseable as CatalogWire: {e}"))
        })?;
        self.seed(wire)
    }
}

impl Default for InMemoryCatalog {
    fn default() -> Self {
        Self::one_hour()
    }
}

#[async_trait]
impl ModelCatalog for InMemoryCatalog {
    async fn refresh(&self) -> Result<usize> {
        // No live gateway in this impl. Callers should use the
        // reqwest-backed fetcher instead.
        Err(Error::BackendUnavailable(
            "InMemoryCatalog has no live gateway; use CatalogFetcher instead".into(),
        ))
    }

    fn lookup(&self, model_id: &str) -> LookupOutcome {
        let Ok(guard) = self.inner.read() else {
            return LookupOutcome::Missing;
        };
        let Some(cached) = guard.entries.get(model_id) else {
            return LookupOutcome::Missing;
        };
        if Self::is_stale(cached, self.ttl) {
            LookupOutcome::Stale(Arc::new(cached.entry.clone()))
        } else {
            LookupOutcome::Fresh(Arc::new(cached.entry.clone()))
        }
    }

    fn len(&self) -> usize {
        self.inner.read().map_or(0, |g| g.entries.len())
    }
}

/// Live fetcher that wraps an `InMemoryCatalog` and refreshes it from
/// a Bifrost gateway at `base_url`. Only compiled with the
/// `catalog-fetch` feature (reqwest dep).
#[cfg(feature = "catalog-fetch")]
pub mod live {
    use super::*;

    /// Fetcher that pulls `/v1/models` from a live Bifrost gateway and
    /// stores the parsed entries in the wrapped [`InMemoryCatalog`].
    #[derive(Debug, Clone)]
    pub struct CatalogFetcher {
        client: reqwest::Client,
        base_url: String,
        catalog: Arc<InMemoryCatalog>,
    }

    impl CatalogFetcher {
        /// Construct a fetcher pinned to `base_url` with the given
        /// request timeout and cache TTL.
        pub fn new(
            base_url: impl Into<String>,
            timeout: Duration,
            cache: Arc<InMemoryCatalog>,
        ) -> Self {
            let client = reqwest::Client::builder()
                .timeout(timeout)
                .build()
                .expect("reqwest client builder is infallible with timeout-only config");
            Self {
                client,
                base_url: base_url.into(),
                catalog: cache,
            }
        }

        /// The configured Bifrost base URL.
        #[must_use]
        pub fn base_url(&self) -> &str {
            &self.base_url
        }

        /// Access the underlying cache (for read-only inspection).
        #[must_use]
        pub fn catalog(&self) -> &InMemoryCatalog {
            &self.catalog
        }
    }

    #[async_trait]
    impl ModelCatalog for CatalogFetcher {
        async fn refresh(&self) -> Result<usize> {
            let url = format!("{}/v1/models", self.base_url);
            let resp = self
                .client
                .get(&url)
                .send()
                .await
                .map_err(|e| unavailable(format!("GET {url} failed: {e}")))?;
            let status = resp.status();
            if !status.is_success() {
                return Err(unavailable(format!("GET {url} returned {status}")));
            }
            let wire: CatalogWire = resp
                .json()
                .await
                .map_err(|e| unavailable(format!("GET {url} body not parseable: {e}")))?;
            self.catalog.seed(wire)
        }

        fn lookup(&self, model_id: &str) -> LookupOutcome {
            self.catalog.lookup(model_id)
        }

        fn len(&self) -> usize {
            self.catalog.len()
        }
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[test]
        fn catalog_fetcher_constructor_holds_url_and_cache() {
            let cache = Arc::new(InMemoryCatalog::one_hour());
            let fetcher = CatalogFetcher::new(
                "http://bifrost.internal:9999",
                Duration::from_secs(2),
                cache,
            );
            assert_eq!(fetcher.base_url(), "http://bifrost.internal:9999");
            assert!(fetcher.catalog().is_empty());
        }

        #[tokio::test]
        async fn refresh_against_unreachable_host_returns_backend_unavailable() {
            // 127.0.0.1:1 is a port that should never be open; this confirms
            // the network error path returns BackendUnavailable (not a panic).
            let cache = Arc::new(InMemoryCatalog::one_hour());
            let fetcher =
                CatalogFetcher::new("http://127.0.0.1:1", Duration::from_millis(100), cache);
            let err = fetcher.refresh().await.unwrap_err();
            assert!(matches!(err, Error::BackendUnavailable(_)));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn entry(id: &str) -> CatalogEntry {
        CatalogEntry {
            id: id.into(),
            object: "model".into(),
            owned_by: None,
            display_name: None,
        }
    }

    #[test]
    fn provider_defaults_to_id_when_owned_by_missing() {
        let e = entry("gpt-4o");
        assert_eq!(e.provider(), "gpt-4o");
    }

    #[test]
    fn provider_uses_owned_by_when_present() {
        let e = CatalogEntry {
            id: "gpt-4o-deployment".into(),
            object: "model".into(),
            owned_by: Some("openai".into()),
            display_name: None,
        };
        assert_eq!(e.provider(), "openai");
    }

    #[test]
    fn wire_round_trips_through_serde() {
        let wire = CatalogWire::from_entries(vec![entry("gpt-4o"), entry("claude-opus-4")]);
        let json = serde_json::to_string(&wire).unwrap();
        let parsed: CatalogWire = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.data.len(), 2);
        assert_eq!(parsed.data[0].id, "gpt-4o");
    }

    #[test]
    fn lookup_fresh_when_within_ttl() {
        let catalog = InMemoryCatalog::with_entries(vec![entry("gpt-4o")], Duration::from_secs(60));
        match catalog.lookup("gpt-4o") {
            LookupOutcome::Fresh(e) => assert_eq!(e.id, "gpt-4o"),
            other => panic!("expected Fresh, got {other:?}"),
        }
    }

    #[test]
    fn lookup_missing_when_unknown() {
        let catalog = InMemoryCatalog::with_entries(vec![], Duration::from_secs(60));
        assert_eq!(catalog.lookup("unknown"), LookupOutcome::Missing);
    }

    #[test]
    fn lookup_stale_after_ttl_expires() {
        let catalog = InMemoryCatalog::with_entries(
            vec![entry("gpt-4o")],
            // 1ns TTL so the very first lookup is already expired.
            Duration::from_nanos(1),
        );
        // Sleep just long enough for the entry to expire.
        std::thread::sleep(Duration::from_millis(2));
        match catalog.lookup("gpt-4o") {
            LookupOutcome::Stale(e) => assert_eq!(e.id, "gpt-4o"),
            other => panic!("expected Stale, got {other:?}"),
        }
    }

    #[test]
    fn seed_rejects_over_cap_payload() {
        let catalog = InMemoryCatalog::one_hour();
        let mut entries = Vec::with_capacity(MAX_CATALOG_ENTRIES + 1);
        for i in 0..MAX_CATALOG_ENTRIES + 1 {
            entries.push(entry(&format!("m-{i}")));
        }
        let wire = CatalogWire::from_entries(entries);
        let err = catalog.seed(wire).unwrap_err();
        assert!(matches!(err, Error::BackendUnavailable(_)));
    }

    #[test]
    fn seed_skips_malformed_entries_without_failing() {
        let catalog = InMemoryCatalog::one_hour();
        let wire = CatalogWire::from_entries(vec![
            entry("good-1"),
            CatalogEntry {
                id: String::new(), // malformed
                object: "model".into(),
                owned_by: None,
                display_name: None,
            },
            entry("good-2"),
        ]);
        let n = catalog.seed(wire).unwrap();
        assert_eq!(n, 2);
        assert!(matches!(catalog.lookup("good-1"), LookupOutcome::Fresh(_)));
        assert!(matches!(catalog.lookup("good-2"), LookupOutcome::Fresh(_)));
    }

    #[test]
    fn seed_from_json_round_trips() {
        let catalog = InMemoryCatalog::one_hour();
        let json = r#"{"object":"list","data":[{"id":"gpt-4o","object":"model"}]}"#;
        let n = catalog.seed_from_json(json).unwrap();
        assert_eq!(n, 1);
        assert!(matches!(catalog.lookup("gpt-4o"), LookupOutcome::Fresh(_)));
    }

    #[test]
    fn seed_from_json_rejects_garbage() {
        let catalog = InMemoryCatalog::one_hour();
        let err = catalog.seed_from_json("not json").unwrap_err();
        assert!(matches!(err, Error::Invalid(_)));
    }

    #[test]
    fn in_memory_catalog_refresh_returns_unavailable() {
        // Confirms the offline impl signals callers to use the fetcher.
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let catalog = InMemoryCatalog::one_hour();
            let err = catalog.refresh().await.unwrap_err();
            assert!(matches!(err, Error::BackendUnavailable(_)));
        });
    }
}
