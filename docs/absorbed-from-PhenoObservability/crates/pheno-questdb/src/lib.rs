//! QuestDB client for PhenoObservability
//!
//! QuestDB is a time-series database that's 100x faster than InfluxDB.
//! Supports native SQL, Kafka ingest, and HTTP API.

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use phenotype_errors::{ApiError, RepositoryError};
use phenotype_observably_ports::timeseries::{TimeSeriesPort, TsLogEntry, TsMetric, TsResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::debug;

/// QuestDB client result type
pub type Result<T> = std::result::Result<T, ApiError>;

/// Metric point
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Metric {
    pub timestamp: DateTime<Utc>,
    pub name: String,
    pub value: f64,
    pub labels: HashMap<String, String>,
}

/// Log entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub timestamp: DateTime<Utc>,
    pub level: String,
    pub message: String,
    pub source: String,
    pub trace_id: Option<String>,
    pub labels: HashMap<String, String>,
}

/// QuestDB REST client
pub struct QuestDBClient {
    url: String,
    http_client: reqwest::Client,
}

impl QuestDBClient {
    /// Create new QuestDB client
    pub fn new(url: &str) -> Self {
        Self {
            url: url.trim_end_matches('/').to_string(),
            http_client: reqwest::Client::new(),
        }
    }

    /// Insert metric using ILP (InfluxDB Line Protocol)
    pub async fn insert_metric(&self, metric: &Metric) -> Result<()> {
        let line = format!(
            "metrics,{},name={} value={} {}",
            Self::format_labels(&metric.labels),
            metric.name,
            metric.value,
            metric.timestamp.timestamp_nanos_opt().unwrap_or(0)
        );

        let response = self
            .http_client
            .post(format!("{}/v1/imp", self.url))
            .body(line)
            .send()
            .await
            .map_err(|e| ApiError::Internal(e.to_string()))?;

        if !response.status().is_success() {
            return Err(ApiError::Internal(format!("HTTP {}", response.status())));
        }

        debug!("Metric inserted: {}", metric.name);
        Ok(())
    }

    /// Insert log entry
    pub async fn insert_log(&self, log: &LogEntry) -> Result<()> {
        let trace = log.trace_id.as_deref().unwrap_or("none");
        let line = format!(
            "logs,level={},source={},trace_id={} message='{}' {}",
            log.level,
            log.source,
            trace,
            Self::escape_value(&log.message),
            log.timestamp.timestamp_nanos_opt().unwrap_or(0)
        );

        let response = self
            .http_client
            .post(format!("{}/v1/imp", self.url))
            .body(line)
            .send()
            .await
            .map_err(|e| ApiError::Internal(e.to_string()))?;

        if !response.status().is_success() {
            return Err(ApiError::Internal(format!("HTTP {}", response.status())));
        }

        debug!("Log inserted: {}", log.message);
        Ok(())
    }

    /// Execute SQL query
    pub async fn query<T: for<'de> Deserialize<'de>>(&self, sql: &str) -> Result<Vec<T>> {
        let url = format!("{}/v1/query?q={}", self.url, urlencoding::encode(sql));

        let response = self
            .http_client
            .get(&url)
            .send()
            .await
            .map_err(|e| ApiError::Internal(e.to_string()))?;

        let body = response
            .text()
            .await
            .map_err(|e| ApiError::Repository(RepositoryError::Serialization(e.to_string())))?;

        let result: QueryResult<T> = serde_json::from_str(&body)
            .map_err(|e| ApiError::Repository(RepositoryError::Serialization(e.to_string())))?;

        if let Some(err) = result.error {
            return Err(ApiError::Repository(RepositoryError::Serialization(err)));
        }

        Ok(result.data)
    }

    /// Aggregate metrics
    pub async fn aggregate(&self, name: &str, interval: &str) -> Result<Vec<AggregatedMetric>> {
        let sql = format!(
            "SELECT timestamp, avg(value) as avg_value, min(value) as min_value, max(value) as max_value \
             FROM metrics WHERE name = '{}' SAMPLE BY {} ALIGN TO CALENDAR",
            name, interval
        );

        self.query(&sql).await
    }

    /// Format labels for ILP
    fn format_labels(labels: &HashMap<String, String>) -> String {
        labels
            .iter()
            .map(|(k, v)| format!("{}={}", k, Self::escape_tag(v)))
            .collect::<Vec<_>>()
            .join(",")
    }

    /// Escape tag value
    fn escape_tag(s: &str) -> String {
        s.replace(',', "\\,").replace('=', "\\=")
    }

    /// Escape value (single quotes)
    fn escape_value(s: &str) -> String {
        s.replace('\'', "''")
    }
}

#[derive(Deserialize)]
struct QueryResult<T> {
    data: Vec<T>,
    #[serde(default)]
    error: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct AggregatedMetric {
    pub timestamp: DateTime<Utc>,
    pub avg_value: f64,
    pub min_value: f64,
    pub max_value: f64,
}

/// Timestamp precision for ILP lines.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TimestampPrecision {
    /// Nanoseconds (QuestDB default)
    Nanoseconds,
    /// Microseconds
    Microseconds,
    /// Milliseconds
    Milliseconds,
}

