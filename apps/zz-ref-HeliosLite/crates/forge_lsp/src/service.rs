//! `DiagnosticsService` — composes a list of `DiagnosticsProvider`s
//! behind an LRU cache and a sync entry point. The async variant
//! `diagnostics_for_path_async` runs on a caller-provided `tokio`
//! runtime handle, so the sync path stays free of async dependencies
//! at the call sites that don't need them (e.g. the audit sink).

use std::collections::HashMap;
use std::num::NonZeroUsize;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use tokio::runtime::Handle;
use tokio::task;

use crate::diagnostic::Diagnostic;
use crate::provider::{DiagnosticsProvider, DiagnosticsResult};
use crate::rustc::RustcProvider;
use crate::tsc::TscProvider;

/// Type alias for the shared (cheap-clone) handle the rest of the
/// workspace uses to invoke the LSP layer.
pub type SharedDiagnosticsService = Arc<DiagnosticsService>;

/// Bounded LRU cache. Plain `HashMap`-backed — sufficient for the
/// agent's working-set scale (dozens of files, not millions).
#[derive(Debug)]
pub struct LruCache<K, V> {
    map: HashMap<K, V>,
    capacity: NonZeroUsize,
}

impl<K: Eq + std::hash::Hash + Clone, V: Clone> LruCache<K, V> {
    pub fn new(capacity: NonZeroUsize) -> Self {
        Self { map: HashMap::new(), capacity }
    }

    pub fn get(&self, key: &K) -> Option<V> {
        self.map.get(key).cloned()
    }

    pub fn insert(&mut self, key: K, value: V) {
        if self.map.len() >= self.capacity.get() {
            // Drop one entry at random — HashMap doesn't have
            // strict LRU semantics but for a working-set cache this
            // is fine. The eviction just removes an arbitrary entry.
            if let Some(k) = self.map.keys().next().cloned() {
                self.map.remove(&k);
            }
        }
        self.map.insert(key, value);
    }

    pub fn invalidate(&mut self, key: &K) {
        self.map.remove(key);
    }

    pub fn len(&self) -> usize {
        self.map.len()
    }

    pub fn is_empty(&self) -> bool {
        self.map.is_empty()
    }
}

impl<K, V> Default for LruCache<K, V>
where
    K: Eq + std::hash::Hash + Clone,
    V: Clone,
{
    fn default() -> Self {
        // 64 entries covers a normal agent working set comfortably.
        Self::new(NonZeroUsize::new(64).expect("64 > 0"))
    }
}

/// The diagnostics service. `Arc`-cloneable via `SharedDiagnosticsService`.
pub struct DiagnosticsService {
    providers: Vec<Box<dyn DiagnosticsProvider>>,
    cache: parking_lot_lite::Mutex<LruCache<PathBuf, Vec<Diagnostic>>>,
}

impl std::fmt::Debug for DiagnosticsService {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("DiagnosticsService")
            .field(
                "providers",
                &self.providers.iter().map(|p| p.name()).collect::<Vec<_>>(),
            )
            .field("cache_size", &self.cache.lock().len())
            .finish()
    }
}

impl DiagnosticsService {
    /// Build a service with the default provider set (rustc + tsc).
    pub fn with_defaults() -> Self {
        Self::new(vec![
            Box::new(RustcProvider::new()),
            Box::new(TscProvider::new()),
        ])
    }

    /// Build a service from an explicit provider set.
    pub fn new(providers: Vec<Box<dyn DiagnosticsProvider>>) -> Self {
        Self {
            providers,
            cache: parking_lot_lite::Mutex::new(LruCache::default()),
        }
    }

    /// Synchronously compute diagnostics for `path`. Hits the cache
    /// first; misses fall through to the first matching provider and
    /// cache the result.
    pub fn diagnostics_for_path(&self, path: &Path, workspace_root: &Path) -> DiagnosticsResult {
        if let Some(cached) = self.cache.lock().get(&path.to_path_buf()) {
            return Ok(cached);
        }
        for provider in &self.providers {
            if provider.supports(path) {
                let diags = provider.diagnostics(path, workspace_root)?;
                self.cache.lock().insert(path.to_path_buf(), diags.clone());
                return Ok(diags);
            }
        }
        // No provider supports this path — return an empty result so
        // the caller can proceed without diagnostics. (We don't cache
        // the empty result because supporting providers may be added
        // later without invalidating entries.)
        Ok(Vec::new())
    }

    /// Async variant — runs the blocking diagnostics on a tokio
    /// `blocking` thread pool so callers don't block the executor.
    pub async fn diagnostics_for_path_async(
        self: Arc<Self>,
        path: PathBuf,
        workspace_root: PathBuf,
    ) -> DiagnosticsResult {
        let path_for_blocking = path.clone();
        let workspace_for_blocking = workspace_root.clone();
        let me = Arc::clone(&self);
        task::spawn_blocking(move || {
            me.diagnostics_for_path(&path_for_blocking, &workspace_for_blocking)
        })
        .await
        .map_err(|e| format!("blocking task join error: {e}"))?
    }

