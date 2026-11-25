//! Integration and unit tests for `pheno-questdb`.
//!
//! Tests are split into two groups:
//!
//! 1. **Unit-level** (no server required) – test the batching / flush logic
//!    entirely in-process.
//! 2. **Integration-level** (`#[ignore]`) – spin up a `wiremock` HTTP server
//!    that behaves like the QuestDB `/v1/imp` endpoint, so flush semantics can
//!    be validated end-to-end.  Run with:
//!    ```text
//!    cargo test -p pheno-questdb -- --include-ignored
//!    ```

use chrono::{DateTime, Duration, TimeZone, Utc};
use pheno_questdb::{BatchIngester, LogEntry, Metric, QuestDBClient, TimestampPrecision};
use std::collections::HashMap;
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn make_metric(name: &str, value: f64, ts: DateTime<Utc>) -> Metric {
    let mut labels = HashMap::new();
    labels.insert("host".to_string(), "test-host".to_string());
    Metric {
        timestamp: ts,
        name: name.to_string(),
        value,
        labels,
    }
}

fn make_log(msg: &str, ts: DateTime<Utc>) -> LogEntry {
    LogEntry {
        timestamp: ts,
        level: "INFO".to_string(),
        message: msg.to_string(),
        source: "test".to_string(),
        trace_id: None,
        labels: HashMap::new(),
    }
}

// ---------------------------------------------------------------------------
// Unit tests – no network required
// ---------------------------------------------------------------------------

/// Batch does NOT flush before reaching the size threshold.
#[test]
fn batch_does_not_flush_below_threshold() {
    let mut batch = BatchIngester::new(5, TimestampPrecision::Nanoseconds);
    let now = Utc::now();

    for i in 0..4 {
        let needs_flush = batch.push_metric(&make_metric("cpu", i as f64, now));
        assert!(!needs_flush, "should not signal flush before threshold");
    }
    assert_eq!(batch.pending(), 4);
}

/// Batch signals flush exactly when reaching the configured size.
#[test]
fn batch_signals_flush_at_size_threshold() {
    let mut batch = BatchIngester::new(3, TimestampPrecision::Nanoseconds);
    let now = Utc::now();

    assert!(!batch.push_metric(&make_metric("cpu", 1.0, now)));
    assert!(!batch.push_metric(&make_metric("cpu", 2.0, now)));
    let needs_flush = batch.push_metric(&make_metric("cpu", 3.0, now));
    assert!(needs_flush, "third push should signal flush");
    assert_eq!(batch.pending(), 3);
}

/// `drain()` returns all buffered lines and leaves the batch empty.
#[test]
fn drain_clears_buffer_and_returns_lines() {
    let mut batch = BatchIngester::new(10, TimestampPrecision::Nanoseconds);
    let now = Utc::now();

    batch.push_metric(&make_metric("mem", 42.0, now));
    batch.push_log(&make_log("hello world", now));

    let lines = batch.drain();
    assert_eq!(lines.len(), 2, "two rows should be drained");
    assert_eq!(batch.pending(), 0, "buffer should be empty after drain");

    // Subsequent drain is a no-op
    let empty = batch.drain();
    assert!(empty.is_empty());
}

/// Batch correctly handles metrics with out-of-order timestamps: the buffer
/// accepts them without error (ordering is QuestDB's responsibility).
#[test]
fn out_of_order_timestamps_accepted_without_error() {
    let mut batch = BatchIngester::new(10, TimestampPrecision::Nanoseconds);
    let base = Utc.with_ymd_and_hms(2024, 1, 1, 0, 0, 0).unwrap();

    // Insert rows with timestamps going backwards in time
    let timestamps = [
        base + Duration::seconds(30),
        base + Duration::seconds(10),
        base + Duration::seconds(20),
        base,
    ];

    for (i, ts) in timestamps.iter().enumerate() {
        batch.push_metric(&make_metric("ooo", i as f64, *ts));
    }

    let lines = batch.drain();
    assert_eq!(lines.len(), 4);
    // All four distinct nanosecond timestamps should appear in the ILP lines
    for ts in &timestamps {
        let expected_ns = ts.timestamp_nanos_opt().unwrap_or(0).to_string();
        assert!(
            lines.iter().any(|l| l.ends_with(&expected_ns)),
            "expected ns timestamp {expected_ns} in drained lines"
        );
    }
}

/// Nanosecond precision encodes the full ns timestamp.
#[test]
fn timestamp_precision_nanoseconds() {
    let mut batch = BatchIngester::new(10, TimestampPrecision::Nanoseconds);
    let ts = Utc.with_ymd_and_hms(2024, 6, 15, 12, 0, 0).unwrap();
    batch.push_metric(&make_metric("prec", 1.0, ts));
    let lines = batch.drain();
    let expected = ts.timestamp_nanos_opt().unwrap().to_string();
    assert!(
        lines[0].ends_with(&expected),
        "ILP line should end with ns timestamp"
    );
}

