//! Benchmark data ingestion from external sources.
//!
//! This module provides clients for fetching benchmark data from:
//! - Artificial Analysis API
//! - OpenRouter API
//! - CLIProxyAPI metrics (60+ granular metrics)
//! - Thegent (Python) adapter
//! - Web scraping (future)
//!
//! It also provides manual override support via config.

pub mod artificial_analysis;
pub mod cli;
pub mod cliproxy_metrics;
pub mod openrouter;
pub mod overrides;
pub mod store;
pub mod thegent_adapter;

pub use cli::run_benchmarks;
pub use cliproxy_metrics::{
    CLIProxyMetricsClient, CLIProxyMetricsConfig, HealthStatus, ModelMetrics, ModelRanking,
    ProviderMetrics, RequestMetrics, UsageAnalytics,
};
pub use overrides::ManualOverrides;
pub use store::{BenchmarkData, BenchmarkSource, BenchmarkStore};
pub use thegent_adapter::{ThegentAdapter, ThegentAdapterConfig};
