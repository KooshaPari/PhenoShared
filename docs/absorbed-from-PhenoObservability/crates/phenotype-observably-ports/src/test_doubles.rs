//! In-memory test doubles for [`CachePort`], [`TimeSeriesPort`], and [`MetricsPort`].
//!
//! Available only with the `test-util` Cargo feature.

use crate::cache::{CachePort, CacheResult};
use crate::metrics::{CounterEntry, GaugeEntry, HistogramEntry, Labels, MetricsPort};
use crate::timeseries::{TimeSeriesPort, TsLogEntry, TsMetric, TsResult};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

// ---------------------------------------------------------------------------
// InMemoryCache
// ---------------------------------------------------------------------------

/// Thread-safe in-memory implementation of [`CachePort`].
///
/// Entries never actually expire — this double is for logic tests only.
/// Use a real Dragonfly/Redis instance for TTL-dependent tests.
#[derive(Clone, Default)]
pub struct InMemoryCache {
    store: Arc<Mutex<HashMap<String, Vec<u8>>>>,
}

impl InMemoryCache {
    /// Inspect the raw store (useful in assertions).
    pub fn snapshot(&self) -> HashMap<String, Vec<u8>> {
        self.store.lock().unwrap().clone()
    }
}

#[async_trait]
impl CachePort for InMemoryCache {
    async fn get(&self, key: &str) -> CacheResult<Option<Vec<u8>>> {
        Ok(self.store.lock().unwrap().get(key).cloned())
    }

    async fn set(&self, key: &str, value: &[u8], _ttl_seconds: u64) -> CacheResult<()> {
        self.store
            .lock()
            .unwrap()
            .insert(key.to_owned(), value.to_vec());
        Ok(())
    }

    async fn delete(&self, key: &str) -> CacheResult<()> {
        self.store.lock().unwrap().remove(key);
        Ok(())
    }

    async fn expire(&self, key: &str, _ttl_seconds: u64) -> CacheResult<bool> {
        Ok(self.store.lock().unwrap().contains_key(key))
    }
}

// ---------------------------------------------------------------------------
// InMemoryTimeSeries
// ---------------------------------------------------------------------------

/// In-memory implementation of [`TimeSeriesPort`].
///
/// All ingested rows accumulate in `metrics` / `logs` until flushed; after
/// flush they move to `flushed_metrics` / `flushed_logs`.  Tests can
/// inspect either collection.
#[derive(Default)]
pub struct InMemoryTimeSeries {
    pending_metrics: Vec<TsMetric>,
    pending_logs: Vec<TsLogEntry>,
    pub flushed_metrics: Vec<TsMetric>,
    pub flushed_logs: Vec<TsLogEntry>,
}

impl InMemoryTimeSeries {
    /// Total number of rows that have been flushed.
    pub fn flushed_count(&self) -> usize {
        self.flushed_metrics.len() + self.flushed_logs.len()
    }
}

#[async_trait]
impl TimeSeriesPort for InMemoryTimeSeries {
    async fn ingest_metric(&mut self, metric: TsMetric) -> TsResult<()> {
        self.pending_metrics.push(metric);
        Ok(())
    }

    async fn ingest_log(&mut self, log: TsLogEntry) -> TsResult<()> {
        self.pending_logs.push(log);
        Ok(())
    }

    async fn flush(&mut self) -> TsResult<usize> {
        let count = self.pending_metrics.len() + self.pending_logs.len();
        self.flushed_metrics.append(&mut self.pending_metrics);
        self.flushed_logs.append(&mut self.pending_logs);
        Ok(count)
    }

    fn pending(&self) -> usize {
        self.pending_metrics.len() + self.pending_logs.len()
    }
}

// ---------------------------------------------------------------------------
// InMemoryMetrics
// ---------------------------------------------------------------------------

/// Thread-safe in-memory implementation of [`MetricsPort`].
///
/// Records every call verbatim so tests can assert on both the values and the
/// labels without needing a real Prometheus registry.
#[derive(Clone, Default)]
pub struct InMemoryMetrics {
    counters: Arc<Mutex<Vec<CounterEntry>>>,
    gauges: Arc<Mutex<Vec<GaugeEntry>>>,
    histograms: Arc<Mutex<Vec<HistogramEntry>>>,
}

impl InMemoryMetrics {
    /// All counter increments recorded so far (in insertion order).
    pub fn counters(&self) -> Vec<CounterEntry> {
        self.counters.lock().unwrap().clone()
    }

    /// All gauge sets recorded so far (in insertion order).
    pub fn gauges(&self) -> Vec<GaugeEntry> {
        self.gauges.lock().unwrap().clone()
    }

