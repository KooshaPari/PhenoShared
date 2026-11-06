//! # Driven Ports (Secondary Ports)
//!
//! Interfaces that the domain defines and infrastructure must implement.
//!
//! These ports are consumed by the domain and implemented by adapters.

use crate::domain::entities::{CacheEntry, SingleflightRequest};
use crate::domain::value_objects::{CacheKey, CacheStats, CacheTier, CacheValue, Ttl};

/// Port for cache operations (DRIVEN)
///
/// ## CQRS: Queries
pub trait CachePort {
    /// Get a value from cache.
    fn get(&self, key: &CacheKey) -> Option<CacheValue>;

    /// Get entry metadata.
    fn get_entry(&self, key: &CacheKey) -> Option<CacheEntry>;
}

/// Port for cache operations (DRIVEN)
///
/// ## CQRS: Commands
pub trait CacheWritePort {
    /// Set a value in cache.
    fn set(&mut self, key: CacheKey, value: CacheValue) -> Result<(), CacheError>;

    /// Set a value with custom TTL.
    fn set_with_ttl(
        &mut self,
        key: CacheKey,
        value: CacheValue,
        ttl: Ttl,
    ) -> Result<(), CacheError>;

    /// Remove a key from cache.
    fn remove(&mut self, key: &CacheKey) -> Result<(), CacheError>;

    /// Clear all entries (optionally by tier).
    fn clear(&mut self, tier: Option<CacheTier>) -> Result<usize, CacheError>;
}

/// Port for singleflight operations (DRIVEN)
pub trait SingleflightPort<T> {
    /// Get or create a singleflight request.
    fn get_or_create(&mut self, key: &str) -> &mut SingleflightRequest<T>;

    /// Wait for a request to complete.
    fn wait(&self, key: &str) -> Option<&SingleflightRequest<T>>;

    /// Remove a completed request.
    fn remove(&mut self, key: &str);
}

/// Port for statistics (DRIVEN)
pub trait StatsPort {
    /// Get current statistics.
    fn get_stats(&self) -> CacheStats;

    /// Record a hit.
    fn record_hit(&mut self, tier: CacheTier);

    /// Record a miss.
    fn record_miss(&mut self);

    /// Record an eviction.
    fn record_eviction(&mut self);

    /// Reset statistics.
    fn reset(&mut self);
}

/// Port for cache eviction (DRIVEN)
pub trait EvictionPort {
    /// Evict expired entries.
    fn evict_expired(&mut self) -> usize;

    /// Evict LRU entries to make room.
    fn evict_lru(&mut self, count: usize) -> usize;

    /// Get current size.
    fn size(&self) -> usize;

    /// Get size of a specific tier.
    fn tier_size(&self, tier: CacheTier) -> usize;
}

/// Port for event publishing (DRIVEN)
pub trait EventPort {
    /// Publish a domain event.
    fn publish(&mut self, event: crate::domain::events::CacheEvent) -> Result<(), String>;
}

/// Cache error types
#[derive(Debug, Clone, thiserror::Error)]
pub enum CacheError {
    #[error("Key not found: {0}")]
    NotFound(String),

    #[error("Key already exists: {0}")]
    AlreadyExists(String),

    #[error("Cache full: cannot evict to make room")]
    CacheFull,

    #[error("Serialization error: {0}")]
    SerializationError(String),

    #[error("IO error: {0}")]
    IoError(String),

    #[error("Invalid TTL: {0}")]
    InvalidTtl(String),
}
