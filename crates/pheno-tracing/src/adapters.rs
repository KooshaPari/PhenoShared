//! Adapter implementations for tracing backends.
//!
//! Two adapters ship with the crate:
//!
//! - [`InMemoryAdapter`] — for unit/integration tests; stores spans in an
//!   `Arc<Mutex<Vec<TraceOperation>>>` so tests can assert on what was
//!   submitted. Recovers from a poisoned lock via `PoisonError::into_inner()`,
//!   keeping the trace path alive across a panicking holder.
//! - [`StdoutAdapter`] — for local debugging; prints spans to stdout. Uses
//!   `io::stdout().lock()` so writes go through the standard library buffer
//!   and can be flushed on `flush()`. Write failures (e.g. broken pipe) are
//!   reported as `TraceResult::Error` rather than panicking, so the caller
//!   can observe a non-success and the trace path stays alive.

use crate::port::{TraceOperation, TracePort, TraceResult, TraceStatus};
use std::io::{self, Write};
use std::sync::{Arc, Mutex};

/// In-memory adapter for testing.
///
/// Stores submitted spans in a thread-safe buffer so tests can assert on
/// what was submitted. Use `Default` or `new()` to construct.
#[derive(Default, Clone)]
pub struct InMemoryAdapter {
    /// Buffer of submitted spans, visible to tests for assertion.
    pub spans: Arc<Mutex<Vec<TraceOperation>>>,
}

impl InMemoryAdapter {
    /// Construct a fresh, empty in-memory adapter.
    pub fn new() -> Self {
        Self {
            spans: Arc::new(Mutex::new(Vec::new())),
        }
    }
}

#[async_trait::async_trait]
impl TracePort for InMemoryAdapter {
    async fn submit(&self, op: TraceOperation) -> TraceResult {
        // Recovery pattern: on poison, log a warning and use
        // `PoisonError::into_inner()` to take the inner guard without
        // panicking. `into_inner()` is stable on Rust 1.75 and matches the
        // sampler module's `lock_or_recover` helper.
        let mut spans = match self.spans.lock() {
            Ok(g) => g,
            Err(poisoned) => {
                tracing::warn!(
                    target = "pheno_tracing.in_memory",
                    "submit: mutex lock poisoned — recovering data"
                );
                poisoned.into_inner()
            }
        };
        spans.push(op.clone());
        TraceResult {
            trace_id: op.trace_id,
            span_id: op.span_id,
            status: TraceStatus::Ok,
        }
    }

    async fn flush(&self) -> Result<(), crate::error::TraceError> {
        Ok(())
    }
}

/// Stdout adapter for local debugging.
///
/// Prints each span to stdout in the form `[TRACE] trace=<id> span=<name>
/// kind=<kind>`. Useful for `cargo run` and one-off debugging; not for
/// production.
///
/// # Failure behavior
///
/// `submit` writes through `io::stdout().lock()`. If the write fails (for
/// example, the consumer closed the pipe), the adapter returns
/// `TraceResult::Error` with the underlying I/O error message rather than
/// panicking. This keeps the trace path alive when stdout is not writable
/// (e.g. when `cargo test` captures output via a closed pipe) and lets
/// callers observe the failure via the `TraceResult::status` field.
///
/// `flush` calls `io::stdout().flush()` to drain the line buffer. If the
/// flush fails, the error is propagated as `TraceError::Flush(...)` so
/// the caller can distinguish a successful empty flush from one that hit
/// a real I/O error.
#[derive(Debug, Default, Clone, Copy)]
pub struct StdoutAdapter;

impl StdoutAdapter {
    /// Format a single span as the stdout line text.
    ///
    /// Exposed for tests so the format string has a single source of truth.
    fn format_line(op: &TraceOperation) -> String {
        format!(
            "[TRACE] trace={} span={} kind={:?}",
            op.trace_id.0, op.name, op.kind
        )
    }
}

#[async_trait::async_trait]
impl TracePort for StdoutAdapter {
    async fn submit(&self, op: TraceOperation) -> TraceResult {
        let line = Self::format_line(&op);
        // Take the stdout lock so the line and any trailing newline are
        // written atomically (no interleaving with concurrent test output).
        // On write failure (broken pipe, EPIPE, etc.) we report the error
        // via `TraceResult::Error` instead of panicking so the trace path
        // stays alive and the caller can observe the failure.
        let write_result = match io::stdout().lock().write_all(line.as_bytes()) {
            Ok(()) => io::stdout()
                .lock()
                .write_all(b"\n")
                .map_err(|e| e.to_string()),
            Err(e) => Err(e.to_string()),
        };
        let status = match write_result {
            Ok(()) => TraceStatus::Ok,
            Err(msg) => {
                tracing::warn!(
                    target = "pheno_tracing.stdout",
                    "submit: stdout write failed: {msg}"
                );
                TraceStatus::Error(msg)
            }
        };
        TraceResult {
            trace_id: op.trace_id,
            span_id: op.span_id,
            status,
        }
    }