    /// All histogram observations recorded so far (in insertion order).
    pub fn histograms(&self) -> Vec<HistogramEntry> {
        self.histograms.lock().unwrap().clone()
    }

    /// Sum of all `delta` values for a counter with the given name.
    pub fn counter_total(&self, name: &str) -> u64 {
        self.counters
            .lock()
            .unwrap()
            .iter()
            .filter(|e| e.name == name)
            .map(|e| e.delta)
            .sum()
    }

    /// Most-recent gauge value for the given name, or `None` if never set.
    pub fn last_gauge(&self, name: &str) -> Option<f64> {
        self.gauges
            .lock()
            .unwrap()
            .iter()
            .rev()
            .find(|e| e.name == name)
            .map(|e| e.value)
    }

    /// All histogram values observed for the given name.
    pub fn histogram_values(&self, name: &str) -> Vec<f64> {
        self.histograms
            .lock()
            .unwrap()
            .iter()
            .filter(|e| e.name == name)
            .map(|e| e.value)
            .collect()
    }
}

impl MetricsPort for InMemoryMetrics {
    fn inc_counter(&self, name: &str, delta: u64, labels: Labels<'_>) {
        let entry = CounterEntry {
            name: name.to_owned(),
            delta,
            labels: labels
                .iter()
                .map(|(k, v)| (k.to_string(), v.to_string()))
                .collect(),
        };
        self.counters.lock().unwrap().push(entry);
    }

    fn set_gauge(&self, name: &str, value: f64, labels: Labels<'_>) {
        let entry = GaugeEntry {
            name: name.to_owned(),
            value,
            labels: labels
                .iter()
                .map(|(k, v)| (k.to_string(), v.to_string()))
                .collect(),
        };
        self.gauges.lock().unwrap().push(entry);
    }

    fn observe_histogram(&self, name: &str, value: f64, labels: Labels<'_>) {
        let entry = HistogramEntry {
            name: name.to_owned(),
            value,
            labels: labels
                .iter()
                .map(|(k, v)| (k.to_string(), v.to_string()))
                .collect(),
        };
        self.histograms.lock().unwrap().push(entry);
    }
}

