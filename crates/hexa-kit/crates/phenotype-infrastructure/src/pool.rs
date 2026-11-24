//! Generic connection pooling

use std::fmt::Debug;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::sync::Mutex as SyncMutex;
use std::time::{Duration, Instant};

use async_trait::async_trait;
use tokio::sync::{OwnedSemaphorePermit, Semaphore};

use crate::InfrastructureError;

/// Connection pool configuration
#[derive(Debug, Clone)]
pub struct PoolConfig {
    pub max_size: usize,
    pub min_idle: usize,
    pub max_lifetime: Duration,
    pub idle_timeout: Duration,
    pub connection_timeout: Duration,
}

impl Default for PoolConfig {
    fn default() -> Self {
        Self {
            max_size: 10,
            min_idle: 1,
            max_lifetime: Duration::from_secs(30 * 60),
            idle_timeout: Duration::from_secs(10 * 60),
            connection_timeout: Duration::from_secs(30),
        }
    }
}

/// A pooled connection that returns to pool on drop.
///
/// Holds a semaphore permit for the lifetime of the checkout so the pool
/// can enforce `max_size` concurrent connections.
pub struct PooledConnection<C>
where
    C: Send + 'static,
{
    inner: Option<C>,
    // Held for the lifetime of this connection. Dropped when the connection
    // returns to the pool, which releases the semaphore slot.
    _permit: Option<OwnedSemaphorePermit>,
    pool: Arc<InnerPool<C>>,
    created_at: Instant,
}

impl<C: Send + 'static> PooledConnection<C> {
    pub fn get(&self) -> &C {
        self.inner.as_ref().unwrap()
    }

    pub fn get_mut(&mut self) -> &mut C {
        self.inner.as_mut().unwrap()
    }
}

impl<C: Send + 'static> Drop for PooledConnection<C> {
    fn drop(&mut self) {
        if let Some(conn) = self.inner.take() {
            self.pool.return_connection(conn, self.created_at);
        }
        // _permit is dropped here, releasing the semaphore slot
    }
}

/// Connection factory trait
#[async_trait]
pub trait ConnectionFactory: Send + Sync + 'static {
    type Connection: Send + 'static;

    async fn create(&self) -> Result<Self::Connection, InfrastructureError>;
    async fn is_valid(&self, conn: &mut Self::Connection) -> bool;
}

struct InnerPool<C> {
    /// Available connections. Uses std::sync::Mutex so Drop can return connections
    /// without needing an async context.
    connections: SyncMutex<Vec<(C, Instant)>>,
    /// Semaphore that limits the total number of checked-out + idle connections.
    sem: Arc<Semaphore>,
    factory: Box<dyn ConnectionFactory<Connection = C>>,
    config: PoolConfig,
    /// Tracks how many connections are currently checked out.
    /// We use an atomic counter instead of pointer-based tracking because
    /// Rust moves change stack addresses, making pointer-based tracking unreliable.
    in_use_count: AtomicUsize,
}

/// Generic connection pool
pub struct ConnectionPool<C> {
    inner: Arc<InnerPool<C>>,
}

impl<C: Send + 'static> Clone for ConnectionPool<C> {
    fn clone(&self) -> Self {
        Self {
            inner: self.inner.clone(),
        }
    }
}

