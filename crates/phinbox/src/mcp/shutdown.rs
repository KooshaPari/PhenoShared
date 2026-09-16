//! Signal handling for graceful MCP server shutdown.
//!
//! On SIGTERM/SIGINT we cancel all in-flight popups gracefully and
//! let the server exit cleanly. Because each popup is spawned in its
//! own process group (POSIX `setsid` / Windows
//! `CREATE_NEW_PROCESS_GROUP`), SIGTERM to the server does not
//! propagate to the popups — they persist until the user closes them
//! or their timeout fires. This is the desired behavior: closing the
//! terminal does not lose the user's in-progress answer.

use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

use tokio::sync::oneshot;

/// Handle to orchestrate graceful MCP server shutdown.
///
/// On SIGTERM/SIGINT we wait for in-flight requests to drain up to the
/// configured timeout, then the server exits cleanly. Each popup is
/// spawned in its own process group (POSIX `setsid` / Windows
/// `CREATE_NEW_PROCESS_GROUP`), so SIGTERM to the server does not
/// propagate to the popups — they persist until the user closes them
/// or their timeout fires.
#[derive(Clone, Debug)]
pub struct ShutdownCoordinator {
    inflight: Arc<AtomicUsize>,
    shutdown_timeout: Duration,
}

impl Default for ShutdownCoordinator {
    fn default() -> Self {
        Self::new(Duration::from_secs(5))
    }
}

impl ShutdownCoordinator {
    /// Create a new coordinator with the given shutdown timeout.
    ///
    /// The timeout controls how long [`cancel_all`](Self::cancel_all)
    /// waits for in-flight requests to finish after the shutdown signal
    /// fires.
    #[must_use]
    pub fn new(shutdown_timeout: Duration) -> Self {
        Self {
            inflight: Arc::new(AtomicUsize::new(0)),
            shutdown_timeout,
        }
    }

    /// Register a new in-flight request. Returns a handle that should
    /// be dropped when the request completes.
    #[must_use]
    pub fn register(&self) -> InFlightGuard {
        self.inflight.fetch_add(1, Ordering::AcqRel);
        InFlightGuard {
            inflight: self.inflight.clone(),
        }
    }

    /// Return the current number of in-flight requests.
    #[must_use]
    pub fn inflight_count(&self) -> usize {
        self.inflight.load(Ordering::Acquire)
    }

    /// Wait for all in-flight requests to finish, up to the configured
    /// timeout. Returns the number of requests still tracked after the
    /// timeout expires (should be zero in the happy case).
    pub async fn cancel_all(&self) -> usize {
        let deadline = tokio::time::Instant::now() + self.shutdown_timeout;
        loop {
            let remaining = self.inflight.load(Ordering::Acquire);
            if remaining == 0 {
                return 0;
            }
            if tokio::time::Instant::now() >= deadline {
                return remaining;
            }
            tokio::time::sleep(Duration::from_millis(50)).await;
        }
    }

    /// Install SIGINT/SIGTERM handlers. Returns immediately; the
    /// returned `oneshot` resolves when a shutdown signal is received.
    /// When the signal fires, `cancel_all()` is called to drain in-flight
    /// requests before the receiver resolves.
    #[cfg(unix)]
    #[must_use]
    pub fn install(self: Arc<Self>) -> oneshot::Receiver<()> {
        let (tx, rx) = oneshot::channel();
        let this = self.clone();
        tokio::spawn(async move {
            use tokio::signal::unix::{signal, SignalKind};
            let mut sigterm =
                signal(SignalKind::terminate()).expect("install SIGTERM handler");
            let mut sigint =
                signal(SignalKind::interrupt()).expect("install SIGINT handler");
            tokio::select! {
                _ = sigterm.recv() => {},
                _ = sigint.recv() => {},
            }
            let remaining = this.cancel_all().await;
            tracing::info!(remaining, "graceful shutdown complete");
            let _ = tx.send(());
        });
        rx
    }

    /// Install CTRL_CLOSE handler (Windows). Returns immediately; the
    /// returned `oneshot` resolves when a shutdown signal is received.
    /// When the signal fires, `cancel_all()` is called to drain in-flight
    /// requests before the receiver resolves.
    #[cfg(not(unix))]
    pub fn install(self: Arc<Self>) -> oneshot::Receiver<()> {
        let (tx, rx) = oneshot::channel();
        let this = self.clone();
        tokio::spawn(async move {
            let _ = tokio::signal::ctrl_c().await;
            let remaining = this.cancel_all().await;
            tracing::info!(remaining, "graceful shutdown complete");
            let _ = tx.send(());
        });
        rx
    }
}

/// RAII guard that decrements the in-flight counter when dropped.
#[derive(Debug)]
pub struct InFlightGuard {
    inflight: Arc<AtomicUsize>,
}

impl Drop for InFlightGuard {
    fn drop(&mut self) {
        self.inflight.fetch_sub(1, Ordering::AcqRel);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;

    #[tokio::test]
    async fn cancel_all_returns_zero_when_nothing_inflight() {
        let coord = ShutdownCoordinator::new(Duration::from_millis(100));
        let remaining = coord.cancel_all().await;
        assert_eq!(remaining, 0);
    }

    #[tokio::test]
    async fn cancel_all_waits_for_inflight_to_drain() {
        let coord = Arc::new(ShutdownCoordinator::new(Duration::from_secs(5)));
        let guard = coord.register();
        let coord_clone = coord.clone();
        // Spawn a task that drops the guard after a short delay
        tokio::spawn(async move {
            tokio::time::sleep(Duration::from_millis(50)).await;
            drop(guard);
        });
        let remaining = coord_clone.cancel_all().await;
        assert_eq!(remaining, 0);
    }

    #[tokio::test]
    async fn cancel_all_times_out_when_inflight_never_drains() {
        let coord = ShutdownCoordinator::new(Duration::from_millis(50));
        let _guard = coord.register();
        let remaining = coord.cancel_all().await;
        // The guard is never dropped, so cancel_all should time out
        // and return the remaining count (1) after 50ms.
        assert_eq!(remaining, 1);
    }

    #[tokio::test]
    async fn register_increments_inflight_count() {
        let coord = ShutdownCoordinator::new(Duration::from_secs(5));
        assert_eq!(coord.inflight_count(), 0);
        let guard = coord.register();
        assert_eq!(coord.inflight_count(), 1);
        drop(guard);
        assert_eq!(coord.inflight_count(), 0);
    }

    #[tokio::test]
    async fn multiple_inflight_guards_tracked_correctly() {
        let coord = Arc::new(ShutdownCoordinator::new(Duration::from_secs(5)));
        let g1 = coord.register();
        let g2 = coord.register();
        let g3 = coord.register();
        assert_eq!(coord.inflight_count(), 3);
        drop(g1);
        assert_eq!(coord.inflight_count(), 2);
        drop(g2);
        assert_eq!(coord.inflight_count(), 1);
        drop(g3);
        assert_eq!(coord.inflight_count(), 0);
    }
}
