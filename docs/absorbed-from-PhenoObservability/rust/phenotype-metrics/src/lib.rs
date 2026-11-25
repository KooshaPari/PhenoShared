//! Phenotype metrics library for standardized metrics collection and reporting.
//!
//! Provides counters, gauges, histograms, and Prometheus export capabilities.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Standardized metrics key with name and labels
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct MetricKey {
    pub name: String,
    pub labels: Vec<(String, String)>,
}

impl MetricKey {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            labels: Vec::new(),
        }
    }

    pub fn with_label(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.labels.push((key.into(), value.into()));
        self
    }

    pub fn with_labels(mut self, labels: Vec<(impl Into<String>, impl Into<String>)>) -> Self {
        for (k, v) in labels {
            self.labels.push((k.into(), v.into()));
        }
        self
    }
}

/// Standardized metrics client with prefix support
pub struct MetricsClient {
    prefix: String,
    labels: Vec<(String, String)>,
}

impl MetricsClient {
    /// Create a new metrics client with prefix
    pub fn new(prefix: impl Into<String>) -> Self {
        Self {
            prefix: prefix.into(),
            labels: Vec::new(),
        }
    }

    /// Add labels to the client
    pub fn with_labels(mut self, labels: Vec<(impl Into<String>, impl Into<String>)>) -> Self {
        for (k, v) in labels {
            self.labels.push((k.into(), v.into()));
        }
        self
    }

    fn make_key(&self, name: &str) -> MetricKey {
        let full_name = format!("{}.{}", self.prefix, name);
        MetricKey::new(full_name).with_labels(self.labels.clone())
    }

    /// Increment a counter
    pub fn counter(&self, recorder: &dyn MetricsRecorder, name: &str, value: u64) {
        let key = self.make_key(name);
        recorder.record_counter(key, value);
    }

    /// Set a gauge value
    pub fn gauge(&self, recorder: &dyn MetricsRecorder, name: &str, value: f64) {
        let key = self.make_key(name);
        recorder.record_gauge(key, value);
    }

    /// Record a histogram value
    pub fn histogram(&self, recorder: &dyn MetricsRecorder, name: &str, value: f64) {
        let key = self.make_key(name);
        recorder.record_histogram(key, value);
    }

    /// Time a function execution
    pub fn timed<F, R>(&self, recorder: &dyn MetricsRecorder, name: &str, f: F) -> R
    where
        F: FnOnce() -> R,
    {
        let start = std::time::Instant::now();
        let result = f();
        let elapsed = start.elapsed().as_secs_f64() * 1000.0; // Convert to ms
        self.histogram(recorder, name, elapsed);
        result
    }
}

/// Trait for metrics recorders
pub trait MetricsRecorder: Send + Sync {
    fn record_counter(&self, key: MetricKey, value: u64);
    fn record_gauge(&self, key: MetricKey, value: f64);
    fn record_histogram(&self, key: MetricKey, value: f64);
}

