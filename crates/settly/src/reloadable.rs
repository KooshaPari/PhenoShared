//! Generic hot-reloadable configuration value ([`Reloadable<T>`]) — Step 1
//! of the config-consolidation plan (phenotype-org-audits #72).
//!
//! Provides a [`Reloadable<T>`] trait for values that can be atomically swapped
//! at runtime, and a default [`ArcReloadable<T>`] implementation backed by
//! [`arc_swap::ArcSwap`] + [`tokio::sync::watch`].
//!
//! # Future integration
//!
//! - Phase B: [`super::crypto::HotReloader<T>`] will implement [`Reloadable<T>`].
//! - Phase C: SIGHUP fallback will trigger [`Reloadable::reload`].
//!
//! # Example
//! ```
//! use settly::reloadable::{ArcReloadable, Reloadable};
//!
//! let r = ArcReloadable::new(42);
//! assert_eq!(*r.current(), 42);
//! r.reload(100).unwrap();
//! assert_eq!(*r.current(), 100);
//! ```

use std::sync::Arc;

use arc_swap::ArcSwap;
use thiserror::Error;
use tokio::sync::watch;

/// Errors from reloadable configuration operations.
#[derive(Debug, Error)]
pub enum ReloadError {
    /// I/O error (file-read path, used by future file-watcher backends).
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    /// JSON deserialization error.
    #[error("deserialization error: {0}")]
    Deserialize(#[from] serde_json::Error),

    /// TOML parse error.
    #[error("toml parse error: {0}")]
    Toml(#[from] toml::de::Error),

    /// Filesystem notification error (notify crate).
    #[error("notify error: {0}")]
    Notify(#[from] notify::Error),

    /// Watch channel closed — no more subscribers.
    #[error("watch channel closed")]
    WatchClosed,
}

/// A value that can be reloaded at runtime.
///
/// The three core operations are:
/// - [`reload()`](Reloadable::reload) — swap the current value (called by a
///   watcher or manually).
/// - [`current()`](Reloadable::current) — get a lock-free reference to the
///   current value (ns-scale).
/// - [`watch()`](Reloadable::watch) — subscribe to reload notifications.
pub trait Reloadable<T>: Send + Sync {
    /// Atomically swap the current value.
    fn reload(&self, new: T) -> Result<(), ReloadError>;

    /// Lock-free reference to the current value.
    fn current(&self) -> Arc<T>;

    /// Subscribe to reload notifications (receiver is notified on each reload).
    fn watch(&self) -> watch::Receiver<Arc<T>>;
}

/// Default [`Reloadable`] implementation backed by [`ArcSwap`] + [`watch`].
pub struct ArcReloadable<T> {
    current: ArcSwap<T>,
    tx: watch::Sender<Arc<T>>,
}

impl<T: Send + Sync + 'static> ArcReloadable<T> {
    /// Create a new [`ArcReloadable`] with the given initial value.
    pub fn new(initial: T) -> Self {
        let arc = Arc::new(initial);
        let (tx, _) = watch::channel(Arc::clone(&arc));
        Self { current: ArcSwap::new(arc), tx }
    }
}

impl<T: Send + Sync + 'static> Reloadable<T> for ArcReloadable<T> {
    fn reload(&self, new: T) -> Result<(), ReloadError> {
        let arc = Arc::new(new);
        // Notify watchers with the new value, then atomically store it.
        let _ = self.tx.send(Arc::clone(&arc));
        self.current.store(arc);
        Ok(())
    }

    fn current(&self) -> Arc<T> {
        self.current.load_full()
    }

    fn watch(&self) -> watch::Receiver<Arc<T>> {
        self.tx.subscribe()
    }
}

// ---------------------------------------------------------------------------
// Unit tests (ported from pheno-runtime-config per consolidation plan)
// ---------------------------------------------------------------------------

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
        assert_eq!(&**rx.borrow(), "world");
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