/// Microsecond precision encodes the µs timestamp.
#[test]
fn timestamp_precision_microseconds() {
    let mut batch = BatchIngester::new(10, TimestampPrecision::Microseconds);
    let ts = Utc.with_ymd_and_hms(2024, 6, 15, 12, 0, 0).unwrap();
    batch.push_metric(&make_metric("prec", 1.0, ts));
    let lines = batch.drain();
    let expected = ts.timestamp_micros().to_string();
    assert!(
        lines[0].ends_with(&expected),
        "ILP line should end with µs timestamp"
    );
}

/// Millisecond precision encodes the ms timestamp.
#[test]
fn timestamp_precision_milliseconds() {
    let mut batch = BatchIngester::new(10, TimestampPrecision::Milliseconds);
    let ts = Utc.with_ymd_and_hms(2024, 6, 15, 12, 0, 0).unwrap();
    batch.push_metric(&make_metric("prec", 1.0, ts));
    let lines = batch.drain();
    let expected = ts.timestamp_millis().to_string();
    assert!(
        lines[0].ends_with(&expected),
        "ILP line should end with ms timestamp"
    );
}

/// Flushing an empty batch is a no-op (drain returns nothing).
#[test]
fn drain_on_empty_batch_is_noop() {
    let mut batch = BatchIngester::new(5, TimestampPrecision::Nanoseconds);
    assert_eq!(batch.pending(), 0);
    let lines = batch.drain();
    assert!(lines.is_empty());
}

/// After drain the batch can accept new rows again (shutdown-drain + reuse).
#[test]
fn batch_reusable_after_drain() {
    let mut batch = BatchIngester::new(5, TimestampPrecision::Nanoseconds);
    let now = Utc::now();

    batch.push_metric(&make_metric("a", 1.0, now));
    batch.drain();

    batch.push_metric(&make_metric("b", 2.0, now));
    assert_eq!(batch.pending(), 1);
    let lines = batch.drain();
    assert!(lines[0].contains("name=b"));
}

/// Mixed metric + log rows in the same batch are both preserved.
#[test]
fn mixed_metric_and_log_rows_in_batch() {
    let mut batch = BatchIngester::new(10, TimestampPrecision::Nanoseconds);
    let now = Utc::now();
    batch.push_metric(&make_metric("disk", 99.0, now));
    batch.push_log(&make_log("disk nearly full", now));
    let lines = batch.drain();
    assert_eq!(lines.len(), 2);
    assert!(lines.iter().any(|l| l.starts_with("metrics,")));
    assert!(lines.iter().any(|l| l.starts_with("logs,")));
}

/// Log entries with a trace ID include the correct trace_id tag.
#[test]
fn log_with_trace_id_includes_tag() {
    let mut batch = BatchIngester::new(10, TimestampPrecision::Nanoseconds);
    let ts = Utc::now();
    let mut log = make_log("traced event", ts);
    log.trace_id = Some("abc-123".to_string());
    batch.push_log(&log);
    let lines = batch.drain();
    assert!(lines[0].contains("trace_id=abc-123"));
}

/// Log entries without a trace ID fall back to `none`.
#[test]
fn log_without_trace_id_uses_none_sentinel() {
    let mut batch = BatchIngester::new(10, TimestampPrecision::Nanoseconds);
    let ts = Utc::now();
    batch.push_log(&make_log("untraced", ts));
    let lines = batch.drain();
    assert!(lines[0].contains("trace_id=none"));
}

/// Single-quote characters in log messages are escaped as `''`.
#[test]
fn log_message_single_quotes_are_escaped() {
    let mut batch = BatchIngester::new(10, TimestampPrecision::Nanoseconds);
    let ts = Utc::now();
    batch.push_log(&make_log("it's a problem", ts));
    let lines = batch.drain();
    assert!(
        lines[0].contains("it''s a problem"),
        "single quotes must be escaped"
    );
}

/// `TimestampPrecision::to_ilp_value` round-trips through all three variants.
#[test]
fn precision_to_ilp_value_all_variants() {
    let ts = Utc.with_ymd_and_hms(2024, 3, 14, 15, 9, 26).unwrap();
    assert_eq!(
        TimestampPrecision::Nanoseconds.to_ilp_value(&ts),
        ts.timestamp_nanos_opt().unwrap()
    );
    assert_eq!(
        TimestampPrecision::Microseconds.to_ilp_value(&ts),
        ts.timestamp_micros()
    );
    assert_eq!(
        TimestampPrecision::Milliseconds.to_ilp_value(&ts),
        ts.timestamp_millis()
    );
}

// ---------------------------------------------------------------------------
// Integration tests – require a live (or mock) QuestDB HTTP endpoint
// ---------------------------------------------------------------------------