impl<C: Send + 'static> ConnectionPool<C> {
    pub async fn new<F>(factory: F, config: PoolConfig) -> Result<Self, InfrastructureError>
    where
        F: ConnectionFactory<Connection = C> + 'static,
    {
        let inner = Arc::new(InnerPool {
            connections: SyncMutex::new(Vec::with_capacity(config.max_size)),
            sem: Arc::new(Semaphore::new(config.max_size)),
            factory: Box::new(factory),
            config: config.clone(),
            in_use_count: AtomicUsize::new(0),
        });

        // Create minimum idle connections
        for _ in 0..config.min_idle {
            let conn = inner.factory.create().await?;
            inner
                .connections
                .lock()
                .unwrap()
                .push((conn, Instant::now()));
        }

        Ok(Self { inner })
    }

    pub async fn acquire(&self) -> Result<PooledConnection<C>, InfrastructureError> {
        // Acquire a semaphore permit for the lifetime of the connection checkout.
        // Using `acquire_owned` so the permit can be moved into PooledConnection.
        let permit = tokio::time::timeout(
            self.inner.config.connection_timeout,
            self.inner.sem.clone().acquire_owned(),
        )
        .await
        .map_err(|_| InfrastructureError::Timeout("Pool acquire".to_string()))?
        .map_err(|_| InfrastructureError::PoolExhausted("semaphore closed".to_string()))?;

        let mut connections = self.inner.connections.lock().unwrap();

        // Try to get an existing connection
        while let Some((mut conn, created_at)) = connections.pop() {
            // Check if connection is still valid
            if self.inner.factory.is_valid(&mut conn).await {
                self.inner.in_use_count.fetch_add(1, Ordering::SeqCst);

                return Ok(PooledConnection {
                    inner: Some(conn),
                    _permit: Some(permit),
                    pool: self.inner.clone(),
                    created_at,
                });
            }
            // Connection is invalid, drop it and continue
        }

        // No valid connection, create a new one
        drop(connections); // Release lock before creating connection

        let conn = self.inner.factory.create().await?;
        self.inner.in_use_count.fetch_add(1, Ordering::SeqCst);

        Ok(PooledConnection {
            inner: Some(conn),
            _permit: Some(permit),
            pool: self.inner.clone(),
            created_at: Instant::now(),
        })
    }

    /// Returns the total number of connections (idle + in-use).
    pub fn size(&self) -> usize {
        let idle = self
            .inner
            .connections
            .lock()
            .map(|guard| guard.len())
            .unwrap_or(0);
        idle + self.inner.in_use_count.load(Ordering::SeqCst)
    }

    /// Returns the number of available permits (idle slots).
    pub fn available(&self) -> usize {
        self.inner.sem.available_permits()
    }
}

impl<C> InnerPool<C> {
    fn return_connection(&self, conn: C, created_at: Instant)
    where
        C: Send + 'static,
    {
        self.in_use_count.fetch_sub(1, Ordering::SeqCst);

        // Check if connection is too old
        if created_at.elapsed() > self.config.max_lifetime {
            // Connection is too old, drop it
            return;
        }

        // Return connection to the pool synchronously.
        // This runs inside Drop, so we cannot use async Mutex.
        // std::sync::Mutex is safe here because the lock is held briefly.
        if let Ok(mut guard) = self.connections.lock() {
            if guard.len() < guard.capacity() {
                guard.push((conn, Instant::now()));
            }
            // If the guard is at capacity, the connection is silently dropped.
            // This is correct behavior — the pool is full.
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct TestFactory;

    #[async_trait]
    impl ConnectionFactory for TestFactory {
        type Connection = String;

        async fn create(&self) -> Result<Self::Connection, InfrastructureError> {
            Ok("test_conn".to_string())
        }

        async fn is_valid(&self, _conn: &mut Self::Connection) -> bool {
            true
        }
    }

    #[tokio::test]
    async fn fr_pool_001_create_pool() {
        let pool = ConnectionPool::new(TestFactory, PoolConfig::default())
            .await
            .unwrap();
        assert_eq!(pool.size(), 1); // min_idle = 1
    }

    #[tokio::test]
    async fn fr_pool_002_acquire_connection() {
        let pool = ConnectionPool::new(TestFactory, PoolConfig::default())
            .await
            .unwrap();

        let conn = pool.acquire().await.unwrap();
        assert_eq!(conn.get(), "test_conn");
        // Connection returns to pool on drop
        drop(conn);

        tokio::time::sleep(Duration::from_millis(10)).await;
        // After drop, the semaphore permit is released
        assert_eq!(pool.available(), 10);
    }

    #[tokio::test]
    async fn fr_pool_003_connection_returned_to_pool() {
        let pool = ConnectionPool::new(TestFactory, PoolConfig::default())
            .await
            .unwrap();

        // Acquire and release
        {
            let _conn = pool.acquire().await.unwrap();
            // conn drops here, returning to pool
        }

        // size should still be 1 (the returned idle connection) + 0 in use
        assert_eq!(pool.size(), 1);

        // Re-acquire should succeed
        let conn = pool.acquire().await.unwrap();
        assert_eq!(conn.get(), "test_conn");
    }

    #[tokio::test]
    async fn fr_pool_004_create_exhausted_timeout() {
        let config = PoolConfig {
            max_size: 2,
            min_idle: 0,
            connection_timeout: Duration::from_millis(50),
            ..Default::default()
        };
        let pool = ConnectionPool::new(TestFactory, config).await.unwrap();

        // Acquire both permits (held in PooledConnection)
        let _conn1 = pool.acquire().await.unwrap();
        let _conn2 = pool.acquire().await.unwrap();

        // Third acquire should time out because all permits are held
        let result = pool.acquire().await;
        assert!(result.is_err());
        let err = format!("{}", result.err().unwrap());
        assert!(
            err.contains("Timeout"),
            "expected Timeout error, got: {err}"
        );
    }
}
