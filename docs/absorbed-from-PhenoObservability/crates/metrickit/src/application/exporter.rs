//! Metric Exporter

use crate::domain::*;

pub trait MetricExporter: Send + Sync {
    fn export(&self, registry: &Registry) -> MetricResult<String>;
}

/// Prometheus format exporter
#[derive(Clone)]
pub struct PrometheusExporter;

impl PrometheusExporter {
    pub fn new() -> Self {
        Self
    }
}

impl Default for PrometheusExporter {
    fn default() -> Self {
        Self::new()
    }
}

impl MetricExporter for PrometheusExporter {
    fn export(&self, registry: &Registry) -> MetricResult<String> {
        let mut output = String::new();

        // Export counters
        let counters = registry.counters.read();
        for (name, counter) in counters.iter() {
            let metadata = counter.metadata();
            if let Some(ref desc) = metadata.description {
                output.push_str(&format!("# HELP {} {}\n", name, desc));
            }
            if let Some(ref unit) = metadata.unit {
                output.push_str(&format!("# UNIT {} {}\n", name, unit));
            }
            output.push_str(&format!("{} {}\n", name, counter.get()));
        }

        // Export gauges
        let gauges = registry.gauges.read();
        for (name, gauge) in gauges.iter() {
            let metadata = gauge.metadata();
            if let Some(ref desc) = metadata.description {
                output.push_str(&format!("# HELP {} {}\n", name, desc));
            }
            output.push_str(&format!("{} {}\n", name, gauge.get()));
        }

        // Export histograms
        let histograms = registry.histograms.read();
        for (name, histogram) in histograms.iter() {
            let value = histogram.get();
            let metadata = histogram.metadata();
            if let Some(ref desc) = metadata.description {
                output.push_str(&format!("# HELP {} {}\n", name, desc));
            }
            output.push_str(&format!("{}_count {}\n", name, value.count));
            output.push_str(&format!("{}_sum {}\n", name, value.sum));
            for (i, count) in value.buckets.counts.iter().enumerate() {
                let bound = if i < value.buckets.bounds.len() {
                    value.buckets.bounds[i]
                } else {
                    f64::INFINITY
                };
                output.push_str(&format!("{}_bucket{{le=\"{}\"}} {}\n", name, bound, count));
            }
        }

        Ok(output)
    }
}
