//! Graceful shutdown on SIGINT / SIGTERM with configurable drain timeout.

use std::time::Duration;

use tokio::{signal, time};
use tracing::{info, warn};

use crate::metrics::{self, names, MetricsHook, NoopMetricsHook};

/// Shutdown behaviour configuration.
#[derive(Debug, Clone)]
pub struct ShutdownConfig {
    /// Max time to wait for in-flight work after signal.
    pub drain_timeout: Duration,
}

impl Default for ShutdownConfig {
    fn default() -> Self {
        let secs = std::env::var("CONFIGRA_SHUTDOWN_TIMEOUT_SECS")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(30);
        Self {
            drain_timeout: Duration::from_secs(secs),
        }
    }
}

/// Wait for OS shutdown signal (Ctrl+C or SIGTERM).
pub async fn shutdown_signal() {
    let ctrl_c = async {
        signal::ctrl_c()
            .await
            .expect("failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("failed to install SIGTERM handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        () = ctrl_c => info!(target: "configra_ops", "received SIGINT, shutting down"),
        () = terminate => info!(target: "configra_ops", "received SIGTERM, shutting down"),
    }
}

/// Coordinates graceful shutdown: signal → optional drain → cleanup hook.
pub struct GracefulShutdown {
    config: ShutdownConfig,
    metrics: Box<dyn MetricsHook>,
}

impl GracefulShutdown {
    /// Create with default config and no-op metrics.
    pub fn new() -> Self {
        Self::with_config(ShutdownConfig::default())
    }

    /// Create with explicit drain timeout.
    pub fn with_config(config: ShutdownConfig) -> Self {
        Self {
            config,
            metrics: Box::new(NoopMetricsHook),
        }
    }

    /// Attach a metrics hook for shutdown events.
    pub fn with_metrics(mut self, hook: Box<dyn MetricsHook>) -> Self {
        self.metrics = hook;
        self
    }

    /// Block until a shutdown signal, optionally run `drain`, then `cleanup`.
    pub async fn run<F, Fut, C, CFut>(&self, drain: F, cleanup: C)
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = ()>,
        C: FnOnce() -> CFut,
        CFut: std::future::Future<Output = ()>,
    {
        shutdown_signal().await;

        if metrics::metrics_enabled() {
            self.metrics.increment_counter(names::SHUTDOWN_TOTAL, 1);
        }

        info!(
            target: "configra_ops",
            timeout_secs = self.config.drain_timeout.as_secs(),
            "draining in-flight work"
        );

        match time::timeout(self.config.drain_timeout, drain()).await {
            Ok(()) => info!(target: "configra_ops", "drain complete"),
            Err(_) => warn!(
                target: "configra_ops",
                timeout_secs = self.config.drain_timeout.as_secs(),
                "drain timed out, proceeding with cleanup"
            ),
        }

        cleanup().await;
        info!(target: "configra_ops", "shutdown complete");
    }
}

impl Default for GracefulShutdown {
    fn default() -> Self {
        Self::new()
    }
}
