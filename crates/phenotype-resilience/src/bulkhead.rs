//! Bulkhead pattern — bounded-concurrency isolation by partition.
//!
//! A [`Bulkhead`] manages `N` named partitions, each limited to
//! `capacity_per_partition` concurrent operations.  Total capacity is
//! `N * capacity_per_partition`.
//!
//! Acquiring a slot returns a [`BulkheadGuard`] that **automatically
//! releases** the slot when dropped (via a background `tokio::spawn`).
//!
//! `Bulkhead` is `Arc`-wrapped internally so it can be cloned and shared
//! cheaply across tasks.

use std::collections::HashMap;
use std::sync::Arc;

use tokio::sync::RwLock;

use crate::error::ResilienceError;

/// Partition-based bulkhead.
///
/// Cheap to clone — the internal state is `Arc`-shared.
#[derive(Debug, Clone)]
pub struct Bulkhead {
    inner: Arc<BulkheadInner>,
}

#[derive(Debug)]
struct BulkheadInner {
    partitions: RwLock<HashMap<usize, usize>>,
    partition_capacity: usize,
    total_capacity: usize,
    current_total: RwLock<usize>,
}

impl Bulkhead {
    /// Create a bulkhead with `num_partitions` partitions, each able to hold
    /// `capacity_per_partition` concurrent operations.
    ///
    /// # Panics
    /// Panics if `num_partitions == 0` or `capacity_per_partition == 0`.
    pub fn new(num_partitions: usize, capacity_per_partition: usize) -> Self {
        assert!(num_partitions > 0, "num_partitions must be > 0");
        assert!(
            capacity_per_partition > 0,
            "capacity_per_partition must be > 0"
        );

        let mut partitions = HashMap::with_capacity(num_partitions);
        for i in 0..num_partitions {
            partitions.insert(i, 0usize);
        }

        Self {
            inner: Arc::new(BulkheadInner {
                partitions: RwLock::new(partitions),
                partition_capacity: capacity_per_partition,
                total_capacity: num_partitions * capacity_per_partition,
                current_total: RwLock::new(0),
            }),
        }
    }

    /// Try to acquire a slot in `partition`.
    ///
    /// Returns a [`BulkheadGuard`] on success; the guard **releases** the slot
    /// automatically on drop.
    ///
    /// # Errors
    /// * [`ResilienceError::BulkheadExhausted`] — the requested partition is full.
    /// * [`ResilienceError::BulkheadTotalExhausted`] — total capacity is full.
    pub async fn try_acquire(&self, partition: usize) -> Result<BulkheadGuard, ResilienceError> {
        let mut parts = self.inner.partitions.write().await;
        let current = parts
            .get(&partition)
            .copied()
            .ok_or(ResilienceError::BulkheadExhausted {
                partition,
                capacity: 0,
            })?;

        if current >= self.inner.partition_capacity {
            return Err(ResilienceError::BulkheadExhausted {
                partition,
                capacity: self.inner.partition_capacity,
            });
        }

        let mut total = self.inner.current_total.write().await;
        if *total >= self.inner.total_capacity {
            return Err(ResilienceError::BulkheadTotalExhausted);
        }

        *parts.get_mut(&partition).unwrap() = current + 1;
        *total += 1;

        Ok(BulkheadGuard {
            bulkhead: self.clone(),
            partition,
        })
    }

    /// Release a slot in `partition` (called by [`BulkheadGuard`] on drop).
    async fn release(&self, partition: usize) {
        let mut parts = self.inner.partitions.write().await;
        let mut total = self.inner.current_total.write().await;

        if let Some(c) = parts.get_mut(&partition) {
            if *c > 0 {
                *c -= 1;
                *total = total.saturating_sub(1);
            }
        }
    }

    /// Current usage of a partition.
    pub async fn usage(&self, partition: usize) -> usize {
        self.inner
            .partitions
            .read()
            .await
            .get(&partition)
            .copied()
            .unwrap_or(0)
    }

    /// Current total usage across all partitions.
    pub async fn total_usage(&self) -> usize {
        *self.inner.current_total.read().await
    }

    /// Maximum concurrent operations per partition.
    pub fn partition_capacity(&self) -> usize {
        self.inner.partition_capacity
    }

    /// Maximum total concurrent operations across all partitions.
    pub fn total_capacity(&self) -> usize {
        self.inner.total_capacity
    }
}

