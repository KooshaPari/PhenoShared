//! Gauge Metric

use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::sync::Arc;

use super::{MetricMetadata, MetricType};

/// Gauge value
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GaugeValue {
    pub value: f64,
}

impl GaugeValue {
    pub fn new(value: f64) -> Self {
        Self { value }
    }

    pub fn set(&mut self, v: f64) {
        self.value = v;
    }

    pub fn inc(&mut self) {
        self.value += 1.0;
    }

    pub fn dec(&mut self) {
        self.value -= 1.0;
    }

    pub fn get(&self) -> f64 {
        self.value
    }
}

/// Gauge metric
#[derive(Clone)]
pub struct Gauge {
    metadata: MetricMetadata,
    value: Arc<RwLock<GaugeValue>>,
}

impl Gauge {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            metadata: MetricMetadata::new(name, MetricType::Gauge),
            value: Arc::new(RwLock::new(GaugeValue::new(0.0))),
        }
    }

    pub fn with_description(mut self, desc: impl Into<String>) -> Self {
        self.metadata = self.metadata.with_description(desc);
        self
    }

    pub fn set(&self, v: f64) {
        self.value.write().set(v);
    }

    pub fn inc(&self) {
        self.value.write().inc();
    }

    pub fn dec(&self) {
        self.value.write().dec();
    }

    pub fn get(&self) -> f64 {
        self.value.read().get()
    }

    pub fn metadata(&self) -> &MetricMetadata {
        &self.metadata
    }
}
