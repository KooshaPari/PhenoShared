//! Hexagonal port traits for PhenoObservability adapters.
//!
//! This crate defines the **driver-side ports** (interfaces) that infra
//! adapters must implement so consumers can program against abstractions and
//! swap real adapters for in-memory test doubles.
//!
//! # Ports
//! - [`CachePort`]       — generic key/value cache (Dragonfly / Redis adapter)
//! - [`TimeSeriesPort`]  — time-series ingest (QuestDB adapter)
//! - [`MetricsPort`]     — counter / gauge / histogram recording (FR-OBS-042)
//!
//! # Test doubles (feature `test-util`)
//! Enable the `test-util` Cargo feature to get:
//! - [`test_doubles::InMemoryCache`]
//! - [`test_doubles::InMemoryTimeSeries`]
//! - [`test_doubles::InMemoryMetrics`]
//!
//! # Prometheus adapter (feature `prometheus-adapter`)
//! Enable the `prometheus-adapter` Cargo feature to get:
//! - [`metrics_prometheus::PrometheusMetrics`]

pub mod cache;
pub mod metrics;
pub mod timeseries;

#[cfg(feature = "test-util")]
pub mod test_doubles;

#[cfg(feature = "prometheus-adapter")]
pub mod metrics_prometheus;

pub use cache::CachePort;
pub use metrics::MetricsPort;
pub use timeseries::TimeSeriesPort;
