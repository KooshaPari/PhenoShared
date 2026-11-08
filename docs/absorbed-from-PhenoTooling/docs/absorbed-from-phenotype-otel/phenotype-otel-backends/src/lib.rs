//! Extensible observability backends for `phenotype-otel`.
//!
//! Provides a [`BackendRegistry`] that allows registering arbitrary [`Backend`]
//! implementations, plus built-in [`StdoutBackend`] and [`OtlpBackend`] structs.
//!
//! The [`Span`] type is a backend-local data record (Serialize/Deserialize).
//! It is intentionally decoupled from `phenotype-otel`'s internal tracer so
//! this crate can be consumed without depending on the live OTLP pipeline.
//! Future versions will provide `From`/`Into` conversions from the upstream
//! `opentelemetry::trace::SpanContext` (see FLEET_DAG L4 #80 follow-ups).

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::SystemTime;
use thiserror::Error;

/// Errors that can occur when interacting with a backend.
#[derive(Debug, Error, PartialEq)]
pub enum BackendError {
    /// Exporting spans to the backend failed.
    #[error("export failed: {0}")]
    ExportFailed(String),
    /// Health check against the backend failed.
    #[error("health check failed: {0}")]
    HealthCheckFailed(String),
}

/// Backend-local data record representing a span ready to be exported.
///
/// Self-contained: carries everything a backend needs to serialize, log, or
/// forward the span. The wire format is JSON (via `serde_json`).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Span {
    /// Human-readable span name.
    pub name: String,
    /// 32-hex-char trace id.
    pub trace_id: String,
    /// 16-hex-char span id.
    pub span_id: String,
    /// Wall-clock start time.
    pub start_time: SystemTime,
    /// Wall-clock end time.
    pub end_time: SystemTime,
    /// Key-value attributes (stringly-typed for the wire format).
    pub attributes: Vec<(String, String)>,
}

impl Span {
    /// Create a minimal span for testing or simple use cases.
    pub fn new(
        name: impl Into<String>,
        trace_id: impl Into<String>,
        span_id: impl Into<String>,
    ) -> Self {
        let now = SystemTime::now();
        Self {
            name: name.into(),
            trace_id: trace_id.into(),
            span_id: span_id.into(),
            start_time: now,
            end_time: now,
            attributes: Vec::new(),
        }
    }

    /// Attach a key-value attribute to the span.
    #[must_use]
    pub fn with_attribute(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.attributes.push((key.into(), value.into()));
        self
    }
}

/// Trait for observability backends that can receive and export spans.
pub trait Backend: Send + Sync {
    /// Return the backend's canonical name.
    fn name(&self) -> &str;
    /// Export a slice of spans to the backend.
    fn export(&self, spans: &[Span]) -> Result<(), BackendError>;
    /// Check whether the backend is healthy.
    fn health(&self) -> Result<(), BackendError>;
}

/// Registry for named observability backends.
pub struct BackendRegistry {
    backends: HashMap<String, Box<dyn Backend>>,
}

impl Default for BackendRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl BackendRegistry {
    /// Create a new empty registry.
    pub fn new() -> Self {
        Self {
            backends: HashMap::new(),
        }
    }

    /// Register a backend under the given name.
    ///
    /// If a backend with the same name already exists, it is replaced.
    pub fn register(&mut self, name: &str, backend: Box<dyn Backend>) {
        self.backends.insert(name.to_string(), backend);
    }

    /// Retrieve a backend by name.
    pub fn get(&self, name: &str) -> Option<&dyn Backend> {
        self.backends.get(name).map(|b| b.as_ref())
    }

    /// List all registered backend names.
    pub fn list(&self) -> Vec<String> {
        let mut names: Vec<String> = self.backends.keys().cloned().collect();
        names.sort();
        names
    }
}

/// Backend that prints spans to stdout as JSON lines.
pub struct StdoutBackend;

impl StdoutBackend {
    /// Create a new stdout backend.
    pub fn new() -> Self {
        Self
    }
}

impl Default for StdoutBackend {
    fn default() -> Self {
        Self::new()
    }
}

