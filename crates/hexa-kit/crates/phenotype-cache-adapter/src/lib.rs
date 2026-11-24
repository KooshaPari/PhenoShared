//! phenotype-cache-adapter
//!
//! Two-tier cache with L1 (LRU) and L2 (Moka), plus the `CacheAdapter` trait
//! that consuming crates (e.g. `phenotype-core`) re-export.

use serde::{Deserialize, Serialize};
use std::fmt::Debug;

pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;

/// Generic cache port trait.  Implement this on any backing store that should
/// be swappable without changing callsite code.
pub trait CacheAdapter: Send + Sync {
    type Key: Clone + Eq + std::hash::Hash + Send + Sync + Debug + 'static;
    type Value: Clone + Send + Sync + Debug + 'static;

    /// Retrieve a value by key.  Returns `None` on a miss.
    fn get(&self, key: &Self::Key) -> Option<Self::Value>;

    /// Insert or replace a value.
    fn put(&self, key: Self::Key, value: Self::Value);

    /// Remove a key, returning the previous value if it existed.
    fn remove(&self, key: &Self::Key) -> Option<Self::Value>;
}

/// Metrics hook for observability.
pub trait MetricsHook: Send + Sync + Debug {
    fn record_hit(&self, tier: &str);
    fn record_miss(&self, tier: &str);
}

#[derive(Clone, Serialize, Deserialize)]
struct CacheEntry<V> {
    value: V,
}

/// Two-tier cache implementation.
pub struct TwoTierCache<K, V>
where
    K: Clone + Eq + std::hash::Hash + Send + Sync + Debug + 'static,
    V: Clone + Send + Sync + Debug + 'static,
{
    l1: std::sync::Arc<std::sync::Mutex<lru::LruCache<K, CacheEntry<V>>>>,
    l2: moka::sync::Cache<K, CacheEntry<V>>,
}

