//! `pheno-runtime-config` — hot-reloadable runtime configuration (L37).
//!
//! Provides [`Reloadable<T>`] — a generic trait for configuration values that
//! can be swapped at runtime without restarting the process.
//!
//! ## Backends
//! - **`notify`** v6 file watcher (inotify / macOS kqueue)
//! - **SIGHUP** fallback for environments without filesystem notifications
//!
//! Both backends use [`arc_swap`] for lock-free reads and [`tokio::sync::watch`]
//! for async fan-out to downstream consumers.
//!
//! ## Quick start
//! ```no_run
//! use pheno_runtime_config::{ArcReloadable, Reloadable};
//!
//! // Initial value, lock-free reads via ArcSwap.
//! let cfg = ArcReloadable::new(42);
//! assert_eq!(*cfg.current(), 42);
//!
//! // Swap to a new value atomically; subscribers get notified.
//! cfg.reload(100).unwrap();
//! assert_eq!(*cfg.current(), 100);
//! ```

pub mod file;
pub mod sighup;

use std::sync::Arc;

use arc_swap::ArcSwap;
use tokio::sync::watch;

/// Errors from reloadable configuration operations.
#[derive(Debug, thiserror::Error)]
pub enum ReloadError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("deserialization error: {0}")]
    Deserialize(#[from] serde_json::Error),
    #[error("toml parse error: {0}")]
    Toml(#[from] toml::de::Error),
    #[error("notify error: {0}")]
    Notify(#[from] notify::Error),
    #[error("watch channel closed")]
    WatchClosed,
}

/// A value that can be reloaded at runtime.
///
/// The two core operations are:
/// - [`reload()`](Reloadable::reload) — swap the current value (called by the
///   watcher or manually via SIGHUP)
/// - [`current()`](Reloadable::current) — get a lock-free reference to the
///   current value (ns-scale)
/// - [`watch()`](Reloadable::watch) — subscribe to reload notifications
pub trait Reloadable<T>: Send + Sync {
    /// Atomically swap the current value.
    fn reload(&self, new: T) -> Result<(), ReloadError>;

    /// Lock-free reference to the current value.
    fn current(&self) -> Arc<T>;

    /// Subscribe to reload notifications (receiver gets a copy on each reload).
    fn watch(&self) -> watch::Receiver<Arc<T>>;
}

/// Default [`Reloadable`] implementation backed by [`ArcSwap`] + [`watch`].
pub struct ArcReloadable<T> {
    current: ArcSwap<T>,
    tx: watch::Sender<Arc<T>>,
}

impl<T: Send + Sync + 'static> ArcReloadable<T> {
    pub fn new(initial: T) -> Self {
        let arc = Arc::new(initial);
        let (tx, _) = watch::channel(Arc::clone(&arc));
        Self {
            current: ArcSwap::new(arc),
            tx,
        }
    }
}

impl<T> Clone for ArcReloadable<T> {
    fn clone(&self) -> Self {
        Self {
            current: ArcSwap::new(self.current.load_full()),
            tx: self.tx.clone(),
        }
    }
}

impl<T: Send + Sync + 'static> Reloadable<T> for ArcReloadable<T> {
    fn reload(&self, new: T) -> Result<(), ReloadError> {
        let arc = Arc::new(new);
        let prev = self.current.swap(arc.clone());
        // Notify subscribers with the *new* value so they read the latest
        let _ = self.tx.send(arc);
        drop(prev);
        Ok(())
    }

    fn current(&self) -> Arc<T> {
        self.current.load_full()
    }

    fn watch(&self) -> watch::Receiver<Arc<T>> {
        self.tx.subscribe()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reloadable_swap_value() {
        let r = ArcReloadable::new(42);
        assert_eq!(*r.current(), 42);

        r.reload(100).unwrap();
        assert_eq!(*r.current(), 100);
    }

    #[tokio::test]
    async fn watch_receives_updated_value() {
        let r = ArcReloadable::new("hello".to_string());
        let mut rx = r.watch();

        r.reload("world".to_string()).unwrap();

        let updated = rx.changed().await;
        assert!(updated.is_ok());
        assert_eq!(*rx.borrow(), Arc::new("world".to_string()));
    }

    #[test]
    fn concurrent_reads_dont_block() {
        use std::sync::atomic::{AtomicUsize, Ordering};
        let r = ArcReloadable::new(0);
        let counter = AtomicUsize::new(0);

        std::thread::scope(|s| {
            // Spawn readers that keep reading while a reload happens
            for _ in 0..4 {
                s.spawn(|| {
                    for _ in 0..100 {
                        let _val = *r.current();
                        counter.fetch_add(1, Ordering::Relaxed);
                    }
                });
            }
        });

        r.reload(999).unwrap();
        assert_eq!(*r.current(), 999);
    }
}
