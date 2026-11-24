//! Observability and operations primitives for Configra services.
//!
//! Additive substrate for audit areas G (Observability) and K (Ops):
//! structured logging, correlation IDs, metrics hooks, health/readiness
//! probes, and graceful shutdown helpers.

pub mod correlation;
pub mod health;
pub mod logging;
pub mod metrics;
pub mod shutdown;

pub use correlation::{CorrelationId, CorrelationLayer};
pub use health::{
    liveness, readiness, CheckResult, HealthCheck, HealthReport, HealthStatus, WorkspaceCheck,
};
pub use logging::{init_logging, LogFormat, LoggingConfig};
pub use metrics::{MetricsHook, MetricsRegistry, NoopMetricsHook};
pub use shutdown::{shutdown_signal, GracefulShutdown, ShutdownConfig};

/// Crate version (matches workspace package version).
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
