//! Distributed tracing utilities with TraceContext and span management.
//!
//! Absorbed from `helix-tracing` (archived 2026-03-26).
//! Original: <https://github.com/KooshaPari/helix-tracing>

use std::fmt;

pub use ::tracing::Level;
use tracing_subscriber::fmt::format::FmtSpan;
use tracing_subscriber::{prelude::*, EnvFilter};

/// Configuration for the tracing subscriber.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TracingConfig {
    /// Minimum tracing level (e.g. `"info"`, `"debug"`).
    pub level: String,
    /// Emit `ENTER`/`EXIT` span events.
    pub span_events: bool,
    /// Include OS thread IDs in log output.
    pub include_thread_ids: bool,
    /// Include OS thread names in log output.
    pub include_thread_names: bool,
    /// Include the crate/module target in log output.
    pub target: bool,
}

impl Default for TracingConfig {
    fn default() -> Self {
        Self {
            level: "info".to_string(),
            span_events: false,
            include_thread_ids: false,
            include_thread_names: false,
            target: true,
        }
    }
}

impl TracingConfig {
    /// Create a config with the given level string; all other fields use defaults.
    pub fn new(level: impl Into<String>) -> Self {
        Self {
            level: level.into(),
            ..Self::default()
        }
    }

    /// Toggle span enter/exit events.
    pub fn with_span_events(mut self, span_events: bool) -> Self {
        self.span_events = span_events;
        self
    }

    /// Toggle thread ID emission.
    pub fn with_thread_ids(mut self, include_thread_ids: bool) -> Self {
        self.include_thread_ids = include_thread_ids;
        self
    }

    /// Toggle thread name emission.
    pub fn with_thread_names(mut self, include_thread_names: bool) -> Self {
        self.include_thread_names = include_thread_names;
        self
    }

    /// Toggle module target emission.
    pub fn with_target(mut self, target: bool) -> Self {
        self.target = target;
        self
    }
}

/// Install a global tracing subscriber using the provided config.
///
/// Returns an error if a global subscriber is already installed.
pub fn init_tracing(config: TracingConfig) -> Result<(), tracing_subscriber::util::TryInitError> {
    build_subscriber(&config).try_init()
}

/// Build (but do not install) a subscriber from `config`.
pub fn build_subscriber(
    config: &TracingConfig,
) -> impl ::tracing::Subscriber + Send + Sync + 'static {
    let filter =
        EnvFilter::try_new(config.level.as_str()).unwrap_or_else(|_| EnvFilter::new("info"));

    let fmt_layer = tracing_subscriber::fmt::layer()
        .with_target(config.target)
        .with_thread_ids(config.include_thread_ids)
        .with_thread_names(config.include_thread_names)
        .with_span_events(if config.span_events {
            FmtSpan::FULL
        } else {
            FmtSpan::NONE
        });

    tracing_subscriber::registry().with(filter).with(fmt_layer)
}

/// Generate a new random span ID (UUID v4).
pub fn span_id() -> String {
    uuid::Uuid::new_v4().to_string()
}

/// Generate a new random trace ID (UUID v4).
pub fn trace_id() -> String {
    uuid::Uuid::new_v4().to_string()
}

/// Convert a [`tracing::Level`] to its canonical lowercase string representation.
pub fn level_as_str(level: Level) -> &'static str {
    match level {
        Level::TRACE => "trace",
        Level::DEBUG => "debug",
        Level::INFO => "info",
        Level::WARN => "warn",
        Level::ERROR => "error",
    }
}

/// A typed key for trace attribute maps.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct TraceKey<'a>(pub &'a str);

impl fmt::Display for TraceKey<'_> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.0)
    }
}

/// Pairs a trace ID with a span ID to propagate distributed request context.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TraceContext {
    /// Root-level identifier for the full request chain.
    pub trace_id: String,
    /// Identifier for this specific unit of work within the trace.
    pub span_id: String,
}

impl TraceContext {
    /// Create a new context with freshly-generated IDs.
    pub fn new() -> Self {
        Self {
            trace_id: trace_id(),
            span_id: span_id(),
        }
    }
}

impl Default for TraceContext {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn creates_non_empty_span_ids() {
        let id = span_id();
        assert!(!id.is_empty());
    }

    #[test]
    fn creates_non_empty_trace_ids() {
        let id = trace_id();
        assert!(!id.is_empty());
    }

    #[test]
    fn trace_context_ids_differ() {
        let ctx = TraceContext::new();
        assert!(!ctx.trace_id.is_empty());
        assert!(!ctx.span_id.is_empty());
        assert_ne!(ctx.trace_id, ctx.span_id);
    }

    #[test]
    fn distinct_contexts_have_distinct_ids() {
        let a = TraceContext::new();
        let b = TraceContext::new();
        assert_ne!(a.trace_id, b.trace_id);
        assert_ne!(a.span_id, b.span_id);
    }

    #[test]
    fn level_strings_are_correct() {
        assert_eq!(level_as_str(Level::TRACE), "trace");
        assert_eq!(level_as_str(Level::DEBUG), "debug");
        assert_eq!(level_as_str(Level::INFO), "info");
        assert_eq!(level_as_str(Level::WARN), "warn");
        assert_eq!(level_as_str(Level::ERROR), "error");
    }

    #[test]
    fn default_tracing_config() {
        let config = TracingConfig::default();
        assert_eq!(config.level, "info");
        assert!(!config.span_events);
        assert!(config.target);
    }

    #[test]
    fn tracing_config_builder_chain() {
        let config = TracingConfig::new("debug")
            .with_span_events(true)
            .with_thread_ids(true)
            .with_thread_names(true)
            .with_target(false);

        assert_eq!(config.level, "debug");
        assert!(config.span_events);
        assert!(config.include_thread_ids);
        assert!(config.include_thread_names);
        assert!(!config.target);
    }
}
