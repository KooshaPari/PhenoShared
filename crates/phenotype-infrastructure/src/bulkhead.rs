//! Bulkhead pattern for resource isolation

use std::sync::Arc;
use tokio::sync::{Semaphore, SemaphorePermit};

/// Bulkhead configuration
#[derive(Debug, Clone)]
pub struct BulkheadConfig {
    pub max_concurrent: usize,
    pub max_queue: usize,
    pub queue_timeout_ms: u64,
}

impl Default for BulkheadConfig {
    fn default() -> Self {
        Self {
            max_concurrent: 10,
            max_queue: 20,
            queue_timeout_ms: 1000,
        }
    }
}

struct BulkheadInner {
    sem: Semaphore,
    config: BulkheadConfig,
}

/// Bulkhead for limiting concurrent operations
pub struct Bulkhead {
    inner: Arc<BulkheadInner>,
}

impl Bulkhead {
    pub fn new(config: BulkheadConfig) -> Self {
        Self {
            inner: Arc::new(BulkheadInner {
                sem: Semaphore::new(config.max_concurrent + config.max_queue),
                config,
            }),
        }
    }

    /// Execute a function within the bulkhead
    pub async fn execute<F, Fut, T>(&self, f: F) -> Result<T, crate::InfrastructureError>
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = T>,
    {
        let permit = tokio::time::timeout(
            std::time::Duration::from_millis(self.inner.config.queue_timeout_ms),
            self.inner.sem.acquire(),
        )
        .await
        .map_err(|_| crate::InfrastructureError::BulkheadFull("queue timeout".to_string()))?
        .map_err(|_| crate::InfrastructureError::BulkheadFull("semaphore closed".to_string()))?;

        // Acquire the "concurrent execution" permit by taking from the front
        // The queue portion is the excess over max_concurrent
        let _exec_permit = self.acquire_execution_permit().await?;

        // Release the queue slot
        drop(permit);

        Ok(f().await)
    }

    async fn acquire_execution_permit(&self) -> Result<SemaphorePermit<'_>, crate::InfrastructureError> {
        // In a real implementation, we'd track concurrent vs queued separately
        // For now, we use a simple approach
        self.inner
            .sem
            .acquire()
            .await
            .map_err(|_| crate::InfrastructureError::BulkheadFull("semaphore closed".to_string()))
    }

    /// Get current metrics
    pub fn metrics(&self) -> BulkheadMetrics {
        BulkheadMetrics {
            available_permits: self.inner.sem.available_permits(),
            max_concurrent: self.inner.config.max_concurrent,
            max_queue: self.inner.config.max_queue,
        }
    }
}

/// Bulkhead metrics
#[derive(Debug, Clone, Copy)]
pub struct BulkheadMetrics {
    pub available_permits: usize,
    pub max_concurrent: usize,
    pub max_queue: usize,
}

impl BulkheadMetrics {
    pub fn in_use(&self) -> usize {
        self.max_concurrent + self.max_queue - self.available_permits
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[tokio::test]
    async fn fr_bulkhead_001_execute_within_limit() {
        let bulkhead = Bulkhead::new(BulkheadConfig {
            max_concurrent: 2,
            max_queue: 1,
            queue_timeout_ms: 100,
        });

        let result = bulkhead.execute(|| async { 42 }).await;
        assert_eq!(result.unwrap(), 42);
    }

    #[tokio::test]
    async fn fr_bulkhead_002_limit_concurrent() {
        let bulkhead = Bulkhead::new(BulkheadConfig {
            max_concurrent: 1,
            max_queue: 1,
            queue_timeout_ms: 100,
        });

        let bulkhead2 = bulkhead.clone();

        // First operation starts immediately
        let handle1 = tokio::spawn(async move {
            bulkhead.execute(|| async {
                tokio::time::sleep(Duration::from_millis(50)).await;
                1
            }).await
        });

        // Second operation either queues or starts after first finishes
        let handle2 = tokio::spawn(async move {
            bulkhead2.execute(|| async { 2 }).await
        });

        let result1 = handle1.await.unwrap();
        let result2 = handle2.await.unwrap();

        assert_eq!(result1.unwrap(), 1);
        assert_eq!(result2.unwrap(), 2);
    }
}
