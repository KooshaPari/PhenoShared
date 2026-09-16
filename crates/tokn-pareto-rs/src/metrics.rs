//! Prometheus-based observability metrics for Pareto cost engine.
//!
//! Provides an ingest-rate counter, queue-depth gauge, and latency histogram
//! exposed through `prometheus-client` so they can be scraped at `/metrics`.

use prometheus_client::encoding::text::encode;
use prometheus_client::metrics::counter::Counter;
use prometheus_client::metrics::gauge::Gauge;
use prometheus_client::metrics::histogram::{Histogram, exponential_buckets};
use prometheus_client::registry::Registry;

/// Top-level metrics registry that owns all metric families.
///
/// Construct once at startup and share via `Arc`.
#[derive(Debug)]
pub struct ParetoMetrics {
    pub registry: Registry,
    /// Monotonically increasing count of items ingested (e.g. cost entries).
    pub ingest_total: Counter,
    /// Current number of items waiting to be processed.
    pub queue_depth: Gauge,
    /// End-to-end processing latency in seconds.
    pub processing_latency: Histogram,
}

impl ParetoMetrics {
    /// Create a new [`ParetoMetrics`] with sensible defaults.
    ///
    /// The histogram uses exponential buckets from 1 ms to 30 s.
    pub fn new() -> Self {
        let mut registry = Registry::default();

        let ingest_total = Counter::default();
        registry.register(
            "pareto_ingest_total",
            "Total number of cost entries ingested",
            ingest_total.clone(),
        );

        let queue_depth = Gauge::default();
        registry.register(
            "pareto_queue_depth",
            "Current number of entries waiting to be processed",
            queue_depth.clone(),
        );

        let processing_latency = Histogram::new(exponential_buckets(0.001, 2.0, 15));
        registry.register(
            "pareto_processing_latency_seconds",
            "Processing latency in seconds",
            processing_latency.clone(),
        );

        Self {
            registry,
            ingest_total,
            queue_depth,
            processing_latency,
        }
    }

    /// Encode the current registry state as the OpenMetrics text format.
    pub fn encode_metrics(&self) -> String {
        let mut buffer = String::new();
        encode(&mut buffer, &self.registry).expect("encoding to string should not fail");
        buffer
    }
}

impl Default for ParetoMetrics {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ingest_counter_increments() {
        let m = ParetoMetrics::new();
        assert_eq!(m.ingest_total.get(), 0);
        m.ingest_total.inc();
        m.ingest_total.inc_by(5);
        assert_eq!(m.ingest_total.get(), 6);
    }

    #[test]
    fn queue_depth_gauge_tracks_current() {
        let m = ParetoMetrics::new();
        assert_eq!(m.queue_depth.get(), 0);
        m.queue_depth.inc();
        m.queue_depth.inc();
        m.queue_depth.dec();
        assert_eq!(m.queue_depth.get(), 1);
    }

    #[test]
    fn latency_histogram_records_and_encodes() {
        let m = ParetoMetrics::new();
        m.processing_latency.observe(0.05);
        m.processing_latency.observe(1.2);

        let text = m.encode_metrics();
        assert!(
            text.contains("pareto_processing_latency_seconds"),
            "encoded metrics should contain the histogram family name"
        );
        assert!(
            text.contains("pareto_ingest_total"),
            "encoded metrics should contain the counter family name"
        );
        assert!(
            text.contains("pareto_queue_depth"),
            "encoded metrics should contain the gauge family name"
        );
    }
}