/// Flush sends all buffered lines to `/v1/imp` in a single request and returns
/// the row count.
#[tokio::test]
#[ignore = "requires QuestDB or mock server; run with --include-ignored"]
async fn integration_flush_sends_batch_to_server() {
    let mock_server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/imp"))
        .respond_with(ResponseTemplate::new(200).set_body_string("OK"))
        .expect(1) // exactly one HTTP request (batched)
        .mount(&mock_server)
        .await;

    let client = QuestDBClient::new(&mock_server.uri());
    let mut batch = BatchIngester::new(100, TimestampPrecision::Nanoseconds);
    let now = Utc::now();

    for i in 0..5 {
        batch.push_metric(&make_metric("cpu", i as f64, now));
    }

    let flushed = batch.flush(&client).await.unwrap();
    assert_eq!(flushed, 5);
    assert_eq!(batch.pending(), 0);

    mock_server.verify().await;
}

/// Flush on an empty batch does not perform any HTTP request.
#[tokio::test]
#[ignore = "requires QuestDB or mock server; run with --include-ignored"]
async fn integration_flush_empty_batch_no_request() {
    let mock_server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/imp"))
        .respond_with(ResponseTemplate::new(200))
        .expect(0) // no requests expected
        .mount(&mock_server)
        .await;

    let client = QuestDBClient::new(&mock_server.uri());
    let mut batch = BatchIngester::new(10, TimestampPrecision::Nanoseconds);
    let flushed = batch.flush(&client).await.unwrap();
    assert_eq!(flushed, 0);

    mock_server.verify().await;
}

/// Out-of-order timestamps are forwarded as-is; QuestDB handles reordering.
/// The mock server accepts the payload and returns 200 (no server-side error).
#[tokio::test]
#[ignore = "requires QuestDB or mock server; run with --include-ignored"]
async fn integration_out_of_order_timestamps_accepted_by_server() {
    let mock_server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/imp"))
        .respond_with(ResponseTemplate::new(200).set_body_string("OK"))
        .expect(1)
        .mount(&mock_server)
        .await;

    let client = QuestDBClient::new(&mock_server.uri());
    let mut batch = BatchIngester::new(100, TimestampPrecision::Nanoseconds);
    let base = Utc.with_ymd_and_hms(2024, 1, 1, 0, 0, 0).unwrap();

    // Push rows with deliberately out-of-order timestamps
    for offset in [30i64, 10, 20, 0, 5] {
        batch.push_metric(&make_metric(
            "ooo",
            offset as f64,
            base + Duration::seconds(offset),
        ));
    }

    let flushed = batch.flush(&client).await.unwrap();
    assert_eq!(flushed, 5, "all 5 rows should be flushed");

    mock_server.verify().await;
}

/// Batch-drain on shutdown: after a graceful shutdown signal the caller drains
/// the buffer without a live server (simulated by flushing into a local Vec).
#[tokio::test]
#[ignore = "requires QuestDB or mock server; run with --include-ignored"]
async fn integration_shutdown_drain_flushes_remaining_rows() {
    let mock_server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/imp"))
        .respond_with(ResponseTemplate::new(200).set_body_string("OK"))
        .expect(1) // single flush at shutdown
        .mount(&mock_server)
        .await;

    let client = QuestDBClient::new(&mock_server.uri());
    let mut batch = BatchIngester::new(1000, TimestampPrecision::Nanoseconds); // large threshold, never auto-fires
    let now = Utc::now();

    // Simulate work accumulating below the size threshold
    for i in 0..7 {
        let _ = batch.push_metric(&make_metric("shutdown", i as f64, now));
    }
    assert_eq!(
        batch.pending(),
        7,
        "rows should be buffered before shutdown"
    );

    // Shutdown: explicit flush drains the remainder
    let flushed = batch.flush(&client).await.unwrap();
    assert_eq!(flushed, 7);
    assert_eq!(batch.pending(), 0);

    mock_server.verify().await;
}

/// Server-side error (non-2xx) propagates as `ApiError::Internal`.
#[tokio::test]
#[ignore = "requires QuestDB or mock server; run with --include-ignored"]
async fn integration_server_error_propagates() {
    let mock_server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/imp"))
        .respond_with(ResponseTemplate::new(500).set_body_string("Internal Server Error"))
        .mount(&mock_server)
        .await;

    let client = QuestDBClient::new(&mock_server.uri());
    let mut batch = BatchIngester::new(10, TimestampPrecision::Nanoseconds);
    let now = Utc::now();
    batch.push_metric(&make_metric("err", 1.0, now));

    let result = batch.flush(&client).await;
    assert!(result.is_err(), "5xx response should yield an error");
    let err_str = format!("{:?}", result.unwrap_err());
    assert!(err_str.contains("500"), "error should mention HTTP 500");
}