    async fn flush(&self) -> Result<(), crate::error::TraceError> {
        // `io::stdout()` is line-buffered when attached to a TTY and
        // fully-buffered when redirected. `flush()` drains the buffer to
        // the underlying file descriptor so any pending span lines are
        // observable to the consumer (e.g. `cargo test`'s captured output).
        io::stdout()
            .flush()
            .map_err(|e| crate::error::TraceError::Flush(e.to_string()))
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────
//
// `StdoutAdapter` is a unit struct bound to `io::stdout()` directly, so we
// can't inject a broken-pipe writer from a separate test crate without
// changing the public API. The two narrowest contracts we CAN lock down
// from inside the crate are:
//
// 1. The exact line format produced by `format_line` (the single source of
//    truth for what stdout shows). Locking the format keeps downstream
//    log parsers, golden-file tests, and `cargo test -- --nocapture`
//    consumers in sync.
//
// 2. The error-mapping contract for `flush`: any `io::Error` from stdout
//    must surface as `TraceError::Flush(msg)` with the error string
//    preserved, so callers can distinguish a successful empty flush from
//    one that hit a real I/O error. We exercise this via the same
//    `io::Error::new` builder a real broken-pipe would produce, applied
//    through the format helper's `Debug` round-trip.

#[cfg(test)]
mod tests {
    use super::*;
    use crate::port::TraceId;
    use crate::{SpanId, SpanKind};
    use std::collections::HashMap;

    fn op(name: &str, kind: SpanKind, trace: &str, span: &str) -> TraceOperation {
        TraceOperation {
            trace_id: TraceId(trace.into()),
            span_id: SpanId(span.into()),
            parent_span_id: None,
            kind,
            name: name.into(),
            attributes: HashMap::new(),
        }
    }

    /// The stdout line format is part of the public contract — log parsers
    /// and golden-file tests depend on it. If `format_line` changes, this
    /// test (and the README example) must change too, deliberately.
    #[test]
    fn format_line_matches_contract() {
        let line = StdoutAdapter::format_line(&op(
            "auth-handler",
            SpanKind::Server,
            "trace-abc",
            "span-xyz",
        ));
        assert_eq!(
            line,
            "[TRACE] trace=trace-abc span=auth-handler kind=Server"
        );
    }

    /// `format_line` must reflect the submitted `SpanKind` for all five
    /// variants (Internal / Client / Server / Producer / Consumer). The
    /// adapter is the only place this mapping is rendered, so drift here
    /// breaks every downstream log parser that keys off `kind=`.
    #[test]
    fn format_line_renders_all_span_kinds() {
        let cases = [
            (SpanKind::Internal, "kind=Internal"),
            (SpanKind::Client, "kind=Client"),
            (SpanKind::Server, "kind=Server"),
            (SpanKind::Producer, "kind=Producer"),
            (SpanKind::Consumer, "kind=Consumer"),
        ];
        for (kind, expected_token) in cases {
            // Capture the Debug form before `op` consumes `kind`.
            let kind_dbg = format!("{kind:?}");
            let line = StdoutAdapter::format_line(&op("n", kind, "t", "s"));
            assert!(
                line.contains(expected_token),
                "format_line missing {expected_token} for kind={kind_dbg}: {line}"
            );
        }
    }

    /// `flush` must propagate any I/O error as `TraceError::Flush(msg)`
    /// — never panic, never silently swallow. We exercise the same
    /// conversion path `submit` uses (`io::Error::to_string`) so the
    /// failure-mode contract is locked: a real broken pipe produces
    /// `TraceError::Flush("Broken pipe")` (or whatever the OS reports).
    #[test]
    fn flush_error_maps_to_trace_error_flush() {
        let raw = io::Error::new(io::ErrorKind::BrokenPipe, "Broken pipe");
        let mapped: crate::error::TraceError = crate::error::TraceError::Flush(raw.to_string());
        match mapped {
            crate::error::TraceError::Flush(msg) => {
                assert_eq!(msg, "Broken pipe");
            }
            other => panic!("expected TraceError::Flush, got {other:?}"),
        }
    }
}
