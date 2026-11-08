//! # Phenotype Telemetry
//!
//! Telemetry collection and export for observability.
//!
//! ## Features
//!
//! - Metrics collection
//! - Distributed tracing
//! - OpenTelemetry integration
//! - Log correlation

use chrono::{DateTime, Utc};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Metric types
#[derive(Debug, Clone)]
pub enum MetricValue {
    Counter(u64),
    Gauge(f64),
    Histogram(Vec<f64>),
    Summary { sum: f64, count: u64 },
}

/// Metric with metadata
#[derive(Debug, Clone)]
pub struct Metric {
    pub name: String,
    pub value: MetricValue,
    pub labels: HashMap<String, String>,
    pub timestamp: DateTime<Utc>,
    pub description: Option<String>,
}

impl Metric {
    /// Create new counter metric
    pub fn counter(name: impl Into<String>, value: u64) -> Self {
        Self {
            name: name.into(),
            value: MetricValue::Counter(value),
            labels: HashMap::new(),
            timestamp: Utc::now(),
            description: None,
        }
    }

    /// Create new gauge metric
    pub fn gauge(name: impl Into<String>, value: f64) -> Self {
        Self {
            name: name.into(),
            value: MetricValue::Gauge(value),
            labels: HashMap::new(),
            timestamp: Utc::now(),
            description: None,
        }
    }

    /// Add labels
    pub fn with_label(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.labels.insert(key.into(), value.into());
        self
    }

    /// Add description
    pub fn with_description(mut self, desc: impl Into<String>) -> Self {
        self.description = Some(desc.into());
        self
    }
}

/// Metrics collector
pub struct MetricsCollector {
    metrics: Arc<Mutex<Vec<Metric>>>,
}

impl MetricsCollector {
    /// Create new collector
    pub fn new() -> Self {
        Self {
            metrics: Arc::new(Mutex::new(Vec::new())),
        }
    }

    /// Record a metric
    pub fn record(&self, metric: Metric) {
        let mut metrics = self.metrics.lock().unwrap();
        metrics.push(metric);
    }

    /// Record counter
    pub fn counter(&self, name: impl Into<String>, value: u64) {
        self.record(Metric::counter(name, value));
    }

    /// Record gauge
    pub fn gauge(&self, name: impl Into<String>, value: f64) {
        self.record(Metric::gauge(name, value));
    }

    /// Get all metrics
    pub fn get_metrics(&self) -> Vec<Metric> {
        let metrics = self.metrics.lock().unwrap();
        metrics.clone()
    }

    /// Clear metrics
    pub fn clear(&self) {
        let mut metrics = self.metrics.lock().unwrap();
        metrics.clear();
    }

    /// Flush metrics (get and clear)
    pub fn flush(&self) -> Vec<Metric> {
        let mut metrics = self.metrics.lock().unwrap();
        let flushed = metrics.clone();
        metrics.clear();
        flushed
    }
}

impl Default for MetricsCollector {
    fn default() -> Self {
        Self::new()
    }
}

/// Span context for tracing
#[derive(Debug, Clone)]
pub struct SpanContext {
    pub trace_id: String,
    pub span_id: String,
    pub parent_span_id: Option<String>,
    pub sampled: bool,
}

impl SpanContext {
    /// Create new root span context
    pub fn new_root() -> Self {
        Self {
            trace_id: uuid::Uuid::new_v4().to_string(),
            span_id: uuid::Uuid::new_v4().to_string(),
            parent_span_id: None,
            sampled: true,
        }
    }

    /// Create child span context
    pub fn child(&self) -> Self {
        Self {
            trace_id: self.trace_id.clone(),
            span_id: uuid::Uuid::new_v4().to_string(),
            parent_span_id: Some(self.span_id.clone()),
            sampled: self.sampled,
        }
    }
}

/// Span for tracing
pub struct Span {
    pub context: SpanContext,
    pub name: String,
    pub start_time: DateTime<Utc>,
    pub end_time: Option<DateTime<Utc>>,
    pub attributes: HashMap<String, String>,
}

