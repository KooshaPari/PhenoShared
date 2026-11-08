//! Counter Metric

use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::sync::Arc;

use super::{MetricMetadata, MetricType};

/// Counter value
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct CounterValue {
    pub value: f64,
}

impl CounterValue {
    pub fn new(value: f64) -> Self {
        Self { value }
    }

    pub fn inc(&mut self) {
        self.value += 1.0;
    }

    pub fn add(&mut self, v: f64) {
        self.value += v;
    }

    pub fn get(&self) -> f64 {
        self.value
    }
}

/// Counter metric
#[derive(Clone)]
pub struct Counter {
    metadata: MetricMetadata,
    value: Arc<RwLock<CounterValue>>,
}

impl Counter {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            metadata: MetricMetadata::new(name, MetricType::Counter),
            value: Arc::new(RwLock::new(CounterValue::default())),
        }
    }

    pub fn with_description(mut self, desc: impl Into<String>) -> Self {
        self.metadata = self.metadata.with_description(desc);
        self
    }

    pub fn with_unit(mut self, unit: impl Into<String>) -> Self {
        self.metadata = self.metadata.with_unit(unit);
        self
    }

    pub fn inc(&self) {
        self.value.write().inc();
    }

    pub fn add(&self, v: f64) {
        self.value.write().add(v);
    }

    pub fn get(&self) -> f64 {
        self.value.read().get()
    }

    pub fn metadata(&self) -> &MetricMetadata {
        &self.metadata
    }
}
