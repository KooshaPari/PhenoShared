//! Metrics collection for OmniRoute Core

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

/// Simple metrics collector
#[derive(Debug, Clone, Default)]
pub struct Metrics {
    /// Total requests processed
    pub requests_total: Arc<AtomicU64>,
    /// Active requests (in-flight)
    pub requests_active: Arc<AtomicU64>,
    /// Total tokens generated
    pub tokens_total: Arc<AtomicU64>,
    /// Total errors
    pub errors_total: Arc<AtomicU64>,
    /// Total request duration in microseconds (for calculating averages)
    pub request_duration_us: Arc<AtomicU64>,
}

impl Metrics {
    /// Create a new metrics instance
    pub fn new() -> Self {
        Self::default()
    }

    /// Record a new request
    pub fn record_request(&self) {
        self.requests_total.fetch_add(1, Ordering::Relaxed);
        self.requests_active.fetch_add(1, Ordering::Relaxed);
    }

    /// Complete a request
    pub fn complete_request(&self, duration_us: u64) {
        self.requests_active.fetch_sub(1, Ordering::Relaxed);
        self.request_duration_us
            .fetch_add(duration_us, Ordering::Relaxed);
    }

    /// Record tokens generated
    pub fn record_tokens(&self, tokens: u64) {
        self.tokens_total.fetch_add(tokens, Ordering::Relaxed);
    }

    /// Record an error
    pub fn record_error(&self) {
        self.errors_total.fetch_add(1, Ordering::Relaxed);
    }

    /// Get current snapshot of metrics
    pub fn snapshot(&self) -> MetricsSnapshot {
        MetricsSnapshot {
            requests_total: self.requests_total.load(Ordering::Relaxed),
            requests_active: self.requests_active.load(Ordering::Relaxed),
            tokens_total: self.tokens_total.load(Ordering::Relaxed),
            errors_total: self.errors_total.load(Ordering::Relaxed),
            request_duration_us: self.request_duration_us.load(Ordering::Relaxed),
        }
    }
}

/// Snapshot of metrics at a point in time
#[derive(Debug, Clone)]
pub struct MetricsSnapshot {
    pub requests_total: u64,
    pub requests_active: u64,
    pub tokens_total: u64,
    pub errors_total: u64,
    pub request_duration_us: u64,
}

impl MetricsSnapshot {
    /// Calculate average request duration in milliseconds
    pub fn avg_request_duration_ms(&self) -> f64 {
        if self.requests_total == 0 {
            return 0.0;
        }
        self.request_duration_us as f64 / self.requests_total as f64 / 1000.0
    }

    /// Calculate error rate
    pub fn error_rate(&self) -> f64 {
        if self.requests_total == 0 {
            return 0.0;
        }
        self.errors_total as f64 / self.requests_total as f64
    }

    /// Format metrics as Prometheus-compatible text
    pub fn to_prometheus(&self) -> String {
        format!(
            r#"# HELP omniroute_requests_total Total requests processed
# TYPE omniroute_requests_total counter
omniroute_requests_total {}

# HELP omniroute_requests_active Active requests
# TYPE omniroute_requests_active gauge
omniroute_requests_active {}

# HELP omniroute_tokens_total Total tokens generated
# TYPE omniroute_tokens_total counter
omniroute_tokens_total {}

# HELP omniroute_errors_total Total errors
# TYPE omniroute_errors_total counter
omniroute_errors_total {}

# HELP omniroute_request_duration_avg Average request duration in milliseconds
# TYPE omniroute_request_duration_avg gauge
omniroute_request_duration_avg {}
"#,
            self.requests_total,
            self.requests_active,
            self.tokens_total,
            self.errors_total,
            self.avg_request_duration_ms(),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metrics() {
        let metrics = Metrics::new();

        metrics.record_request();
        metrics.record_request();
        metrics.record_tokens(100);
        metrics.complete_request(5000);

        let snapshot = metrics.snapshot();
        assert_eq!(snapshot.requests_total, 2);
        assert_eq!(snapshot.tokens_total, 100);
    }

    #[test]
    fn test_avg_duration() {
        let metrics = Metrics::new();

        metrics.record_request();
        metrics.complete_request(1000);
        metrics.record_request();
        metrics.complete_request(3000);

        let snapshot = metrics.snapshot();
        assert!((snapshot.avg_request_duration_ms() - 2.0).abs() < 0.1);
    }
}
