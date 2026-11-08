//! Tracer Trait - Port Interface

use async_trait::async_trait;

use super::{SpanContext, SpanKind};

/// Tracer trait - primary port
#[async_trait]
pub trait Tracer: Send + Sync {
    /// Start a new span
    fn span(&self, name: &str) -> Box<dyn SpanHandle>;

    /// Start a child span
    fn span_with_parent(&self, name: &str, parent: &SpanContext) -> Box<dyn SpanHandle>;

    /// Start a span with kind
    fn span_with_kind(&self, name: &str, kind: SpanKind) -> Box<dyn SpanHandle>;

    /// Get the tracer name
    fn name(&self) -> &str;

    /// Get the tracer version
    fn version(&self) -> Option<&str>;
}

/// Span handle for finishing spans
pub trait SpanHandle: Send {
    fn set_attribute(&self, key: String, value: super::AttributeValue);
    fn add_event(&self, name: String);
    fn end(&self);
}

/// Concrete handle wrapping a [`super::Span`] with interior mutability so the
/// sync `SpanHandle` contract (which takes `&self`) can mutate the underlying
/// span safely across threads.
pub struct SpanHandleImpl {
    inner: std::sync::Mutex<super::Span>,
}

impl SpanHandleImpl {
    pub fn new(span: super::Span) -> Self {
        Self {
            inner: std::sync::Mutex::new(span),
        }
    }
}

impl SpanHandle for SpanHandleImpl {
    fn set_attribute(&self, key: String, value: super::AttributeValue) {
        if let Ok(mut span) = self.inner.lock() {
            span.set_attribute(key, value);
        }
    }

    fn add_event(&self, name: String) {
        if let Ok(mut span) = self.inner.lock() {
            span.add_event(name);
        }
    }

    fn end(&self) {
        if let Ok(mut span) = self.inner.lock() {
            span.end();
        }
    }
}

/// Span wrapper for scoped spans
pub struct ScopedSpan<'a> {
    tracer: &'a dyn Tracer,
    name: String,
    span: Box<dyn SpanHandle>,
}

impl<'a> ScopedSpan<'a> {
    pub fn new(tracer: &'a dyn Tracer, name: &str) -> Self {
        let span = tracer.span(name);
        Self {
            tracer,
            name: name.to_string(),
            span,
        }
    }

    pub fn with_attribute(self, key: &str, value: super::AttributeValue) -> Self {
        self.span.set_attribute(key.to_string(), value);
        self
    }

    pub fn with_event(self, name: &str) -> Self {
        self.span.add_event(name.to_string());
        self
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn tracer(&self) -> &dyn Tracer {
        self.tracer
    }
}

impl<'a> Drop for ScopedSpan<'a> {
    fn drop(&mut self) {
        self.span.end();
    }
}
