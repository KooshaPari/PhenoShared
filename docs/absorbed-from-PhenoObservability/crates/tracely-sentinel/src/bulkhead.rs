//! # phenotype-sentinel
//!
//! Bulkhead isolation pattern implementation.

use std::collections::HashMap;
use std::sync::Arc;
use thiserror::Error;
use tokio::sync::RwLock;

/// Bulkhead error types.
#[derive(Debug, Error)]
pub enum BulkheadError {
    /// A specific partition has reached its capacity.
    #[error("Partition {0} exhausted")]
    PartitionExhausted(usize),

    /// The total capacity across all partitions is exhausted.
    #[error("Total capacity exhausted")]
    TotalExhausted,
}

/// Bulkhead for partition-based isolation
///
/// Limits concurrent access to resources by partitioning
/// them into isolated groups.
#[derive(Debug)]
pub struct Bulkhead {
    partitions: Arc<RwLock<HashMap<usize, usize>>>,
    partition_capacity: usize,
    total_capacity: usize,
    current_total: Arc<RwLock<usize>>,
}

impl Bulkhead {
    /// Create a new bulkhead wrapped in an Arc
    ///
    /// - `num_partitions`: Number of partitions
    /// - `capacity_per_partition`: Max concurrent operations per partition
    pub fn new(num_partitions: usize, capacity_per_partition: usize) -> Arc<Self> {
        let mut partitions = HashMap::new();
        for i in 0..num_partitions {
            partitions.insert(i, 0);
        }

        Arc::new(Self {
            partitions: Arc::new(RwLock::new(partitions)),
            partition_capacity: capacity_per_partition,
            total_capacity: num_partitions * capacity_per_partition,
            current_total: Arc::new(RwLock::new(0)),
        })
    }

    /// Try to acquire a permit in a partition
    pub async fn try_acquire(
        self: &Arc<Self>,
        partition: usize,
    ) -> Result<PartitionGuard, BulkheadError> {
        let mut partitions = self.partitions.write().await;
        let current = partitions.get(&partition).copied().unwrap_or(0);

        if current >= self.partition_capacity {
            return Err(BulkheadError::PartitionExhausted(partition));
        }

        let mut total = self.current_total.write().await;
        if *total >= self.total_capacity {
            return Err(BulkheadError::TotalExhausted);
        }

        partitions.insert(partition, current + 1);
        *total += 1;

        Ok(PartitionGuard { bulkhead: Arc::clone(self), partition })
    }

    /// Release a permit from a partition
    pub async fn release(&self, partition: usize) {
        let mut partitions = self.partitions.write().await;
        let mut total = self.current_total.write().await;

        if let Some(current) = partitions.get_mut(&partition) {
            if *current > 0 {
                *current -= 1;
                *total = total.saturating_sub(1);
            }
        }
    }

    /// Get current usage of a partition
    pub async fn usage(&self, partition: usize) -> usize {
        let partitions = self.partitions.read().await;
        partitions.get(&partition).copied().unwrap_or(0)
    }

    /// Get total current usage
    pub async fn total_usage(&self) -> usize {
        *self.current_total.read().await
    }

    /// Get partition capacity
    pub fn partition_capacity(&self) -> usize {
        self.partition_capacity
    }

    /// Get total capacity
    pub fn total_capacity(&self) -> usize {
        self.total_capacity
    }
}

// The BulkheadError enum is defined above with thiserror derive.

/// Partition guard that automatically releases on drop
pub struct PartitionGuard {
    bulkhead: Arc<Bulkhead>,
    partition: usize,
}

