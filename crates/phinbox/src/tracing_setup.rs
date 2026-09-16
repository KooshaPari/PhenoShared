//! Structured tracing for popup lifecycle events.
//!
//! We never log entered values — only request IDs, status, elapsed time,
//! renderer, and platform.

use crate::spec::{ElicitResponse, PromptSpec};

/// Emit a tracing event when a popup starts rendering.
pub fn trace_request_start(request_id: &str, spec: &PromptSpec) {
    tracing::info!(
        target: "phinbox",
        request_id,
        title = spec.title.as_str(),
        field_kind = field_kind_str(&spec.field),
        urgency = urgency_str(spec.urgency),
        timeout_secs = spec.timeout_secs,
        "popup opened"
    );
}

/// Emit a tracing event when a popup closes (any outcome).
pub fn trace_request_end(request_id: &str, response: &ElicitResponse) {
    let status = match response {
        ElicitResponse::Answered { .. } => "answered",
        ElicitResponse::Cancelled { .. } => "cancelled",
        ElicitResponse::TimedOut { .. } => "timed_out",
        ElicitResponse::Failed { .. } => "failed",
    };
    tracing::info!(
        target: "phinbox",
        request_id,
        status,
        "popup closed"
    );
}

fn field_kind_str(spec: &crate::spec::FieldSpec) -> &'static str {
    use crate::spec::FieldSpec;
    match spec {
        FieldSpec::Text { secret: true, .. } => "text(secret)",
        FieldSpec::Text { .. } => "text",
        FieldSpec::LongText { .. } => "long_text",
        FieldSpec::Integer { .. } => "integer",
        FieldSpec::Choice { .. } => "choice",
        FieldSpec::Boolean { .. } => "boolean",
        FieldSpec::DateTime { .. } => "datetime",
    }
}

fn urgency_str(u: crate::spec::Urgency) -> &'static str {
    use crate::spec::Urgency;
    match u {
        Urgency::Info => "info",
        Urgency::Warning => "warning",
        Urgency::Error => "error",
        Urgency::Secret => "secret",
    }
}

/// Install a `tracing` subscriber that emits to stderr, with an env-filter
/// honoring `RUST_LOG`. Idempotent — safe to call multiple times.
pub fn init() {
    use std::sync::OnceLock;

    static INIT: OnceLock<()> = OnceLock::new();
    INIT.get_or_init(|| {
        let env_filter = tracing_subscriber::EnvFilter::try_from_default_env()
            .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info"));
        let _ = tracing_subscriber::fmt()
            .with_env_filter(env_filter)
            .with_writer(std::io::stderr)
            .with_target(false)
            .try_init();
    });
}