// ---------------------------------------------------------------------------
// Unit tests (always compiled — no network required)
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::timeseries::{TsLogEntry, TsMetric};
    use chrono::Utc;
    use std::collections::HashMap;

    // --- CachePort object-safety sanity ---
    #[test]
    fn cache_port_is_object_safe() {
        let c: Box<dyn CachePort> = Box::new(InMemoryCache::default());
        drop(c);
    }

    // --- TimeSeriesPort object-safety sanity ---
    #[test]
    fn ts_port_is_object_safe() {
        let ts: Box<dyn TimeSeriesPort> = Box::new(InMemoryTimeSeries::default());
        drop(ts);
    }

    // --- InMemoryCache round-trip ---
    #[tokio::test]
    async fn cache_set_get_delete() {
        let cache = InMemoryCache::default();

        cache.set("hello", b"world", 30).await.unwrap();
        assert_eq!(cache.get("hello").await.unwrap(), Some(b"world".to_vec()));

        cache.delete("hello").await.unwrap();
        assert_eq!(cache.get("hello").await.unwrap(), None);
    }

    #[tokio::test]
    async fn cache_expire_returns_false_for_missing_key() {
        let cache = InMemoryCache::default();
        let existed = cache.expire("no-such-key", 60).await.unwrap();
        assert!(!existed);
    }

    #[tokio::test]
    async fn cache_expire_returns_true_for_present_key() {
        let cache = InMemoryCache::default();
        cache.set("k", b"v", 10).await.unwrap();
        let existed = cache.expire("k", 60).await.unwrap();
        assert!(existed);
    }

    // --- InMemoryTimeSeries round-trip ---
    fn make_metric(name: &str, value: f64) -> TsMetric {
        TsMetric {
            timestamp: Utc::now(),
            name: name.to_owned(),
            value,
            labels: HashMap::new(),
        }
    }

    fn make_log(msg: &str) -> TsLogEntry {
        TsLogEntry {
            timestamp: Utc::now(),
            level: "INFO".to_owned(),
            message: msg.to_owned(),
            source: "test".to_owned(),
            trace_id: None,
            labels: HashMap::new(),
        }
    }

    #[tokio::test]
    async fn ts_ingest_and_flush() {
        let mut ts = InMemoryTimeSeries::default();

        ts.ingest_metric(make_metric("cpu", 0.5)).await.unwrap();
        ts.ingest_log(make_log("hello")).await.unwrap();
        assert_eq!(ts.pending(), 2);

        let flushed = ts.flush().await.unwrap();
        assert_eq!(flushed, 2);
        assert_eq!(ts.pending(), 0);
        assert_eq!(ts.flushed_count(), 2);
    }

    #[tokio::test]
    async fn ts_flush_empty_is_zero() {
        let mut ts = InMemoryTimeSeries::default();
        let flushed = ts.flush().await.unwrap();
        assert_eq!(flushed, 0);
    }

    #[tokio::test]
    async fn ts_multiple_flush_accumulates() {
        let mut ts = InMemoryTimeSeries::default();
        ts.ingest_metric(make_metric("m1", 1.0)).await.unwrap();
        ts.flush().await.unwrap();
        ts.ingest_metric(make_metric("m2", 2.0)).await.unwrap();
        ts.flush().await.unwrap();
        assert_eq!(ts.flushed_metrics.len(), 2);
    }

    // --- MetricsPort object-safety ---
    #[test]
    fn metrics_port_is_object_safe() {
        let m: Box<dyn crate::metrics::MetricsPort> = Box::new(InMemoryMetrics::default());
        drop(m);
    }

    // --- InMemoryMetrics: counter increments accumulate ---
    #[test]
    fn metrics_counter_increments_accumulate() {
        let m = InMemoryMetrics::default();
        m.inc_counter("http.requests", 3, &[("method", "GET")]);
        m.inc_counter("http.requests", 7, &[("method", "GET")]);
        assert_eq!(m.counter_total("http.requests"), 10);
    }

    // --- InMemoryMetrics: inc() shorthand increments by 1 ---
    #[test]
    fn metrics_inc_shorthand_adds_one() {
        let m = InMemoryMetrics::default();
        m.inc("errors", &[("svc", "auth")]);
        m.inc("errors", &[("svc", "auth")]);
        m.inc("errors", &[("svc", "auth")]);
        assert_eq!(m.counter_total("errors"), 3);
    }

    // --- InMemoryMetrics: gauge set, last value wins ---
    #[test]
    fn metrics_gauge_last_value_wins() {
        let m = InMemoryMetrics::default();
        m.set_gauge("queue.depth", 10.0, &[]);
        m.set_gauge("queue.depth", 5.0, &[]);
        assert_eq!(m.last_gauge("queue.depth"), Some(5.0));
    }

    // --- InMemoryMetrics: gauge absent returns None ---
    #[test]
    fn metrics_gauge_absent_returns_none() {
        let m = InMemoryMetrics::default();
        assert_eq!(m.last_gauge("never.set"), None);
    }

    // --- InMemoryMetrics: histogram observations ---
    #[test]
    fn metrics_histogram_observations_recorded() {
        let m = InMemoryMetrics::default();
        m.observe_histogram("latency_ms", 10.0, &[("route", "/api")]);
        m.observe_histogram("latency_ms", 20.0, &[("route", "/api")]);
        m.observe_histogram("latency_ms", 30.0, &[("route", "/api")]);
        let vals = m.histogram_values("latency_ms");
        assert_eq!(vals, vec![10.0, 20.0, 30.0]);
    }

    // --- InMemoryMetrics: labels are carried through ---
    #[test]
    fn metrics_labels_carried() {
        let m = InMemoryMetrics::default();
        m.inc_counter("reqs", 1, &[("env", "prod"), ("region", "us-east-1")]);
        let entries = m.counters();
        assert_eq!(entries.len(), 1);
        assert_eq!(
            entries[0].labels.get("env").map(String::as_str),
            Some("prod")
        );
        assert_eq!(
            entries[0].labels.get("region").map(String::as_str),
            Some("us-east-1")
        );
    }

    // --- InMemoryMetrics: different metric names do not cross-contaminate ---
    #[test]
    fn metrics_names_are_independent() {
        let m = InMemoryMetrics::default();
        m.inc_counter("a", 5, &[]);
        m.inc_counter("b", 2, &[]);
        assert_eq!(m.counter_total("a"), 5);
        assert_eq!(m.counter_total("b"), 2);
    }

    // --- InMemoryMetrics: round-trip via Box<dyn MetricsPort> ---
    #[test]
    fn metrics_double_round_trip_via_dyn() {
        let m = InMemoryMetrics::default();
        let port: Box<dyn crate::metrics::MetricsPort> = Box::new(m.clone());
        port.inc("ticks", &[]);
        port.set_gauge("temp", 98.6, &[("unit", "F")]);
        port.observe_histogram("duration", 0.5, &[]);
        // inspect via the original handle
        assert_eq!(m.counter_total("ticks"), 1);
        assert_eq!(m.last_gauge("temp"), Some(98.6));
        assert_eq!(m.histogram_values("duration"), vec![0.5]);
    }
}