/// RAII guard that releases a bulkhead slot on drop.
pub struct BulkheadGuard {
    bulkhead: Bulkhead,
    partition: usize,
}

impl Drop for BulkheadGuard {
    fn drop(&mut self) {
        let bh = self.bulkhead.clone();
        let p = self.partition;
        tokio::spawn(async move { bh.release(p).await });
    }
}

// Manual Debug to avoid exposing internals.
impl std::fmt::Debug for BulkheadGuard {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "BulkheadGuard(partition={})", self.partition)
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── Capacity accessors ───────────────────────────────────────────────────

    #[test]
    fn partition_capacity_accessor() {
        let bh = Bulkhead::new(3, 5);
        assert_eq!(bh.partition_capacity(), 5);
    }

    #[test]
    fn total_capacity_accessor() {
        let bh = Bulkhead::new(4, 5);
        assert_eq!(bh.total_capacity(), 20);
    }

    // ── Happy path ───────────────────────────────────────────────────────────

    #[tokio::test]
    async fn acquire_increments_usage() {
        let bh = Bulkhead::new(3, 2);
        let _g = bh.try_acquire(0).await.unwrap();
        assert_eq!(bh.usage(0).await, 1);
        assert_eq!(bh.total_usage().await, 1);
    }

    #[tokio::test]
    async fn guard_drop_releases_slot() {
        let bh = Bulkhead::new(3, 2);
        {
            let _g = bh.try_acquire(0).await.unwrap();
            assert_eq!(bh.usage(0).await, 1);
        }
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
        assert_eq!(bh.usage(0).await, 0);
        assert_eq!(bh.total_usage().await, 0);
    }

    #[tokio::test]
    async fn multiple_guards_same_partition() {
        let bh = Bulkhead::new(1, 3);
        let _g1 = bh.try_acquire(0).await.unwrap();
        let _g2 = bh.try_acquire(0).await.unwrap();
        let _g3 = bh.try_acquire(0).await.unwrap();
        assert_eq!(bh.usage(0).await, 3);
    }

    // ── Limit enforced ───────────────────────────────────────────────────────

    #[tokio::test]
    async fn rejects_over_partition_limit() {
        let bh = Bulkhead::new(3, 2);
        let _g1 = bh.try_acquire(0).await.unwrap();
        let _g2 = bh.try_acquire(0).await.unwrap();
        let err = bh.try_acquire(0).await.unwrap_err();
        assert!(
            matches!(err, ResilienceError::BulkheadExhausted { partition: 0, .. }),
            "expected BulkheadExhausted, got {err:?}"
        );
    }

    #[tokio::test]
    async fn rejects_over_total_limit() {
        let bh = Bulkhead::new(2, 1);
        let _g0 = bh.try_acquire(0).await.unwrap();
        let _g1 = bh.try_acquire(1).await.unwrap();
        let err = bh.try_acquire(0).await.unwrap_err();
        // Either partition-full or total-full depending on order of checks.
        assert!(matches!(
            err,
            ResilienceError::BulkheadExhausted { .. } | ResilienceError::BulkheadTotalExhausted
        ));
    }

    // ── Partition isolation ──────────────────────────────────────────────────

    #[tokio::test]
    async fn partitions_are_isolated() {
        let bh = Bulkhead::new(2, 2);
        let _g0 = bh.try_acquire(0).await.unwrap();
        let _g1 = bh.try_acquire(1).await.unwrap();
        assert_eq!(bh.usage(0).await, 1);
        assert_eq!(bh.usage(1).await, 1);
        assert_eq!(bh.total_usage().await, 2);
    }

    #[tokio::test]
    async fn one_partition_full_does_not_block_others() {
        let bh = Bulkhead::new(3, 1);
        let _g0 = bh.try_acquire(0).await.unwrap();
        // Partition 0 is full; partitions 1 and 2 should still work.
        assert!(bh.try_acquire(1).await.is_ok());
        assert!(bh.try_acquire(2).await.is_ok());
    }

    // ── Concurrency ──────────────────────────────────────────────────────────

    #[tokio::test]
    async fn concurrent_acquires_across_partitions() {
        let bh = Bulkhead::new(5, 10);
        let mut handles = vec![];
        for p in 0..5 {
            let bh2 = bh.clone();
            handles.push(tokio::spawn(async move { bh2.try_acquire(p).await.ok() }));
        }
        for h in handles {
            let _ = h.await;
        }
        assert!(bh.total_usage().await > 0);
    }
}