/// Metrics snapshot for reporting
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricsSnapshot {
    pub timestamp: DateTime<Utc>,
    pub counters: Vec<MetricCounter>,
    pub gauges: Vec<MetricGauge>,
    pub histograms: Vec<MetricHistogram>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricCounter {
    pub name: String,
    pub value: u64,
    pub labels: Vec<(String, String)>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricGauge {
    pub name: String,
    pub value: f64,
    pub labels: Vec<(String, String)>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricHistogram {
    pub name: String,
    pub count: u64,
    pub sum: f64,
    pub min: f64,
    pub max: f64,
    pub p50: f64,
    pub p95: f64,
    pub p99: f64,
    pub labels: Vec<(String, String)>,
}

/// Simple in-memory metrics recorder
#[derive(Debug, Default)]
pub struct InMemoryRecorder {
    counters: Arc<Mutex<HashMap<MetricKey, u64>>>,
    gauges: Arc<Mutex<HashMap<MetricKey, f64>>>,
    histograms: Arc<Mutex<HashMap<MetricKey, Vec<f64>>>>,
}

impl InMemoryRecorder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn snapshot(&self) -> MetricsSnapshot {
        let counters: Vec<MetricCounter> = {
            let data = self.counters.lock().unwrap();
            data.iter()
                .map(|(k, v)| MetricCounter {
                    name: k.name.clone(),
                    value: *v,
                    labels: k.labels.clone(),
                })
                .collect()
        };

        let gauges: Vec<MetricGauge> = {
            let data = self.gauges.lock().unwrap();
            data.iter()
                .map(|(k, v)| MetricGauge {
                    name: k.name.clone(),
                    value: *v,
                    labels: k.labels.clone(),
                })
                .collect()
        };

        let histograms: Vec<MetricHistogram> = {
            let data = self.histograms.lock().unwrap();
            data.iter()
                .map(|(k, v)| {
                    let count = v.len() as u64;
                    let sum: f64 = v.iter().sum();
                    let min = v.iter().cloned().fold(f64::INFINITY, f64::min);
                    let max = v.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
                    let mut sorted = v.clone();
                    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
                    let p50 = sorted.get(sorted.len() / 2).cloned().unwrap_or(0.0);
                    let p95 = sorted.get(sorted.len() * 95 / 100).cloned().unwrap_or(0.0);
                    let p99 = sorted.get(sorted.len() * 99 / 100).cloned().unwrap_or(0.0);

                    MetricHistogram {
                        name: k.name.clone(),
                        count,
                        sum,
                        min,
                        max,
                        p50,
                        p95,
                        p99,
                        labels: k.labels.clone(),
                    }
                })
                .collect()
        };

        MetricsSnapshot {
            timestamp: Utc::now(),
            counters,
            gauges,
            histograms,
        }
    }
}

impl MetricsRecorder for InMemoryRecorder {
    fn record_counter(&self, key: MetricKey, value: u64) {
        let mut data = self.counters.lock().unwrap();
        *data.entry(key).or_insert(0) += value;
    }

    fn record_gauge(&self, key: MetricKey, value: f64) {
        let mut data = self.gauges.lock().unwrap();
        data.insert(key, value);
    }

    fn record_histogram(&self, key: MetricKey, value: f64) {
        let mut data = self.histograms.lock().unwrap();
        data.entry(key).or_default().push(value);
    }
}

/// Prometheus-compatible text format exporter
pub fn export_prometheus_format(snapshot: &MetricsSnapshot) -> String {
    let mut output = String::new();

    // Export counters
    for counter in &snapshot.counters {
        let labels = format_labels(&counter.labels);
        output.push_str(&format!(
            "# HELP {}_total Total count\n",
            sanitize_metric_name(&counter.name)
        ));
        output.push_str(&format!(
            "# TYPE {}_total counter\n",
            sanitize_metric_name(&counter.name)
        ));
        output.push_str(&format!(
            "{}_total{} {}\n",
            sanitize_metric_name(&counter.name),
            labels,
            counter.value
        ));
    }

    // Export gauges
    for gauge in &snapshot.gauges {
        let labels = format_labels(&gauge.labels);
        output.push_str(&format!(
            "# HELP {} Current value\n",
            sanitize_metric_name(&gauge.name)
        ));
        output.push_str(&format!(
            "# TYPE {} gauge\n",
            sanitize_metric_name(&gauge.name)
        ));
        output.push_str(&format!(
            "{}{} {}\n",
            sanitize_metric_name(&gauge.name),
            labels,
            gauge.value
        ));
    }

    // Export histograms
    for hist in &snapshot.histograms {
        let labels = format_labels(&hist.labels);
        let name = sanitize_metric_name(&hist.name);

        output.push_str(&format!("# HELP {} Histogram\n", name));
        output.push_str(&format!("# TYPE {} histogram\n", name));

        // _bucket entries (simplified - just one bucket for all values)
        output.push_str(&format!(
            "{}_bucket{{le=\"+Inf\"{}}} {}\n",
            name,
            format_labels_prometheus(&hist.labels),
            hist.count
        ));

        // _sum and _count
        output.push_str(&format!("{}_sum{} {}\n", name, labels, hist.sum));
        output.push_str(&format!("{}_count{} {}\n", name, labels, hist.count));
    }

    output
}

fn sanitize_metric_name(name: &str) -> String {
    name.replace(".", "_").replace("-", "_")
}

fn format_labels(labels: &[(String, String)]) -> String {
    if labels.is_empty() {
        String::new()
    } else {
        let formatted: Vec<String> = labels
            .iter()
            .map(|(k, v)| format!("{}=\"{}\"", k, v))
            .collect();
        format!("{{{}}}", formatted.join(","))
    }
}

fn format_labels_prometheus(labels: &[(String, String)]) -> String {
    if labels.is_empty() {
        String::new()
    } else {
        let formatted: Vec<String> = labels
            .iter()
            .map(|(k, v)| format!(",{}=\"{}\"", k, v))
            .collect();
        formatted.join("")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metric_key_creation() {
        let key = MetricKey::new("test.counter").with_label("env", "test");
        assert_eq!(key.name, "test.counter");
        assert_eq!(key.labels.len(), 1);
    }

    #[test]
    fn test_in_memory_recorder_counter() {
        let recorder = InMemoryRecorder::new();
        let key = MetricKey::new("test.counter");

        recorder.record_counter(key.clone(), 5);
        recorder.record_counter(key.clone(), 3);

        let snapshot = recorder.snapshot();
        assert_eq!(snapshot.counters.len(), 1);
        assert_eq!(snapshot.counters[0].value, 8);
    }

    #[test]
    fn test_in_memory_recorder_gauge() {
        let recorder = InMemoryRecorder::new();
        let key = MetricKey::new("test.gauge");

        recorder.record_gauge(key.clone(), 42.0);

        let snapshot = recorder.snapshot();
        assert_eq!(snapshot.gauges.len(), 1);
        assert_eq!(snapshot.gauges[0].value, 42.0);
    }

    #[test]
    fn test_in_memory_recorder_histogram() {
        let recorder = InMemoryRecorder::new();
        let key = MetricKey::new("test.histogram");

        for i in 1..=10 {
            recorder.record_histogram(key.clone(), i as f64 * 10.0);
        }

        let snapshot = recorder.snapshot();
        assert_eq!(snapshot.histograms.len(), 1);
        assert_eq!(snapshot.histograms[0].count, 10);
        assert_eq!(snapshot.histograms[0].sum, 550.0); // 10+20+...+100
    }

    #[test]
    fn test_metrics_client() {
        let recorder = InMemoryRecorder::new();
        let client = MetricsClient::new("phenotype").with_labels(vec![("env", "test")]);

        client.counter(&recorder, "requests", 1);
        client.gauge(&recorder, "memory_mb", 1024.0);
        client.histogram(&recorder, "latency", 150.0);

        let snapshot = recorder.snapshot();
        assert_eq!(snapshot.counters.len(), 1);
        assert_eq!(snapshot.counters[0].name, "phenotype.requests");
        assert_eq!(snapshot.gauges.len(), 1);
        assert_eq!(snapshot.histograms.len(), 1);
    }

    #[test]
    fn test_prometheus_export() {
        let recorder = InMemoryRecorder::new();
        let client = MetricsClient::new("test");

        client.counter(&recorder, "requests", 10);
        client.gauge(&recorder, "memory", 100.0);

        let snapshot = recorder.snapshot();
        let output = export_prometheus_format(&snapshot);

        assert!(output.contains("test_requests_total"));
        assert!(output.contains("test_memory"));
        assert!(output.contains("# HELP"));
        assert!(output.contains("# TYPE"));
    }
}