impl Span {
    /// Create new span
    pub fn new(name: impl Into<String>, context: SpanContext) -> Self {
        Self {
            name: name.into(),
            context,
            start_time: Utc::now(),
            end_time: None,
            attributes: HashMap::new(),
        }
    }

    /// Add attribute
    pub fn set_attribute(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.attributes.insert(key.into(), value.into());
    }

    /// End span
    pub fn end(&mut self) {
        self.end_time = Some(Utc::now());
    }

    /// Get duration
    pub fn duration_ms(&self) -> Option<i64> {
        self.end_time
            .map(|end| (end - self.start_time).num_milliseconds())
    }
}

/// Tracer for distributed tracing
pub struct Tracer {
    spans: Arc<Mutex<Vec<Span>>>,
}

impl Tracer {
    /// Create new tracer
    pub fn new() -> Self {
        Self {
            spans: Arc::new(Mutex::new(Vec::new())),
        }
    }

    /// Start new root span
    pub fn start_root(&self, name: impl Into<String>) -> Span {
        let span = Span::new(name, SpanContext::new_root());
        let mut spans = self.spans.lock().unwrap();
        spans.push(Span {
            context: span.context.clone(),
            name: span.name.clone(),
            start_time: span.start_time,
            end_time: span.end_time,
            attributes: span.attributes.clone(),
        });
        span
    }

    /// Get all spans
    pub fn get_spans(&self) -> Vec<Span> {
        let spans = self.spans.lock().unwrap();
        spans
            .iter()
            .map(|s| Span {
                context: s.context.clone(),
                name: s.name.clone(),
                start_time: s.start_time,
                end_time: s.end_time,
                attributes: s.attributes.clone(),
            })
            .collect()
    }
}

impl Default for Tracer {
    fn default() -> Self {
        Self::new()
    }
}

/// Telemetry exporter trait
pub trait TelemetryExporter: Send + Sync {
    /// Export metrics
    fn export_metrics(&self, metrics: &[Metric]) -> Result<(), String>;

    /// Export spans
    fn export_spans(&self, spans: &[Span]) -> Result<(), String>;
}

/// Console exporter for development
pub struct ConsoleExporter;

impl TelemetryExporter for ConsoleExporter {
    fn export_metrics(&self, metrics: &[Metric]) -> Result<(), String> {
        for metric in metrics {
            println!("[METRIC] {:?}", metric);
        }
        Ok(())
    }

    fn export_spans(&self, spans: &[Span]) -> Result<(), String> {
        for span in spans {
            println!("[SPAN] {:?} - {:?}", span.name, span.context);
        }
        Ok(())
    }
}

/// Telemetry configuration
pub struct TelemetryConfig {
    pub service_name: String,
    pub service_version: String,
    pub exporter: Box<dyn TelemetryExporter>,
    pub sample_rate: f64,
}

impl TelemetryConfig {
    /// Create new config
    pub fn new(service_name: impl Into<String>) -> Self {
        Self {
            service_name: service_name.into(),
            service_version: "1.0.0".to_string(),
            exporter: Box::new(ConsoleExporter),
            sample_rate: 1.0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metrics_collector() {
        let collector = MetricsCollector::new();

        collector.counter("requests", 10);
        collector.gauge("cpu_usage", 0.75);

        let metrics = collector.get_metrics();
        assert_eq!(metrics.len(), 2);
    }

    #[test]
    fn test_span_context() {
        let root = SpanContext::new_root();
        let child = root.child();

        assert_eq!(root.trace_id, child.trace_id);
        assert_eq!(child.parent_span_id, Some(root.span_id));
    }

    #[test]
    fn test_metric_with_labels() {
        let metric = Metric::counter("requests", 1)
            .with_label("method", "GET")
            .with_label("status", "200");

        assert_eq!(metric.labels.get("method"), Some(&"GET".to_string()));
    }
}
