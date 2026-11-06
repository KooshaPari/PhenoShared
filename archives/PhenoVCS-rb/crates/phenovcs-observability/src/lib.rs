//! PhenoVCS observability substrate — thin re-export of pheno-tracing (ADR-012, ADR-036).
//!
//! ## Quickstart
//!
//! ```no_run
//! use phenovcs_observability::{emit_span, otlp_endpoint, SERVICE_NAME};
//!
//! let mut attrs = std::collections::HashMap::new();
//! attrs.insert("op".to_string(), "init".to_string());
//! emit_span("phenovcs.init", attrs);
//! ```

use pheno_tracing::{
    adapters::StdoutAdapter,
    port::{SpanId, SpanKind, TraceId, TraceOperation, TracePort},
};
use std::collections::HashMap;
use std::sync::Arc;

pub const SERVICE_NAME: &str = "phenovcs";
pub const DEFAULT_OTLP_ENDPOINT: &str = "http://localhost:4317";

pub fn otlp_endpoint() -> String {
    std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT")
        .unwrap_or_else(|_| DEFAULT_OTLP_ENDPOINT.to_string())
}

pub fn build_span(
    trace_id: &str,
    span_id: &str,
    parent_span_id: Option<&str>,
    name: &str,
    kind: SpanKind,
    attributes: HashMap<String, String>,
) -> TraceOperation {
    TraceOperation {
        trace_id: TraceId(trace_id.to_string()),
        span_id: SpanId(span_id.to_string()),
        parent_span_id: parent_span_id.map(|s| SpanId(s.to_string())),
        kind,
        name: name.to_string(),
        attributes,
    }
}

pub fn next_trace_id() -> String {
    use std::sync::atomic::{AtomicU64, Ordering};
    static COUNTER: AtomicU64 = AtomicU64::new(0);
    let n = COUNTER.fetch_add(1, Ordering::SeqCst);
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    format!("phenovcs-trace-{}-{}", ts, n)
}

pub async fn submit_span(op: TraceOperation) {
    let port: Arc<dyn TracePort> = Arc::new(StdoutAdapter);
    let _ = port.submit(op).await;
    let _ = port.flush().await;
}

pub async fn emit_span(name: &str, attributes: HashMap<String, String>) {
    let trace_id = next_trace_id();
    let op = build_span(
        &trace_id,
        &format!("{}-{}", name, trace_id),
        None,
        name,
        SpanKind::Internal,
        attributes,
    );
    submit_span(op).await;
}

pub use pheno_tracing::compat::{debug, error, info, instrument, span, trace, warn};
