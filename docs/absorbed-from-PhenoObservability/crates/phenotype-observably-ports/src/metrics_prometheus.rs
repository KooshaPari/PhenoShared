//! Prometheus adapter for [`MetricsPort`].
//!
//! Available only with the `prometheus-adapter` Cargo feature.
//! Wraps the `prometheus` 0.14 registry to record counters, gauges, and
//! histograms using the standard Prometheus data model.

use crate::metrics::{Labels, MetricsPort};
use prometheus::{CounterVec, GaugeVec, HistogramOpts, HistogramVec, Opts, Registry};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Lazily-registered Prometheus metric families, keyed by metric name.
struct PrometheusInner {
    registry: Registry,
    counters: HashMap<String, CounterVec>,
    gauges: HashMap<String, GaugeVec>,
    histograms: HashMap<String, HistogramVec>,
}

impl PrometheusInner {
    fn new(registry: Registry) -> Self {
        Self {
            registry,
            counters: HashMap::new(),
            gauges: HashMap::new(),
            histograms: HashMap::new(),
        }
    }

    /// Extract sorted label names from a label slice.
    fn label_names(labels: Labels<'_>) -> Vec<String> {
        labels.iter().map(|(k, _)| k.to_string()).collect()
    }

    fn label_values<'a>(labels: Labels<'a>) -> Vec<&'a str> {
        labels.iter().map(|(_, v)| *v).collect()
    }

    fn get_or_create_counter(&mut self, name: &str, labels: Labels<'_>) -> Option<CounterVec> {
        if !self.counters.contains_key(name) {
            let label_names = Self::label_names(labels);
            let label_refs: Vec<&str> = label_names.iter().map(String::as_str).collect();
            let opts = Opts::new(name, name);
            match CounterVec::new(opts, &label_refs) {
                Ok(cv) => {
                    if self.registry.register(Box::new(cv.clone())).is_err() {
                        return None;
                    }
                    self.counters.insert(name.to_owned(), cv);
                }
                Err(_) => return None,
            }
        }
        self.counters.get(name).cloned()
    }

    fn get_or_create_gauge(&mut self, name: &str, labels: Labels<'_>) -> Option<GaugeVec> {
        if !self.gauges.contains_key(name) {
            let label_names = Self::label_names(labels);
            let label_refs: Vec<&str> = label_names.iter().map(String::as_str).collect();
            let opts = Opts::new(name, name);
            match GaugeVec::new(opts, &label_refs) {
                Ok(gv) => {
                    if self.registry.register(Box::new(gv.clone())).is_err() {
                        return None;
                    }
                    self.gauges.insert(name.to_owned(), gv);
                }
                Err(_) => return None,
            }
        }
        self.gauges.get(name).cloned()
    }

    fn get_or_create_histogram(&mut self, name: &str, labels: Labels<'_>) -> Option<HistogramVec> {
        if !self.histograms.contains_key(name) {
            let label_names = Self::label_names(labels);
            let label_refs: Vec<&str> = label_names.iter().map(String::as_str).collect();
            // Standard latency buckets (ms): .005 → 10
            let buckets = prometheus::exponential_buckets(0.005, 2.0, 20)
                .unwrap_or_else(|_| prometheus::DEFAULT_BUCKETS.to_vec());
            let opts = HistogramOpts::new(name, name).buckets(buckets);
            match HistogramVec::new(opts, &label_refs) {
                Ok(hv) => {
                    if self.registry.register(Box::new(hv.clone())).is_err() {
                        return None;
                    }
                    self.histograms.insert(name.to_owned(), hv);
                }
                Err(_) => return None,
            }
        }
        self.histograms.get(name).cloned()
    }
}

/// [`MetricsPort`] adapter backed by a `prometheus::Registry`.
///
/// Metrics families are registered lazily on first observation.  All writes
/// are safe under concurrent access via an internal `Mutex`.
///
/// # Example
/// ```ignore
/// let adapter = PrometheusMetrics::default(); // uses global registry
/// let port: Box<dyn MetricsPort> = Box::new(adapter);
/// port.inc("http_requests_total", &[("method", "GET")]);
/// ```
#[derive(Clone)]
pub struct PrometheusMetrics {
    inner: Arc<Mutex<PrometheusInner>>,
}