impl Drop for PartitionGuard {
    fn drop(&mut self) {
        // Spawn a task to release the partition
        let bulkhead = Arc::clone(&self.bulkhead);
        let partition = self.partition;
        tokio::spawn(async move {
            bulkhead.release(partition).await;
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-OBS-031
    #[tokio::test]
    async fn test_bulkhead_partition_limit() {
        let bulkhead = Bulkhead::new(3, 2);
        let _guard1 = bulkhead.try_acquire(0).await.unwrap();
        let _guard2 = bulkhead.try_acquire(0).await.unwrap();
        let result = bulkhead.try_acquire(0).await;
        assert!(result.is_err());
    }

    // Traces to: FR-OBS-032
    #[tokio::test]
    async fn test_bulkhead_guard_creation() {
        let bulkhead = Bulkhead::new(3, 2);
        let guard = bulkhead.try_acquire(0).await;
        assert!(guard.is_ok());
        assert_eq!(bulkhead.usage(0).await, 1);
    }

    // Traces to: FR-OBS-033
    #[tokio::test]
    async fn test_bulkhead_guard_release() {
        let bulkhead = Bulkhead::new(3, 2);
        {
            let _guard = bulkhead.try_acquire(0).await.unwrap();
            assert_eq!(bulkhead.usage(0).await, 1);
        }
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
        assert_eq!(bulkhead.usage(0).await, 0);
    }

    // Traces to: FR-OBS-033
    #[tokio::test]
    async fn test_bulkhead_acquire_release() {
        let bulkhead = Bulkhead::new(3, 2);
        {
            let _guard = bulkhead.try_acquire(0).await.unwrap();
            assert_eq!(bulkhead.usage(0).await, 1);
        }
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
        assert_eq!(bulkhead.usage(0).await, 0);
    }

    // Traces to: FR-OBS-034
    #[tokio::test]
    async fn test_bulkhead_multi_partition_isolation() {
        let bulkhead = Bulkhead::new(2, 2);
        let _g0 = bulkhead.try_acquire(0).await.unwrap();
        let _g1 = bulkhead.try_acquire(1).await.unwrap();
        assert_eq!(bulkhead.usage(0).await, 1);
        assert_eq!(bulkhead.usage(1).await, 1);
    }

    // Traces to: FR-OBS-034
    #[tokio::test]
    async fn test_bulkhead_prevent_over_allocation() {
        let bulkhead = Bulkhead::new(2, 1);
        let _guard1 = bulkhead.try_acquire(0).await.unwrap();
        let _guard2 = bulkhead.try_acquire(1).await.unwrap();
        let result = bulkhead.try_acquire(0).await;
        assert!(result.is_err());
    }

    // Traces to: FR-OBS-035
    #[test]
    fn test_bulkhead_config_validation() {
        let bulkhead = Bulkhead::new(3, 5);
        assert_eq!(bulkhead.partition_capacity(), 5);
        assert_eq!(bulkhead.total_capacity(), 15);
    }

    // Traces to: FR-OBS-036
    #[tokio::test]
    async fn test_bulkhead_concurrent_access() {
        let bulkhead = Bulkhead::new(5, 10);
        let mut handles = vec![];
        for partition in 0..5 {
            let bh = Arc::clone(&bulkhead);
            let handle = tokio::spawn(async move { bh.try_acquire(partition).await.ok() });
            handles.push(handle);
        }
        for handle in handles {
            let _ = handle.await;
        }
        assert!(bulkhead.total_usage().await > 0);
    }

    // Traces to: FR-OBS-037
    #[tokio::test]
    async fn test_bulkhead_exhausted_error() {
        let bulkhead = Bulkhead::new(1, 1);
        let _guard = bulkhead.try_acquire(0).await.unwrap();
        let result = bulkhead.try_acquire(0).await;
        assert!(result.is_err());
    }

    // Traces to: FR-OBS-037
    #[tokio::test]
    async fn test_bulkhead_partition_exhausted() {
        let bulkhead = Bulkhead::new(2, 1);
        let _guard1 = bulkhead.try_acquire(0).await.unwrap();
        let result = bulkhead.try_acquire(0).await;
        assert!(result.is_err());
    }

    // Traces to: FR-OBS-031
    #[tokio::test]
    async fn test_bulkhead_total_exhausted() {
        let bulkhead = Bulkhead::new(2, 1);
        let _guard1 = bulkhead.try_acquire(0).await.unwrap();
        let _guard2 = bulkhead.try_acquire(1).await.unwrap();
        let result = bulkhead.try_acquire(0).await;
        assert!(result.is_err());
    }

    // Traces to: FR-OBS-032
    #[tokio::test]
    async fn test_bulkhead_multiple_guards() {
        let bulkhead = Bulkhead::new(3, 3);
        let _g1 = bulkhead.try_acquire(0).await.unwrap();
        let _g2 = bulkhead.try_acquire(0).await.unwrap();
        let _g3 = bulkhead.try_acquire(0).await.unwrap();
        assert_eq!(bulkhead.usage(0).await, 3);
    }

    // Traces to: FR-OBS-034
    #[tokio::test]
    async fn test_bulkhead_isolation_between_partitions() {
        let bulkhead = Bulkhead::new(3, 5);
        for p in 0..3 {
            bulkhead.try_acquire(p).await.ok();
        }
        assert_eq!(bulkhead.total_usage().await, 3);
    }

    // Traces to: FR-OBS-031
    #[tokio::test]
    async fn test_bulkhead_capacity_per_partition() {
        let bulkhead = Bulkhead::new(2, 3);
        assert_eq!(bulkhead.partition_capacity(), 3);
    }

    // Traces to: FR-OBS-031
    #[tokio::test]
    async fn test_bulkhead_total_capacity() {
        let bulkhead = Bulkhead::new(4, 5);
        assert_eq!(bulkhead.total_capacity(), 20);
    }
}