    /// Run diagnostics for `path` using the supplied `tokio`
    /// runtime `Handle`. The blocking provider call is dispatched on
    /// that handle's blocking pool.
    pub fn diagnostics_for_path_with_handle(
        self: Arc<Self>,
        handle: &Handle,
        path: PathBuf,
        workspace_root: PathBuf,
    ) -> DiagnosticsResult {
        let path_for_blocking = path.clone();
        let workspace_for_blocking = workspace_root.clone();
        let me = Arc::clone(&self);
        handle.block_on(async move {
            me.diagnostics_for_path_async(path_for_blocking, workspace_for_blocking)
                .await
        })
    }

    /// Forget the cached diagnostics for `path`. Call this from the
    /// orchestrator after a Write/Patch so subsequent reads pick up
    /// the new content.
    pub fn invalidate(&self, path: &Path) {
        self.cache.lock().invalidate(&path.to_path_buf());
    }

    /// Current number of cached entries (useful for debugging).
    pub fn cache_len(&self) -> usize {
        self.cache.lock().len()
    }
}

/// Minimal hand-rolled `Mutex` to avoid pulling in `parking_lot`.
/// Wraps `std::sync::Mutex` so we get `Send` + `Sync` automatically.
mod parking_lot_lite {
    use std::sync::Mutex as StdMutex;

    #[derive(Debug)]
    pub struct Mutex<T>(StdMutex<T>);

    impl<T> Mutex<T> {
        pub fn new(value: T) -> Self {
            Self(StdMutex::new(value))
        }

        pub fn lock(&self) -> std::sync::MutexGuard<'_, T> {
            self.0.lock().expect("mutex poisoned")
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::diagnostic::DiagnosticSeverity;
    use crate::provider::{DiagnosticsProvider, DiagnosticsResult};
    use std::path::PathBuf;

    struct StubProvider(&'static str, &'static [&'static str]);
    impl DiagnosticsProvider for StubProvider {
        fn name(&self) -> &'static str {
            self.0
        }
        fn supports(&self, path: &Path) -> bool {
            path.extension()
                .and_then(|e| e.to_str())
                .map(|e| self.1.contains(&e))
                .unwrap_or(false)
        }
        fn diagnostics(&self, path: &Path, _workspace_root: &Path) -> DiagnosticsResult {
            Ok(vec![
                Diagnostic::new(path.to_path_buf(), DiagnosticSeverity::Warning, 1, self.0)
                    .with_source(self.0),
            ])
        }
    }

    #[test]
    fn lru_cache_holds_and_evicts() {
        let mut cache: LruCache<u32, u32> = LruCache::new(NonZeroUsize::new(2).unwrap());
        cache.insert(1, 100);
        cache.insert(2, 200);
        assert_eq!(cache.get(&1), Some(100));
        assert_eq!(cache.get(&2), Some(200));
        cache.insert(3, 300);
        assert_eq!(cache.len(), 2);
    }

    #[test]
    fn lru_cache_invalidates_entry() {
        let mut cache: LruCache<u32, u32> = LruCache::new(NonZeroUsize::new(4).unwrap());
        cache.insert(7, 700);
        cache.invalidate(&7);
        assert!(cache.get(&7).is_none());
    }

    #[test]
    fn diagnostics_for_path_picks_first_matching_provider() {
        let service = DiagnosticsService::new(vec![
            Box::new(StubProvider("a", &["rs"])),
            Box::new(StubProvider("b", &["ts"])),
            Box::new(StubProvider("c", &["tsx"])),
        ]);
        let rs_diags = service
            .diagnostics_for_path(&PathBuf::from("foo.rs"), &PathBuf::from("."))
            .unwrap();
        assert_eq!(rs_diags.len(), 1);
        assert_eq!(
            rs_diags.first().and_then(|d| d.source.as_deref()),
            Some("a")
        );

        let ts_diags = service
            .diagnostics_for_path(&PathBuf::from("foo.ts"), &PathBuf::from("."))
            .unwrap();
        assert_eq!(
            ts_diags.first().and_then(|d| d.source.as_deref()),
            Some("b")
        );
    }

    #[test]
    fn diagnostics_for_path_returns_empty_for_unsupported() {
        let service = DiagnosticsService::new(vec![Box::new(StubProvider("a", &["rs"]))]);
        let diags = service
            .diagnostics_for_path(&PathBuf::from("foo.py"), &PathBuf::from("."))
            .unwrap();
        assert!(diags.is_empty());
    }

    #[test]
    fn diagnostics_for_path_caches_results() {
        let service = DiagnosticsService::new(vec![Box::new(StubProvider("a", &["rs"]))]);
        let path = PathBuf::from("foo.rs");
        let _ = service
            .diagnostics_for_path(&path, &PathBuf::from("."))
            .unwrap();
        assert_eq!(service.cache_len(), 1);
        let _ = service
            .diagnostics_for_path(&path, &PathBuf::from("."))
            .unwrap();
        assert_eq!(service.cache_len(), 1);
        service.invalidate(&path);
        assert_eq!(service.cache_len(), 0);
    }

    #[test]
    fn with_defaults_registers_rustc_and_tsc() {
        let service = DiagnosticsService::with_defaults();
        let formatted = format!("{:?}", service);
        assert!(formatted.contains("rustc"));
        assert!(formatted.contains("tsc"));
    }

    #[test]
    fn shared_diagnostics_service_is_cheap_clone() {
        let shared: SharedDiagnosticsService = Arc::new(DiagnosticsService::with_defaults());
        let clone = Arc::clone(&shared);
        assert!(Arc::ptr_eq(&shared, &clone));
    }
}
