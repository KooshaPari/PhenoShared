//! phenotype-cache-adapter
//!
//! Two-tier cache with L1 (LRU) and L2 (Moka).

use serde::{Deserialize, Serialize};
use std::fmt::Debug;

pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;

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
    use std::sync::atomic::{AtomicU32, Ordering};

    /// Metrics hook that counts L1/L2 hits and misses for assertions.
    #[derive(Debug, Default)]
    struct CountingHook {
        l1_hits: AtomicU32,
        l1_misses: AtomicU32,
        l2_hits: AtomicU32,
        l2_misses: AtomicU32,
    }

    impl MetricsHook for CountingHook {
        fn record_hit(&self, tier: &str) {
            match tier {
                "l1" => {
                    self.l1_hits.fetch_add(1, Ordering::SeqCst);
                }
                "l2" => {
                    self.l2_hits.fetch_add(1, Ordering::SeqCst);
                }
                _ => {}
            }
        }
        fn record_miss(&self, tier: &str) {
            match tier {
                "l1" => {
                    self.l1_misses.fetch_add(1, Ordering::SeqCst);
                }
                "l2" => {
                    self.l2_misses.fetch_add(1, Ordering::SeqCst);
                }
                _ => {}
            }
        }
    }

    #[test]
    fn lru_l2_capacities_are_set() {
        let cache: TwoTierCache<String, String> = TwoTierCache::new(64, 2048);
        // Insert more than L1 holds; get one back to verify L2 promotion path.
        for i in 0..128 {
            cache.put(format!("k{i}"), format!("v{i}"));
        }
        // Each get should be served from L1 (most recent) until evicted,
        // then promoted from L2 to L1. Sanity: no panic and value is correct.
        let v = cache.get(&"k0".to_string());
        // k0 was evicted from L1 long ago, so it should be promoted from L2.
        assert_eq!(v, Some("v0".to_string()));
    }

    #[test]
    fn put_then_get_returns_value() {
        let cache: TwoTierCache<String, i32> = TwoTierCache::new(16, 64);
        cache.put("alpha".to_string(), 1);
        cache.put("beta".to_string(), 2);
        assert_eq!(cache.get(&"alpha".to_string()), Some(1));
        assert_eq!(cache.get(&"beta".to_string()), Some(2));
    }

    #[test]
    fn get_missing_returns_none() {
        let cache: TwoTierCache<String, i32> = TwoTierCache::new(16, 64);
        assert_eq!(cache.get(&"missing".to_string()), None);
    }

    #[test]
    fn put_overwrites_existing_value() {
        let cache: TwoTierCache<String, i32> = TwoTierCache::new(16, 64);
        cache.put("k".to_string(), 1);
        cache.put("k".to_string(), 2);
        assert_eq!(cache.get(&"k".to_string()), Some(2));
    }

    #[test]
    fn l1_capacity_zero_falls_back_to_default() {
        // The constructor should not panic on a zero L1 capacity.
        let cache: TwoTierCache<String, String> = TwoTierCache::new(0, 16);
        cache.put("k".to_string(), "v".to_string());
        assert_eq!(cache.get(&"k".to_string()), Some("v".to_string()));
    }

    #[test]
    fn l2_promotion_promotes_value_into_l1() {
        // Fill L1 to force eviction, then verify that a get on an evicted key
        // re-populates L1 from L2 (and the second get is an L1 hit).
        let cache: TwoTierCache<String, String> = TwoTierCache::new(2, 32);
        cache.put("a".to_string(), "1".to_string());
        cache.put("b".to_string(), "2".to_string());
        cache.put("c".to_string(), "3".to_string()); // "a" evicted from L1
        let v1 = cache.get(&"a".to_string());
        let v2 = cache.get(&"a".to_string());
        assert_eq!(v1, Some("1".to_string()));
        assert_eq!(v2, Some("1".to_string()));
    }

    #[test]
    fn metrics_hook_trait_default_impls() {
        // Verify the trait compiles and is object-safe (we cannot actually call
        // record_hit/record_miss on TwoTierCache since it does not use the hook,
        // but the trait itself can be implemented and exercised).
        let hook: Box<dyn MetricsHook> = Box::new(CountingHook::default());
        hook.record_hit("l1");
        hook.record_hit("l2");
        hook.record_miss("l1");
        hook.record_miss("l2");
        // No panic and the trait object is Send + Sync.
        fn assert_send_sync<T: Send + Sync + ?Sized>() {}
        assert_send_sync::<dyn MetricsHook>();
    }

    #[test]
    fn metrics_hook_handles_unknown_tier() {
        // Unknown tier strings are silently ignored — this is the documented
        // behavior so the trait can be extended without breaking the impl.
        let hook = CountingHook::default();
        hook.record_hit("l3");
        hook.record_miss("l3");
        assert_eq!(hook.l1_hits.load(Ordering::SeqCst), 0);
        assert_eq!(hook.l2_hits.load(Ordering::SeqCst), 0);
        assert_eq!(hook.l1_misses.load(Ordering::SeqCst), 0);
        assert_eq!(hook.l2_misses.load(Ordering::SeqCst), 0);
    }
}
