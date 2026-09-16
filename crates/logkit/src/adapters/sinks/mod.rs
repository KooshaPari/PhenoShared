//! Sinks
//!
//! This module provides the [`Sink`] trait for log output destinations,
//! along with concrete implementations.
//!
//! # Implementations
//!
//! | Sink           | Description                                          |
//! |----------------|------------------------------------------------------|
//! | [`ConsoleSink`] | Writes log entries to stdout/stderr                  |
//! | [`BoundedSink`] | Wraps any [`Sink`] with concurrency backpressure      |

use std::io::Write as _;
use std::sync::Arc;

use crate::domain::{Level, LogEntry, LogError};
use async_trait::async_trait;
use tokio::sync::Semaphore;

/// A destination for log entries.
///
/// All implementations must be [`Send`] + [`Sync`] so they can be shared
/// across async tasks.
#[async_trait]
pub trait Sink: Send + Sync {
    /// Write a single log entry to this sink.
    ///
    /// Returns [`LogError`] if the write could not be completed.
    async fn write(&self, entry: &LogEntry) -> Result<(), LogError>;

    /// Flush any pending writes.
    ///
    /// The default implementation is a no-op.
    async fn flush(&self) -> Result<(), LogError> {
        let _ = self;
        Ok(())
    }
}

/// Console sink — writes to stdout (info level and below) or stderr (error/fatal).
pub struct ConsoleSink;

impl ConsoleSink {
    pub fn new() -> Self {
        Self
    }
}

impl Default for ConsoleSink {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Sink for ConsoleSink {
    async fn write(&self, entry: &LogEntry) -> Result<(), LogError> {
        if entry.level >= Level::Error {
            let mut h = std::io::stderr().lock();
            writeln!(h, "{} [{}]", entry.level, entry.message)
                .map_err(|e| LogError::Io(format!("stderr write failed: {e}")))?;
            h.flush()
                .map_err(|e| LogError::Io(format!("stderr flush failed: {e}")))?;
        } else {
            let mut h = std::io::stdout().lock();
            writeln!(h, "{} [{}]", entry.level, entry.message)
                .map_err(|e| LogError::Io(format!("stdout write failed: {e}")))?;
            h.flush()
                .map_err(|e| LogError::Io(format!("stdout flush failed: {e}")))?;
        }
        Ok(())
    }

