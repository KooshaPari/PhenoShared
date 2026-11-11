//! Cooperative shutdown for `sl-daemon serve`.
//!
//! A root [`ServeShutdown`] [`CancellationToken`] fans out to the HTTP server,
//! ETL consumer, and watcher sweep so Ctrl+C (or an explicit [`ServeShutdown::cancel`])
//! stops in-flight work without leaving tasks orphaned.

use tokio_util::sync::CancellationToken;

/// Root cooperative shutdown signal for `serve`.
#[derive(Clone, Debug, Default)]
pub struct ServeShutdown(CancellationToken);

impl ServeShutdown {
    /// Create a new, uncancelled shutdown handle.
    pub fn new() -> Self {
        Self(CancellationToken::new())
    }

    /// Borrow the underlying [`CancellationToken`] for watcher/ETL wiring.
    pub fn token(&self) -> &CancellationToken {
        &self.0
    }

    /// Signal all subscribers to stop.
    pub fn cancel(&self) {
        self.0.cancel();
    }

    /// Future that completes when [`Self::cancel`] is called.
    pub fn cancelled(&self) -> tokio_util::sync::WaitForCancellationFuture<'_> {
        self.0.cancelled()
    }

    /// Spawn a background task that calls [`Self::cancel`] on Ctrl+C / SIGINT.
    pub fn spawn_ctrl_c_handler(&self) -> tokio::task::JoinHandle<()> {
        let token = self.0.clone();
        tokio::spawn(async move {
            if tokio::signal::ctrl_c().await.is_ok() {
                token.cancel();
            }
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[tokio::test]
    async fn cancel_notifies_waiters() {
        let shutdown = ServeShutdown::new();
        assert!(!shutdown.token().is_cancelled());
        let waiter = shutdown.clone();
        let handle = tokio::spawn(async move {
            waiter.cancelled().await;
        });

        shutdown.cancel();
        assert!(shutdown.token().is_cancelled());

        tokio::time::timeout(Duration::from_secs(1), handle)
            .await
            .expect("cancelled waiter should complete")
            .expect("task join");
    }
}
