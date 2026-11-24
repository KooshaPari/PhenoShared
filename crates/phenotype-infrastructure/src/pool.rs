//! Generic connection pooling

use crate::InfrastructureError;
use async_trait::async_trait;
use dashmap::DashMap;
use std::fmt::Debug;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{Mutex, Semaphore};

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

/// A pooled connection that returns to pool on drop
pub struct PooledConnection<C> {
    inner: Option<C>,
    pool: Arc<InnerPool<C>>,
    created_at: Instant,
}

impl<C> PooledConnection<C> {
    pub fn get(&self) -> &C {
        self.inner.as_ref().unwrap()
    }

    pub fn get_mut(&mut self) -> &mut C {
        self.inner.as_mut().unwrap()
    }
}

impl<C> Drop for PooledConnection<C> {
    fn drop(&mut self) {
        if let Some(conn) = self.inner.take() {
            self.pool.return_connection(conn, self.created_at);
        }
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
    connections: Mutex<Vec<(C, Instant)>>,
    sem: Semaphore,
    factory: Box<dyn ConnectionFactory<Connection = C>>,
    config: PoolConfig,
    in_use: DashMap<usize, Instant>,
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
            connections: Mutex::new(Vec::with_capacity(config.max_size)),
            sem: Semaphore::new(config.max_size),
            factory: Box::new(factory),
            config: config.clone(),
            in_use: DashMap::new(),
        });

        // Create minimum idle connections
        for _ in 0..config.min_idle {
            let conn = inner.factory.create().await?;
            inner.connections.lock().await.push((conn, Instant::now()));
        }

        Ok(Self { inner })
    }

    pub async fn acquire(&self) -> Result<PooledConnection<C>, InfrastructureError> {
        let _permit = tokio::time::timeout(
            self.inner.config.connection_timeout,
            self.inner.sem.acquire(),
        )
        .await
        .map_err(|_| InfrastructureError::Timeout("Pool acquire".to_string()))?
        .map_err(|_| InfrastructureError::PoolExhausted("semaphore closed".to_string()))?;

        let mut connections = self.inner.connections.lock().await;

        // Try to get an existing connection
        while let Some((mut conn, created_at)) = connections.pop() {
            // Check if connection is still valid
            if self.inner.factory.is_valid(&mut conn).await {
                let conn_id = &conn as *const C as usize;
                self.inner.in_use.insert(conn_id, Instant::now());

                return Ok(PooledConnection {
                    inner: Some(conn),
                    pool: self.inner.clone(),
                    created_at,
                });
            }
            // Connection is invalid, drop it and continue
        }

        // No valid connection, create a new one
        drop(connections); // Release lock before creating connection

        let conn = self.inner.factory.create().await?;
        let conn_id = &conn as *const C as usize;
        self.inner.in_use.insert(conn_id, Instant::now());

        Ok(PooledConnection {
            inner: Some(conn),
            pool: self.inner.clone(),
            created_at: Instant::now(),
        })
    }

    pub fn size(&self) -> usize {
        self.inner.connections.blocking_lock().len() + self.inner.in_use.len()
    }

    pub fn available(&self) -> usize {
        self.inner.sem.available_permits()
    }
}

impl<C> InnerPool<C> {
    fn return_connection(&self, conn: C, created_at: Instant) {
        let conn_id = &conn as *const C as usize;
        self.in_use.remove(&conn_id);

        // Check if connection is too old
        if created_at.elapsed() > self.config.max_lifetime {
            // Connection is too old, drop it
            return;
        }

        // Try to return to pool (best effort)
        let rt = tokio::runtime::Handle::try_current();
        if let Ok(rt) = rt {
            let connections = self.connections.clone();
            rt.spawn(async move {
                if let Ok(mut guard) = connections.try_lock() {
                    if guard.len() < guard.capacity() {
                        guard.push((conn, Instant::now()));
                    }
                }
            });
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
        assert_eq!(pool.available(), 10);
    }
}