impl PrometheusMetrics {
    /// Create an adapter using a custom `Registry`.
    pub fn with_registry(registry: Registry) -> Self {
        Self {
            inner: Arc::new(Mutex::new(PrometheusInner::new(registry))),
        }
    }

    /// Create an adapter using the default global Prometheus registry.
    pub fn default_registry() -> Self {
        Self::with_registry(prometheus::default_registry().clone())
    }

    /// Expose the underlying `Registry` so callers can gather metrics.
    pub fn registry(&self) -> Registry {
        self.inner.lock().unwrap().registry.clone()
    }
}

impl Default for PrometheusMetrics {
    fn default() -> Self {
        Self::with_registry(Registry::new())
    }
}

impl MetricsPort for PrometheusMetrics {
    fn inc_counter(&self, name: &str, delta: u64, labels: Labels<'_>) {
        let cv = {
            let mut inner = self.inner.lock().unwrap();
            inner.get_or_create_counter(name, labels)
        };
        if let Some(cv) = cv {
            let lv = PrometheusInner::label_values(labels);
            if let Ok(c) = cv.get_metric_with_label_values(&lv) {
                c.inc_by(delta as f64);
            }
        }
    }

    fn set_gauge(&self, name: &str, value: f64, labels: Labels<'_>) {
        let gv = {
            let mut inner = self.inner.lock().unwrap();
            inner.get_or_create_gauge(name, labels)
        };
        if let Some(gv) = gv {
            let lv = PrometheusInner::label_values(labels);
            if let Ok(g) = gv.get_metric_with_label_values(&lv) {
                g.set(value);
            }
        }
    }

    fn observe_histogram(&self, name: &str, value: f64, labels: Labels<'_>) {
        let hv = {
            let mut inner = self.inner.lock().unwrap();
            inner.get_or_create_histogram(name, labels)
        };
        if let Some(hv) = hv {
            let lv = PrometheusInner::label_values(labels);
            if let Ok(h) = hv.get_metric_with_label_values(&lv) {
                h.observe(value);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use prometheus::{Encoder, TextEncoder};

    fn gather_text(adapter: &PrometheusMetrics) -> String {
        let mfs = adapter.registry().gather();
        let encoder = TextEncoder::new();
        let mut buf = Vec::new();
        encoder.encode(&mfs, &mut buf).unwrap();
        String::from_utf8(buf).unwrap()
    }

    #[test]
    fn prometheus_counter_recorded() {
        let adapter = PrometheusMetrics::default();
        adapter.inc_counter("prom_req_total", 3, &[("method", "GET")]);
        adapter.inc_counter("prom_req_total", 2, &[("method", "GET")]);
        let text = gather_text(&adapter);
        assert!(text.contains("prom_req_total"), "metric name missing");
        assert!(text.contains("method=\"GET\""), "label missing");
    }

    #[test]
    fn prometheus_gauge_set() {
        let adapter = PrometheusMetrics::default();
        adapter.set_gauge("prom_queue_depth", 7.0, &[("q", "jobs")]);
        let text = gather_text(&adapter);
        assert!(text.contains("prom_queue_depth"), "gauge missing");
        assert!(text.contains("7"), "gauge value missing");
    }

    #[test]
    fn prometheus_histogram_observed() {
        let adapter = PrometheusMetrics::default();
        adapter.observe_histogram("prom_latency_ms", 42.0, &[("route", "/health")]);
        let text = gather_text(&adapter);
        assert!(
            text.contains("prom_latency_ms_bucket"),
            "histogram bucket missing"
        );
        assert!(
            text.contains("prom_latency_ms_sum"),
            "histogram sum missing"
        );
        assert!(
            text.contains("prom_latency_ms_count"),
            "histogram count missing"
        );
    }

    #[test]
    fn prometheus_adapter_is_object_safe() {
        let a = PrometheusMetrics::default();
        let _: Box<dyn MetricsPort> = Box::new(a);
    }
}
