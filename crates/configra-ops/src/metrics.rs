//! Lightweight metrics hook for counters and gauges.
//!
//! Integrators can swap [`NoopMetricsHook`] for a Prometheus / OTEL bridge
//! without changing call sites.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};

/// Metrics recording port.
pub trait MetricsHook: Send + Sync {
    /// Increment a counter by `delta` (default 1).
    fn increment_counter(&self, name: &str, delta: u64);
    /// Set a gauge to an absolute value.
    fn set_gauge(&self, name: &str, value: f64);
    /// Record a histogram observation (hook may no-op if unsupported).
    fn observe_histogram(&self, name: &str, value: f64);
}

/// No-op metrics hook (default until a backend is wired).
#[derive(Debug, Default, Clone, Copy)]
pub struct NoopMetricsHook;

impl MetricsHook for NoopMetricsHook {
    fn increment_counter(&self, _name: &str, _delta: u64) {}
    fn set_gauge(&self, _name: &str, _value: f64) {}
    fn observe_histogram(&self, _name: &str, _value: f64) {}
}

/// In-process metrics registry (testing / sidecar export).
#[derive(Debug, Default, Clone)]
pub struct MetricsRegistry {
    inner: Arc<RwLock<Inner>>,
}

#[derive(Debug, Default)]
struct Inner {
    counters: HashMap<String, u64>,
    gauges: HashMap<String, f64>,
}

impl MetricsRegistry {
    /// Create an empty registry.
    pub fn new() -> Self {
        Self::default()
    }

    /// Snapshot current counter values.
    pub fn counters(&self) -> HashMap<String, u64> {
        self.inner
            .read()
            .expect("metrics lock poisoned")
            .counters
            .clone()
    }

    /// Snapshot current gauge values.
    pub fn gauges(&self) -> HashMap<String, f64> {
        self.inner
            .read()
            .expect("metrics lock poisoned")
            .gauges
            .clone()
    }
}

impl MetricsHook for MetricsRegistry {
    fn increment_counter(&self, name: &str, delta: u64) {
        let mut guard = self.inner.write().expect("metrics lock poisoned");
        *guard.counters.entry(name.to_owned()).or_insert(0) += delta;
    }

    fn set_gauge(&self, name: &str, value: f64) {
        let mut guard = self.inner.write().expect("metrics lock poisoned");
        guard.gauges.insert(name.to_owned(), value);
    }

    fn observe_histogram(&self, name: &str, value: f64) {
        // Store last observation under `{name}_last` for simple introspection.
        let mut guard = self.inner.write().expect("metrics lock poisoned");
        guard.gauges.insert(format!("{name}_last"), value);
    }
}

/// Returns whether metrics collection is enabled (`CONFIGRA_METRICS_ENABLED`).
pub fn metrics_enabled() -> bool {
    match std::env::var("CONFIGRA_METRICS_ENABLED") {
        Ok(v) => !matches!(
            v.to_ascii_lowercase().as_str(),
            "0" | "false" | "off" | "no"
        ),
        Err(_) => true,
    }
}

/// Standard Configra metric names.
pub mod names {
    pub const CONFIG_LOAD_TOTAL: &str = "configra_config_load_total";
    pub const CONFIG_LOAD_ERRORS: &str = "configra_config_load_errors_total";
    pub const HEALTH_CHECK_TOTAL: &str = "configra_health_check_total";
    pub const SHUTDOWN_TOTAL: &str = "configra_shutdown_total";
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn registry_records_counters() {
        let reg = MetricsRegistry::new();
        reg.increment_counter("test", 2);
        reg.increment_counter("test", 3);
        assert_eq!(reg.counters().get("test"), Some(&5));
    }
}