impl TimestampPrecision {
    /// Convert a [`DateTime<Utc>`] to the integer representation for this precision.
    pub fn to_ilp_value(self, dt: &DateTime<Utc>) -> i64 {
        match self {
            TimestampPrecision::Nanoseconds => dt.timestamp_nanos_opt().unwrap_or(0),
            TimestampPrecision::Microseconds => dt.timestamp_micros(),
            TimestampPrecision::Milliseconds => dt.timestamp_millis(),
        }
    }
}

/// Buffered batch of ILP lines destined for QuestDB.
#[derive(Debug)]
pub struct BatchIngester {
    /// Maximum number of rows before an automatic flush.
    pub flush_size: usize,
    /// Pending ILP lines not yet sent.
    lines: Vec<String>,
    /// Timestamp precision used when formatting new lines.
    pub precision: TimestampPrecision,
}

impl BatchIngester {
    /// Create a new `BatchIngester` with the given `flush_size` and `precision`.
    pub fn new(flush_size: usize, precision: TimestampPrecision) -> Self {
        Self {
            flush_size,
            lines: Vec::new(),
            precision,
        }
    }

    /// Buffer a [`Metric`] row.  Returns `true` when the batch has reached
    /// `flush_size` and the caller should call [`flush`](Self::flush).
    pub fn push_metric(&mut self, metric: &Metric) -> bool {
        let ts = self.precision.to_ilp_value(&metric.timestamp);
        let line = format!(
            "metrics,{},name={} value={} {}",
            QuestDBClient::format_labels(&metric.labels),
            metric.name,
            metric.value,
            ts,
        );
        self.lines.push(line);
        self.lines.len() >= self.flush_size
    }

    /// Buffer a [`LogEntry`] row.  Returns `true` when the batch should be
    /// flushed.
    pub fn push_log(&mut self, log: &LogEntry) -> bool {
        let ts = self.precision.to_ilp_value(&log.timestamp);
        let trace = log.trace_id.as_deref().unwrap_or("none");
        let line = format!(
            "logs,level={},source={},trace_id={} message='{}' {}",
            log.level,
            log.source,
            trace,
            QuestDBClient::escape_value(&log.message),
            ts,
        );
        self.lines.push(line);
        self.lines.len() >= self.flush_size
    }

    /// Return the number of buffered (un-flushed) rows.
    pub fn pending(&self) -> usize {
        self.lines.len()
    }

    /// Drain and return all buffered ILP lines, clearing the internal buffer.
    ///
    /// The caller is responsible for sending the returned lines to QuestDB.
    pub fn drain(&mut self) -> Vec<String> {
        std::mem::take(&mut self.lines)
    }

    /// Send all buffered lines to QuestDB via the provided client, then clear
    /// the buffer.  A no-op if the buffer is empty.
    pub async fn flush(&mut self, client: &QuestDBClient) -> Result<usize> {
        if self.lines.is_empty() {
            return Ok(0);
        }
        let body = self.lines.join("\n");
        let count = self.lines.len();
        self.lines.clear();

        let response = client
            .http_client
            .post(format!("{}/v1/imp", client.url))
            .body(body)
            .send()
            .await
            .map_err(|e| ApiError::Internal(e.to_string()))?;

        if !response.status().is_success() {
            return Err(ApiError::Internal(format!(
                "flush HTTP {}",
                response.status()
            )));
        }

        debug!("Flushed {} rows to QuestDB", count);
        Ok(count)
    }
}

// ---------------------------------------------------------------------------
// Hexagonal port implementation — BatchIngester ↔ TimeSeriesPort
// ---------------------------------------------------------------------------

#[async_trait]
impl TimeSeriesPort for BatchIngester {
    async fn ingest_metric(&mut self, metric: TsMetric) -> TsResult<()> {
        let m = Metric {
            timestamp: metric.timestamp,
            name: metric.name,
            value: metric.value,
            labels: metric.labels,
        };
        self.push_metric(&m);
        Ok(())
    }

    async fn ingest_log(&mut self, log: TsLogEntry) -> TsResult<()> {
        let l = LogEntry {
            timestamp: log.timestamp,
            level: log.level,
            message: log.message,
            source: log.source,
            trace_id: log.trace_id,
            labels: log.labels,
        };
        self.push_log(&l);
        Ok(())
    }

    /// Drains buffered lines and returns the count.
    ///
    /// NOTE: `BatchIngester::flush` requires a `&QuestDBClient` reference,
    /// which the port cannot carry.  The port implementation therefore drains
    /// the buffer and returns the row count; callers that need real HTTP
    /// delivery should use the inherent `flush(&client)` method directly.
    async fn flush(&mut self) -> TsResult<usize> {
        let lines = self.drain();
        Ok(lines.len())
    }

    fn pending(&self) -> usize {
        self.pending()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_labels() {
        let mut labels = HashMap::new();
        labels.insert("host".to_string(), "server1".to_string());
        labels.insert("region".to_string(), "us-west".to_string());

        let formatted = QuestDBClient::format_labels(&labels);
        assert!(formatted.contains("host=server1"));
        assert!(formatted.contains("region=us-west"));
    }

    #[test]
    fn test_escape_value() {
        let escaped = QuestDBClient::escape_value("Hello's World");
        assert!(escaped.contains("''"));
    }
}
