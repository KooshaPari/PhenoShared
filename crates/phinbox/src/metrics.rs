//! Optional Prometheus metrics, gated behind the `observability` feature.

#[cfg(feature = "observability")]
pub mod metrics {
    use std::sync::OnceLock;

    use prometheus::{
        register_counter_vec, register_gauge, register_histogram_vec, CounterVec, Gauge, HistogramVec,
    };

    static IN_FLIGHT: OnceLock<Gauge> = OnceLock::new();
    static TOTAL: OnceLock<CounterVec> = OnceLock::new();
    static TIMEOUTS: OnceLock<CounterVec> = OnceLock::new();
    static FAILURES: OnceLock<CounterVec> = OnceLock::new();
    static ELAPSED: OnceLock<HistogramVec> = OnceLock::new();

    /// Initialize all metric families. Idempotent — safe to call multiple times.
    pub fn init() {
        IN_FLIGHT.get_or_init(|| {
            register_gauge!(
                "phinbox_in_flight",
                "Number of popups currently open"
            )
            .unwrap()
        });
        TOTAL.get_or_init(|| {
            register_counter_vec!(
                "phinbox_total",
                "Total popups opened, by status",
                &["status"]
            )
            .unwrap()
        });
        TIMEOUTS.get_or_init(|| {
            register_counter_vec!(
                "phinbox_timeouts_total",
                "Popups that timed out, by platform",
                &["platform"]
            )
            .unwrap()
        });
        FAILURES.get_or_init(|| {
            register_counter_vec!(
                "phinbox_failures_total",
                "Popups that failed to render, by platform",
                &["platform"]
            )
            .unwrap()
        });
        ELAPSED.get_or_init(|| {
            register_histogram_vec!(
                "phinbox_elapsed_seconds",
                "Time from popup open to user response",
                &["status"],
                vec![0.1, 0.5, 1.0, 5.0, 30.0, 60.0, 300.0]
            )
            .unwrap()
        });
    }

    /// Increment the in-flight gauge. Call when a popup opens.
    pub fn on_open() {
        if let Some(g) = IN_FLIGHT.get() {
            g.inc();
        }
    }

    /// Decrement the in-flight gauge and observe the elapsed time.
    /// `status` should be one of: answered, cancelled, timed_out, failed.
    pub fn on_close(status: &str, elapsed_secs: f64) {
        if let Some(g) = IN_FLIGHT.get() {
            g.dec();
        }
        if let Some(c) = TOTAL.get() {
            c.with_label_values(&[status]).inc();
        }
        if status == "timed_out" {
            if let Some(c) = TIMEOUTS.get() {
                let platform = format!("{:?}", crate::platform());
                c.with_label_values(&[platform])
                    .inc_by(1.0);
            }
        }
        if status == "failed" {
            if let Some(c) = FAILURES.get() {
                let platform = format!("{:?}", crate::platform());
                c.with_label_values(&[platform])
                    .inc_by(1.0);
            }
        }
        if let Some(h) = ELAPSED.get() {
            h.with_label_values(&[status]).observe(elapsed_secs);
        }
    }
}