impl Backend for StdoutBackend {
    fn name(&self) -> &str {
        "stdout"
    }

    fn export(&self, spans: &[Span]) -> Result<(), BackendError> {
        for span in spans {
            let line = serde_json::to_string(span)
                .map_err(|e| BackendError::ExportFailed(e.to_string()))?;
            println!("{line}");
        }
        Ok(())
    }

    fn health(&self) -> Result<(), BackendError> {
        Ok(())
    }
}

/// Backend that exports spans via OTLP (stub implementation).
pub struct OtlpBackend;

impl OtlpBackend {
    /// Create a new OTLP backend.
    pub fn new() -> Self {
        Self
    }
}

impl Default for OtlpBackend {
    fn default() -> Self {
        Self::new()
    }
}

impl Backend for OtlpBackend {
    fn name(&self) -> &str {
        "otlp"
    }

    fn export(&self, _spans: &[Span]) -> Result<(), BackendError> {
        // Stub: in a real implementation this would send spans over HTTP/gRPC.
        Ok(())
    }

    fn health(&self) -> Result<(), BackendError> {
        // Stub: in a real implementation this would probe the collector.
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn registry_registers_backend() {
        let mut registry = BackendRegistry::new();
        let backend = StdoutBackend::new();
        registry.register("stdout", Box::new(backend));
        let retrieved = registry.get("stdout");
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().name(), "stdout");
    }

    #[test]
    fn stdout_backend_exports_spans() {
        let backend = StdoutBackend::new();
        let spans = vec![
            Span::new("test-span", "trace-1", "span-1"),
            Span::new("test-span-2", "trace-1", "span-2"),
        ];
        let result = backend.export(&spans);
        assert!(result.is_ok());
    }

    #[test]
    fn otlp_backend_name_is_otlp() {
        let backend = OtlpBackend::new();
        assert_eq!(backend.name(), "otlp");
    }

    #[test]
    fn registry_lists_backends() {
        let mut registry = BackendRegistry::new();
        registry.register("stdout", Box::new(StdoutBackend::new()));
        registry.register("otlp", Box::new(OtlpBackend::new()));
        let mut names = registry.list();
        names.sort();
        assert_eq!(names, vec!["otlp", "stdout"]);
    }

    #[test]
    fn registry_get_missing_returns_none() {
        let registry = BackendRegistry::new();
        assert!(registry.get("missing").is_none());
    }

    #[test]
    fn stdout_backend_health_ok() {
        let backend = StdoutBackend::new();
        assert!(backend.health().is_ok());
    }

    #[test]
    fn otlp_backend_health_ok() {
        let backend = OtlpBackend::new();
        assert!(backend.health().is_ok());
    }

    #[test]
    fn backend_error_export_failed_display() {
        let err = BackendError::ExportFailed("connection refused".to_string());
        assert!(err.to_string().contains("export failed"));
        assert!(err.to_string().contains("connection refused"));
    }

    #[test]
    fn backend_error_health_check_failed_display() {
        let err = BackendError::HealthCheckFailed("timeout".to_string());
        assert!(err.to_string().contains("health check failed"));
        assert!(err.to_string().contains("timeout"));
    }

    #[test]
    fn otlp_backend_export_empty_is_ok() {
        let backend = OtlpBackend::new();
        let result = backend.export(&[]);
        assert!(result.is_ok());
    }

    #[test]
    fn backend_registry_default_is_empty() {
        let registry = BackendRegistry::default();
        assert!(registry.list().is_empty());
    }

    #[test]
    fn span_with_attribute() {
        let span = Span::new("test", "trace-1", "span-1")
            .with_attribute("env", "prod")
            .with_attribute("region", "us-west");
        assert_eq!(span.attributes.len(), 2);
        assert_eq!(span.attributes[0], ("env".to_string(), "prod".to_string()));
    }

    #[test]
    fn span_serde_roundtrip() {
        let span = Span::new("test", "trace-1", "span-1");
        let json = serde_json::to_string(&span).unwrap();
        let parsed: Span = serde_json::from_str(&json).unwrap();
        assert_eq!(span, parsed);
    }
}
