//! Metric Types

use serde::{Deserialize, Serialize};

/// Metric type
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MetricType {
    Counter,
    Gauge,
    Histogram,
    Summary,
}

/// Metric metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricMetadata {
    pub name: String,
    pub description: Option<String>,
    pub unit: Option<String>,
    pub metric_type: MetricType,
}

impl MetricMetadata {
    pub fn new(name: impl Into<String>, metric_type: MetricType) -> Self {
        Self {
            name: name.into(),
            description: None,
            unit: None,
            metric_type,
        }
    }

    pub fn with_description(mut self, desc: impl Into<String>) -> Self {
        self.description = Some(desc.into());
        self
    }

    pub fn with_unit(mut self, unit: impl Into<String>) -> Self {
        self.unit = Some(unit.into());
        self
    }
}
