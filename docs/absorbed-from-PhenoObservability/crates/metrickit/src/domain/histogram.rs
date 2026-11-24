//! Histogram Metric

use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::sync::Arc;

use super::{MetricMetadata, MetricType};

/// Histogram buckets
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistogramBuckets {
    pub bounds: Vec<f64>,
    pub counts: Vec<u64>,
}

impl HistogramBuckets {
    pub fn new(bounds: Vec<f64>) -> Self {
        let len = bounds.len();
        Self {
            bounds,
            counts: vec![0; len + 1],
        }
    }

    pub fn observe(&mut self, value: f64) {
        for (i, bound) in self.bounds.iter().enumerate() {
            if value <= *bound {
                self.counts[i] += 1;
                return;
            }
        }
        *self.counts.last_mut().unwrap() += 1;
    }
}

/// Histogram value
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistogramValue {
    pub count: u64,
    pub sum: f64,
    pub buckets: HistogramBuckets,
}

impl HistogramValue {
    pub fn new(bounds: Vec<f64>) -> Self {
        Self {
            count: 0,
            sum: 0.0,
            buckets: HistogramBuckets::new(bounds),
        }
    }

    pub fn observe(&mut self, value: f64) {
        self.count += 1;
        self.sum += value;
        self.buckets.observe(value);
    }
}

/// Histogram metric
#[derive(Clone)]
pub struct Histogram {
    metadata: MetricMetadata,
    value: Arc<RwLock<HistogramValue>>,
}

impl Histogram {
    /// Create with default buckets
    pub fn new(name: impl Into<String>) -> Self {
        Self::with_buckets(
            name,
            vec![
                0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
            ],
        )
    }

    /// Create with custom buckets
    pub fn with_buckets(name: impl Into<String>, bounds: Vec<f64>) -> Self {
        Self {
            metadata: MetricMetadata::new(name, MetricType::Histogram),
            value: Arc::new(RwLock::new(HistogramValue::new(bounds))),
        }
    }

    pub fn with_description(mut self, desc: impl Into<String>) -> Self {
        self.metadata = self.metadata.with_description(desc);
        self
    }

    pub fn observe(&self, value: f64) {
        self.value.write().observe(value);
    }

    pub fn get(&self) -> HistogramValue {
        self.value.read().clone()
    }

    pub fn metadata(&self) -> &MetricMetadata {
        &self.metadata
    }
}