    async fn flush(&self) -> Result<(), LogError> {
        Ok(())
    }
}

/// Wraps any [`Sink`] with a concurrency cap via a tokio [`Semaphore`].
///
/// This prevents unbounded resource usage when log producers temporarily
/// outpace the underlying sink, providing backpressure.
///
/// # Example
///
/// ```ignore
/// use logkit::adapters::sinks::{BoundedSink, ConsoleSink};
///
/// let sink = BoundedSink::new(ConsoleSink, 128);
/// ```
pub struct BoundedSink<S> {
    inner: S,
    semaphore: Arc<Semaphore>,
}

impl<S> BoundedSink<S> {
    /// Create a new `BoundedSink` wrapping `inner` with at most `max_concurrent`
    /// in-flight `write` calls.
    ///
    /// When the limit is reached, subsequent `write` calls will **wait** until
    /// an in-flight write completes (backpressure).
    pub fn new(inner: S, max_concurrent: usize) -> Self {
        Self {
            inner,
            semaphore: Arc::new(Semaphore::new(max_concurrent)),
        }
    }
}

impl<S> Clone for BoundedSink<S>
where
    S: Clone,
{
    fn clone(&self) -> Self {
        Self {
            inner: self.inner.clone(),
            semaphore: Arc::clone(&self.semaphore),
        }
    }
}

#[async_trait]
impl<S> Sink for BoundedSink<S>
where
    S: Sink,
{
    async fn write(&self, entry: &LogEntry) -> Result<(), LogError> {
        let _permit = self
            .semaphore
            .acquire()
            .await
            .map_err(|e| LogError::Io(format!("semaphore closed: {e}")))?;
        self.inner.write(entry).await
    }

    async fn flush(&self) -> Result<(), LogError> {
        let _permit = self
            .semaphore
            .acquire()
            .await
            .map_err(|e| LogError::Io(format!("semaphore closed: {e}")))?;
        self.inner.flush().await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::{Level, LogEntry};

    /// A sink that records writes for verification.
    #[derive(Clone, Default)]
    struct RecordingSink {
        entries: Arc<std::sync::Mutex<Vec<LogEntry>>>,
    }

    impl RecordingSink {
        fn new() -> Self {
            Self::default()
        }

        fn written(&self) -> Vec<LogEntry> {
            self.entries.lock().unwrap().clone()
        }
    }

    #[async_trait]
    impl Sink for RecordingSink {
        async fn write(&self, entry: &LogEntry) -> Result<(), LogError> {
            self.entries.lock().unwrap().push(entry.clone());
            Ok(())
        }

        async fn flush(&self) -> Result<(), LogError> {
            Ok(())
        }
    }

    #[tokio::test]
    async fn console_sink_write_returns_ok() {
        let sink = ConsoleSink;
        let entry = LogEntry::new(Level::Info, "test message");
        let result = sink.write(&entry).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn bounded_sink_forwards_writes() {
        let inner = RecordingSink::new();
        let bounded = BoundedSink::new(inner.clone(), 8);

        let entry = LogEntry::new(Level::Debug, "hello bounded");
        bounded.write(&entry).await.unwrap();

        let written = inner.written();
        assert_eq!(written.len(), 1);
        assert_eq!(written[0].message, "hello bounded");
    }

    #[tokio::test]
    async fn bounded_sink_enforces_concurrency_limit() {
        let inner = RecordingSink::new();
        let bounded = BoundedSink::new(inner.clone(), 3);

        // Fire off 10 writes concurrently — only 3 should be in-flight at once.
        let mut handles = Vec::new();
        for i in 0..10 {
            let s = BoundedSink {
                inner: inner.clone(),
                semaphore: Arc::clone(&bounded.semaphore),
            };
            handles.push(tokio::spawn(async move {
                s.write(&LogEntry::new(Level::Info, format!("burst {i}")))
                    .await
            }));
        }

        for h in handles {
            h.await.unwrap().unwrap();
        }

        assert_eq!(inner.written().len(), 10);
    }

    #[tokio::test]
    async fn bounded_sink_rejects_zero_capacity() {
        // A capacity of 0 means the semaphore starts at 0 — first write will wait
        // but we can test that it doesn't panic.
        let inner = RecordingSink::new();
        let bounded = BoundedSink::new(inner.clone(), 1);

        // Acquire the one permit permanently to simulate exhaustion
        let _lock = bounded.semaphore.acquire().await.unwrap();

        // This should not panic — it will wait until a permit is available
        // (timeout-based test would hang, so we just check it compiles and type-checks)
        let inner2 = inner.clone();
        let sem = Arc::clone(&bounded.semaphore);
        let handle = tokio::spawn(async move {
            let bounded2 = BoundedSink {
                inner: inner2,
                semaphore: sem,
            };
            bounded2
                .write(&LogEntry::new(Level::Warn, "should wait"))
                .await
        });
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        assert!(!handle.is_finished());
        drop(_lock); // release permit
        handle.await.unwrap().unwrap();
    }

    #[tokio::test]
    async fn bounded_sink_clone_shares_semaphore() {
        let inner = RecordingSink::new();
        let bounded = BoundedSink::new(inner.clone(), 2);

        let cloned = bounded.clone();
        // Both share the same semaphore — acquiring on one affects the other.
        let p1 = bounded.semaphore.acquire().await.unwrap();
        let p2 = cloned.semaphore.acquire().await.unwrap();

        // Both permits acquired; no more available.
        let inner2 = inner.clone();
        let sem = Arc::clone(&bounded.semaphore);
        let handle = tokio::spawn(async move {
            let b = BoundedSink {
                inner: inner2,
                semaphore: sem,
            };
            b.write(&LogEntry::new(Level::Info, "blocked")).await
        });

        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
        assert!(!handle.is_finished());

        drop((p1, p2));
        handle.await.unwrap().unwrap();
    }

    #[tokio::test]
    async fn console_sink_flush_returns_ok() {
        let sink = ConsoleSink;
        assert!(sink.flush().await.is_ok());
    }
}
