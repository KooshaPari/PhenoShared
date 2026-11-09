//! `MetricsPort` — hexagonal port for counter / gauge / histogram recording.
//!
//! The trait is synchronous and object-safe so it can be held as
//! `Box<dyn MetricsPort>` without the `async_trait` indirection that
//! `CachePort` requires.

use std::collections::HashMap;

/// Canonical error type for metrics operations.
#[derive(Debug, thiserror::Error)]
pub enum MetricsError {
    #[error("failed to register metric '{name}': {source}")]
    RegistrationFailed {
        name: String,
        #[source]
        source: Box<dyn std::error::Error + Send + Sync + 'static>,
    },
    #[error("metrics backend error: {0}")]
    Backend(String),
}

pub type MetricsResult<T> = Result<T, MetricsError>;

/// Label key-value pairs attached to a metric observation.
pub type Labels<'a> = &'a [(&'a str, &'a str)];

/// Port that any metrics adapter must implement.
///
/// All methods take a name and a slice of label key-value pairs so that a
/// single adapter instance can record dimensioned metrics without carrying
/// per-metric state in the caller.
///
/// # Object safety
/// The trait is `dyn`-safe: all methods take `&self` (or `&mut self`-free
/// variants where the adapter needs interior mutability) and return
/// non-generic values.
pub trait MetricsPort: Send + Sync {
    /// Increment a counter by `delta`.
    ///
    /// Counters are monotonically increasing values (e.g. request count).
    fn inc_counter(&self, name: &str, delta: u64, labels: Labels<'_>);

    /// Shorthand for `inc_counter(name, 1, labels)`.
    fn inc(&self, name: &str, labels: Labels<'_>) {
        self.inc_counter(name, 1, labels);
    }

    /// Set an absolute gauge value.
    ///
    /// Gauges represent current snapshots (e.g. queue depth, memory usage).
    fn set_gauge(&self, name: &str, value: f64, labels: Labels<'_>);

    /// Record a single histogram observation.
    ///
    /// Histograms track distribution of values (e.g. request latency).
    fn observe_histogram(&self, name: &str, value: f64, labels: Labels<'_>);
}

// ---------------------------------------------------------------------------
// Value types used by the in-memory double (declared here so they live in
// the same module as the port trait).
// ---------------------------------------------------------------------------

/// A recorded counter entry in the in-memory double.
#[derive(Debug, Clone, PartialEq)]
pub struct CounterEntry {
    pub name: String,
    pub delta: u64,
    pub labels: HashMap<String, String>,
}

/// A recorded gauge entry in the in-memory double.
#[derive(Debug, Clone, PartialEq)]
pub struct GaugeEntry {
    pub name: String,
    pub value: f64,
    pub labels: HashMap<String, String>,
}

/// A recorded histogram observation in the in-memory double.
#[derive(Debug, Clone, PartialEq)]
pub struct HistogramEntry {
    pub name: String,
    pub value: f64,
    pub labels: HashMap<String, String>,
}
