//! `TimeSeriesPort` — hexagonal port for a time-series ingest backend (e.g. QuestDB).

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use phenotype_error_core::ApiError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Canonical error type for time-series operations.
pub type TsResult<T> = Result<T, ApiError>;

/// A single metric data point.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TsMetric {
    pub timestamp: DateTime<Utc>,
    pub name: String,
    pub value: f64,
    pub labels: HashMap<String, String>,
}

/// A single log entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TsLogEntry {
    pub timestamp: DateTime<Utc>,
    pub level: String,
    pub message: String,
    pub source: String,
    pub trace_id: Option<String>,
    pub labels: HashMap<String, String>,
}

/// Port that any time-series adapter must implement.
///
/// Mirrors the ingest surface of [`pheno_questdb::BatchIngester`] /
/// [`pheno_questdb::QuestDBClient`].
#[async_trait]
pub trait TimeSeriesPort: Send + Sync {
    /// Ingest a single metric point.
    async fn ingest_metric(&mut self, metric: TsMetric) -> TsResult<()>;

    /// Ingest a single log entry.
    async fn ingest_log(&mut self, log: TsLogEntry) -> TsResult<()>;

    /// Flush any internally buffered data to the backing store.
    /// Returns the number of rows flushed.
    async fn flush(&mut self) -> TsResult<usize>;

    /// Number of rows buffered but not yet flushed.
    fn pending(&self) -> usize;
}
