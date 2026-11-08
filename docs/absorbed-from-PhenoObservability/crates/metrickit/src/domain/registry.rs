//! Metric Registry

use parking_lot::RwLock;
use std::collections::HashMap;

use super::{Counter, Gauge, Histogram, MetricError};

/// Metric registry
pub struct Registry {
    pub(crate) counters: RwLock<HashMap<String, Counter>>,
    pub(crate) gauges: RwLock<HashMap<String, Gauge>>,
    pub(crate) histograms: RwLock<HashMap<String, Histogram>>,
}

impl Default for Registry {
    fn default() -> Self {
        Self::new()
    }
}

impl Registry {
    pub fn new() -> Self {
        Self {
            counters: RwLock::new(HashMap::new()),
            gauges: RwLock::new(HashMap::new()),
            histograms: RwLock::new(HashMap::new()),
        }
    }

    /// Register a counter
    pub fn register_counter(&self, name: &str) -> Result<Counter, MetricError> {
        let counter = Counter::new(name);
        let mut counters = self.counters.write();
        if counters.contains_key(name) {
            return Err(MetricError::AlreadyRegistered(name.into()));
        }
        counters.insert(name.into(), counter.clone());
        Ok(counter)
    }

    /// Get or create a counter
    pub fn counter(&self, name: &str) -> Counter {
        let mut counters = self.counters.write();
        if let Some(c) = counters.get(name) {
            return c.clone();
        }
        let counter = Counter::new(name);
        counters.insert(name.into(), counter.clone());
        counter
    }

    /// Register a gauge
    pub fn register_gauge(&self, name: &str) -> Result<Gauge, MetricError> {
        let gauge = Gauge::new(name);
        let mut gauges = self.gauges.write();
        if gauges.contains_key(name) {
            return Err(MetricError::AlreadyRegistered(name.into()));
        }
        gauges.insert(name.into(), gauge.clone());
        Ok(gauge)
    }

    /// Get or create a gauge
    pub fn gauge(&self, name: &str) -> Gauge {
        let mut gauges = self.gauges.write();
        if let Some(g) = gauges.get(name) {
            return g.clone();
        }
        let gauge = Gauge::new(name);
        gauges.insert(name.into(), gauge.clone());
        gauge
    }

    /// Register a histogram
    pub fn register_histogram(
        &self,
        name: &str,
        bounds: Vec<f64>,
    ) -> Result<Histogram, MetricError> {
        let histogram = Histogram::with_buckets(name, bounds);
        let mut histograms = self.histograms.write();
        if histograms.contains_key(name) {
            return Err(MetricError::AlreadyRegistered(name.into()));
        }
        histograms.insert(name.into(), histogram.clone());
        Ok(histogram)
    }

    /// Get or create a histogram
    pub fn histogram(&self, name: &str) -> Histogram {
        let mut histograms = self.histograms.write();
        if let Some(h) = histograms.get(name) {
            return h.clone();
        }
        let histogram = Histogram::new(name);
        histograms.insert(name.into(), histogram.clone());
        histogram
    }

    /// Clear all metrics
    pub fn clear(&self) {
        self.counters.write().clear();
        self.gauges.write().clear();
        self.histograms.write().clear();
    }
}
