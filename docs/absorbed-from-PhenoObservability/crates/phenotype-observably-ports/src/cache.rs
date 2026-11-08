//! `CachePort` — hexagonal port for a key/value cache (e.g. Dragonfly/Redis).

use async_trait::async_trait;
use phenotype_error_core::RepositoryError;

/// Canonical error type for cache operations.
pub type CacheResult<T> = Result<T, RepositoryError>;

/// Port that any cache adapter must implement.
///
/// The surface deliberately mirrors the subset of Redis commands that
/// [`pheno_dragonfly::DragonflyClient`] exposes so the impl block is zero-cost.
#[async_trait]
pub trait CachePort: Send + Sync {
    /// Retrieve the raw bytes stored at `key`, or `None` if absent.
    async fn get(&self, key: &str) -> CacheResult<Option<Vec<u8>>>;

    /// Store `value` at `key` with an expiry of `ttl_seconds`.
    async fn set(&self, key: &str, value: &[u8], ttl_seconds: u64) -> CacheResult<()>;

    /// Remove the entry at `key`.  A no-op (not an error) when the key does
    /// not exist.
    async fn delete(&self, key: &str) -> CacheResult<()>;

    /// Refresh the TTL of an existing `key` to `ttl_seconds`.
    /// Returns `true` if the key existed and the TTL was updated.
    async fn expire(&self, key: &str, ttl_seconds: u64) -> CacheResult<bool>;
}
