//! Core contracts and abstractions for the Phenotype ecosystem.
//!
//! This crate defines the fundamental interfaces and types that other
//! Phenotype crates depend on, ensuring loose coupling and clear contracts.

#![warn(missing_docs)]
#![warn(clippy::all)]

/// Re-export common serde types for convenience.
pub mod serde {
    pub use serde::{Deserialize, Serialize};
}

/// Standard result type used across phenotype crates.
pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;

/// Core contract trait for domain events and messages.
///
/// This trait defines the basic contract interface used across the phenotype
/// ecosystem for event sourcing, messaging, and domain event handling.
pub trait Contract: Send + Sync {
    /// Returns the type of this contract.
    fn contract_type(&self) -> &'static str;

    /// Returns the timestamp when this contract was created.
    fn timestamp(&self) -> chrono::DateTime<chrono::Utc>;

    /// Returns the correlation ID for tracking related events.
    fn correlation_id(&self) -> uuid::Uuid;

    /// Returns a reference to this object as Any for downcasting.
    fn as_any(&self) -> &dyn std::any::Any;
}

/// Event trait for domain events.
///
/// This trait extends Contract and adds event-specific properties like
/// aggregate ID and sequence number for event sourcing.
pub trait Event: Contract {
    /// Returns the aggregate ID this event belongs to.
    fn aggregate_id(&self) -> &str;

    /// Returns the sequence number of this event in the aggregate's stream.
    fn sequence(&self) -> u64;
}

/// A trait for recording cache metrics at different tiers.
///
/// Implementors can record hits and misses at different cache layers
/// (e.g., L1, L2) for observability and performance monitoring.
///
/// # Examples
///
/// ```
/// use phenotype_contracts::{MetricsHook, NoOpMetrics};
///
/// let metrics = NoOpMetrics;
/// metrics.record_hit("l1");
/// metrics.record_miss("l2");
/// ```
pub trait MetricsHook: Send + Sync {
    /// Record a cache hit at the specified tier (e.g., "l1", "l2").
    fn record_hit(&self, tier: &str);

    /// Record a cache miss at the specified tier (e.g., "l1", "l2").
    fn record_miss(&self, tier: &str);

    /// Record a counter metric with a name, value, and tags
    fn record_counter(&self, name: &str, value: u64, tags: &[&str]);

    /// Record a gauge metric with a name, value, and tags
    fn record_gauge(&self, name: &str, value: f64, tags: &[&str]);

    /// Record a histogram metric with a name, value, and tags
    fn record_histogram(&self, name: &str, value: f64, tags: &[&str]);
}

/// No-op metrics hook for when observability is not needed.
#[derive(Debug, Default, Clone, Copy)]
pub struct NoOpMetrics;

impl MetricsHook for NoOpMetrics {
    fn record_hit(&self, _tier: &str) {
        // Intentionally no-op
    }

    fn record_miss(&self, _tier: &str) {
        // Intentionally no-op
    }

    fn record_counter(&self, _name: &str, _value: u64, _tags: &[&str]) {
        // Intentionally no-op
    }

    fn record_gauge(&self, _name: &str, _value: f64, _tags: &[&str]) {
        // Intentionally no-op
    }

    fn record_histogram(&self, _name: &str, _value: f64, _tags: &[&str]) {
        // Intentionally no-op
    }
}

/// A simple counter-based metrics hook for testing.
#[derive(Debug, Default)]
pub struct CounterMetrics {
    hits: std::sync::atomic::AtomicU64,
    misses: std::sync::atomic::AtomicU64,
}

impl CounterMetrics {
    /// Create a new counter metrics instance.
    pub fn new() -> Self {
        Self::default()
    }

    /// Get the current hit count.
    pub fn hits(&self) -> u64 {
        self.hits.load(std::sync::atomic::Ordering::Relaxed)
    }

    /// Get the current miss count.
    pub fn misses(&self) -> u64 {
        self.misses.load(std::sync::atomic::Ordering::Relaxed)
    }

    /// Reset all counters to zero.
    pub fn reset(&self) {
        self.hits.store(0, std::sync::atomic::Ordering::Relaxed);
        self.misses.store(0, std::sync::atomic::Ordering::Relaxed);
    }
}

impl MetricsHook for CounterMetrics {
    fn record_hit(&self, _tier: &str) {
        self.hits.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    }

    fn record_miss(&self, _tier: &str) {
        self.misses
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    }

    fn record_counter(&self, _name: &str, _value: u64, _tags: &[&str]) {
        // Stub implementation
    }

    fn record_gauge(&self, _name: &str, _value: f64, _tags: &[&str]) {
        // Stub implementation
    }

    fn record_histogram(&self, _name: &str, _value: f64, _tags: &[&str]) {
        // Stub implementation
    }
}

#[cfg(test)]
mod metrics_tests {
    use super::*;

    #[test]
    fn noop_metrics_does_not_panic() {
        let metrics = NoOpMetrics;
        metrics.record_hit("l1");
        metrics.record_miss("l2");
        // Should not panic
    }

    #[test]
    fn counter_metrics_tracks_hits() {
        let metrics = CounterMetrics::new();
        metrics.record_hit("l1");
        metrics.record_hit("l1");
        metrics.record_hit("l2");
        assert_eq!(metrics.hits(), 3);
    }

    #[test]
    fn counter_metrics_tracks_misses() {
        let metrics = CounterMetrics::new();
        metrics.record_miss("l1");
        metrics.record_miss("l2");
        assert_eq!(metrics.misses(), 2);
    }

    #[test]
    fn counter_metrics_reset_works() {
        let metrics = CounterMetrics::new();
        metrics.record_hit("l1");
        metrics.record_miss("l1");
        metrics.reset();
        assert_eq!(metrics.hits(), 0);
        assert_eq!(metrics.misses(), 0);
    }
}
