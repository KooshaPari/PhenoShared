// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Cache module - High-performance in-memory cache

use std::collections::HashMap;
use std::sync::RwLock;
use std::time::{Duration, Instant};
use thiserror::Error;
use tracing::{debug, instrument};

/// Cache errors
#[derive(Debug, Error)]
pub enum CacheError {
    #[error("Key not found: {0}")]
    NotFound(String),

    /// Underlying I/O failure (poisoned lock serialised, etc).
    ///
    /// Traces to: FR-HELIOS-IO-010
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}

/// Cache configuration
#[derive(Debug, Clone)]
pub struct CacheConfig {
    pub max_capacity: u64,
    pub ttl_secs: u64,
    pub name: String,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self { max_capacity: 10_000, ttl_secs: 300, name: "default".to_string() }
    }
}

/// Cache entry
#[derive(Clone)]
struct Entry {
    value: Vec<u8>,
    expires_at: Instant,
}

/// Synchronous in-memory cache
pub struct Cache {
    store: RwLock<HashMap<String, Entry>>,
    ttl: Duration,
    max_capacity: u64,
    _name: String,
}

impl Cache {
    pub fn new(config: &CacheConfig) -> Self {
        Self {
            store: RwLock::new(HashMap::new()),
            ttl: Duration::from_secs(config.ttl_secs),
            max_capacity: config.max_capacity,
            _name: config.name.clone(),
        }
    }

    pub fn with_defaults() -> Self {
        Self::new(&CacheConfig::default())
    }

    /// Traces to: FR-HELIOS-CACHE-001
    #[instrument(skip(self), fields(key = %key))]
    pub fn get(&self, key: &str) -> Option<Vec<u8>> {
        let store = self.store.read().ok()?;
        store.get(key).and_then(|e| {
            if e.expires_at > Instant::now() {
                debug!("cache hit");
                Some(e.value.clone())
            } else {
                debug!("cache miss (expired)");
                None
            }
        })
    }

    /// Traces to: FR-HELIOS-CACHE-001
    #[instrument(skip(self), fields(key = %key))]
    pub fn get_str(&self, key: &str) -> Option<String> {
        self.get(key).and_then(|v| String::from_utf8(v).ok())
    }

    /// Traces to: FR-HELIOS-CACHE-001
    #[instrument(skip(self, value), fields(key = %key, value_len = value.len()))]
    pub fn set(&self, key: String, value: Vec<u8>) {
        // Evict if at capacity
        if let Ok(mut store) = self.store.write() {
            if store.len() >= self.max_capacity as usize {
                debug!(current_size = store.len(), "evicting expired entries");
                store.retain(|_, v| v.expires_at > Instant::now());
            }
            store.insert(key, Entry { value, expires_at: Instant::now() + self.ttl });
        }
    }

    /// Traces to: FR-HELIOS-CACHE-001
    #[instrument(skip(self), fields(key = %key))]
    pub fn remove(&self, key: &str) -> Option<Vec<u8>> {
        self.store.write().ok()?.remove(key).map(|e| e.value)
    }

    pub fn contains(&self, key: &str) -> bool {
        self.get(key).is_some()
    }

    pub fn clear(&self) {
        if let Ok(mut store) = self.store.write() {
            store.clear();
        }
    }

    pub fn len(&self) -> u64 {
        self.store.read().ok().map(|s| s.len() as u64).unwrap_or(0)
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

impl Default for Cache {
    fn default() -> Self {
        Self::with_defaults()
    }
}

/// Cache statistics
#[derive(Debug, Clone, Default)]
pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub evictions: u64,
}

impl CacheStats {
    pub fn hit_rate(&self) -> f64 {
        let total = self.hits + self.misses;
        if total == 0 {
            0.0
        } else {
            self.hits as f64 / total as f64
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cache_set_get() {
        let cache = Cache::with_defaults();
        cache.set("key1".to_string(), b"value1".to_vec());
        assert!(cache.get("key1").is_some());
    }

    #[test]
    fn test_cache_miss() {
        let cache = Cache::with_defaults();
        assert!(cache.get("nonexistent").is_none());
    }

    #[test]
    fn test_cache_remove() {
        let cache = Cache::with_defaults();
        cache.set("key1".to_string(), b"value1".to_vec());
        cache.remove("key1");
        assert!(cache.get("key1").is_none());
    }

    #[test]
    fn test_cache_str() {
        let cache = Cache::with_defaults();
        cache.set("key1".to_string(), b"value1".to_vec());
        assert_eq!(cache.get_str("key1"), Some("value1".to_string()));
    }

    /// Traces to: FR-HELIOS-IO-010
    /// `From<io::Error>` must produce the `Io` variant.
    #[test]
    fn from_io_error_maps_to_io_variant() {
        let io_err = std::io::Error::other("cache lock poisoned");
        let err: CacheError = io_err.into();
        assert!(matches!(err, CacheError::Io(_)));
    }

    /// Traces to: FR-HELIOS-IO-010
    /// Display must surface the underlying I/O message.
    #[test]
    fn io_error_display_includes_message() {
        let io_err = std::io::Error::other("disk full");
        let err: CacheError = io_err.into();
        assert!(err.to_string().contains("disk full"));
    }

    #[test]
    fn cache_expires_entries_after_ttl() {
        let cache = Cache::new(&CacheConfig { max_capacity: 10, ttl_secs: 0, name: "ttl".into() });
        cache.set("expiring".to_string(), b"value".to_vec());
        std::thread::sleep(std::time::Duration::from_millis(1));
        assert!(cache.get("expiring").is_none());
    }

    #[test]
    fn cache_len_and_contains_track_entries() {
        let cache = Cache::with_defaults();
        cache.set("a".to_string(), b"1".to_vec());
        cache.set("b".to_string(), b"2".to_vec());
        assert_eq!(cache.len(), 2);
        assert!(cache.contains("a"));
        cache.remove("a");
        assert!(!cache.contains("a"));
    }

    #[test]
    fn cache_clear_and_stats_helpers() {
        let cache = Cache::with_defaults();
        cache.set("key".to_string(), b"v".to_vec());
        assert!(!cache.is_empty());
        cache.clear();
        assert!(cache.is_empty());

        let stats = CacheStats { hits: 3, misses: 1, ..Default::default() };
        assert_eq!(stats.hit_rate(), 0.75);
        assert_eq!(CacheStats::default().hit_rate(), 0.0);
    }
}