impl<K, V> TwoTierCache<K, V>
where
    K: Clone + Eq + std::hash::Hash + Send + Sync + Debug + 'static,
    V: Clone + Send + Sync + Debug + 'static,
{
    pub fn new(l1_cap: usize, l2_cap: u64) -> Self {
        Self {
            l1: std::sync::Arc::new(std::sync::Mutex::new(lru::LruCache::new(
                std::num::NonZeroUsize::new(l1_cap)
                    .unwrap_or(std::num::NonZeroUsize::new(100).unwrap()),
            ))),
            l2: moka::sync::Cache::builder().max_capacity(l2_cap).build(),
        }
    }

    pub fn get(&self, key: &K) -> Option<V> {
        let mut l1 = self.l1.lock().unwrap();
        if let Some(entry) = l1.get(key) {
            return Some(entry.value.clone());
        }
        drop(l1);

        if let Some(entry) = self.l2.get(key) {
            let value = entry.value.clone();
            let mut l1 = self.l1.lock().unwrap();
            l1.put(
                key.clone(),
                CacheEntry {
                    value: value.clone(),
                },
            );
            return Some(value);
        }
        None
    }

    pub fn put(&self, key: K, value: V) {
        let mut l1 = self.l1.lock().unwrap();
        l1.put(
            key.clone(),
            CacheEntry {
                value: value.clone(),
            },
        );
        drop(l1);
        self.l2.insert(key, CacheEntry { value });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    /// Test metrics hook that counts hits and misses atomically.
    #[derive(Debug, Default)]
    struct TestMetrics {
        hits: AtomicUsize,
        misses: AtomicUsize,
    }

    impl MetricsHook for TestMetrics {
        fn record_hit(&self, _tier: &str) {
            self.hits.fetch_add(1, Ordering::SeqCst);
        }
        fn record_miss(&self, _tier: &str) {
            self.misses.fetch_add(1, Ordering::SeqCst);
        }
    }

    #[test]
    fn test_new_cache_returns_none() {
        let cache: TwoTierCache<String, String> = TwoTierCache::new(10, 100);
        assert!(cache.get(&"nonexistent".to_string()).is_none());
    }

    #[test]
    fn test_put_get_roundtrip() {
        let cache: TwoTierCache<String, String> = TwoTierCache::new(10, 100);
        cache.put("key1".to_string(), "value1".to_string());
        assert_eq!(cache.get(&"key1".to_string()), Some("value1".to_string()));
    }

    #[test]
    fn test_get_missing_key() {
        let cache: TwoTierCache<String, String> = TwoTierCache::new(10, 100);
        cache.put("key1".to_string(), "value1".to_string());
        assert!(cache.get(&"missing".to_string()).is_none());
    }

    #[test]
    fn test_overwrite_value() {
        let cache: TwoTierCache<String, String> = TwoTierCache::new(10, 100);
        cache.put("key1".to_string(), "value1".to_string());
        cache.put("key1".to_string(), "value2".to_string());
        assert_eq!(cache.get(&"key1".to_string()), Some("value2".to_string()));
    }

    #[test]
    fn test_multiple_keys() {
        let cache: TwoTierCache<String, i32> = TwoTierCache::new(10, 100);
        cache.put("a".to_string(), 1);
        cache.put("b".to_string(), 2);
        cache.put("c".to_string(), 3);
        assert_eq!(cache.get(&"a".to_string()), Some(1));
        assert_eq!(cache.get(&"b".to_string()), Some(2));
        assert_eq!(cache.get(&"c".to_string()), Some(3));
    }

    #[test]
    fn test_l1_eviction_falls_back_to_l2() {
        // L1 capacity of 1 means only 1 entry stays in L1 at a time.
        let cache: TwoTierCache<String, String> = TwoTierCache::new(1, 100);

        // Put two entries; only the latest fits in L1.
        cache.put("a".to_string(), "alpha".to_string());
        cache.put("b".to_string(), "beta".to_string());

        // 'a' is evicted from L1 but should still be reachable from L2.
        assert_eq!(cache.get(&"a".to_string()), Some("alpha".to_string()));
        // 'b' should be in L1 (most recent put).
        assert_eq!(cache.get(&"b".to_string()), Some("beta".to_string()));
    }

    #[test]
    fn test_integer_key_type() {
        let cache: TwoTierCache<u64, String> = TwoTierCache::new(10, 100);
        cache.put(42, "meaning of life".to_string());
        assert_eq!(cache.get(&42), Some("meaning of life".to_string()));
    }

    #[test]
    fn test_large_value() {
        let cache: TwoTierCache<i32, Vec<u8>> = TwoTierCache::new(10, 100);
        let large_val = vec![42u8; 4096];
        cache.put(1, large_val.clone());
        assert_eq!(cache.get(&1), Some(large_val));
    }

    #[test]
    fn test_zero_l1_capacity_defaults_to_100() {
        // When l1_cap is 0, NonZeroUsize fails and the code defaults to 100.
        let cache: TwoTierCache<String, String> = TwoTierCache::new(0, 100);
        // Insert 50 entries — all should fit in L1 (capacity defaults to 100).
        for i in 0..50 {
            cache.put(format!("key{i}"), format!("val{i}"));
        }
        for i in 0..50 {
            assert_eq!(cache.get(&format!("key{i}")), Some(format!("val{i}")));
        }
    }

    #[test]
    fn test_metrics_hook_trait_object() {
        // Verify MetricsHook is usable as a trait object (object-safe).
        let hook: Box<dyn MetricsHook> = Box::new(TestMetrics::default());
        hook.record_hit("l1");
        hook.record_miss("l2");
        // If this compiles and runs without panicking, the trait is object-safe.
    }

    #[test]
    fn test_concurrent_access() {
        use std::sync::Arc;
        use std::thread;

        let cache = Arc::new(TwoTierCache::<i32, i32>::new(100, 1000));
        let mut handles = vec![];

        for i in 0..20 {
            let cache = Arc::clone(&cache);
            handles.push(thread::spawn(move || {
                cache.put(i, i * 2);
            }));
        }

        for handle in handles {
            handle.join().expect("thread panicked");
        }

        for i in 0..20 {
            assert_eq!(cache.get(&i), Some(i * 2));
        }
    }
}
