//! Tracer Provider - Use Case

use async_trait::async_trait;
use std::sync::Arc;

use crate::domain::*;

pub struct TracerProviderBuilder {
    name: String,
    version: Option<String>,
    sampler: Box<dyn Sampler>,
    exporter: Option<Box<dyn SpanExporter>>,
}

impl TracerProviderBuilder {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            version: None,
            sampler: Box::new(AlwaysOnSampler),
            exporter: None,
        }
    }

    pub fn version(mut self, version: impl Into<String>) -> Self {
        self.version = Some(version.into());
        self
    }

    pub fn with_sampler(mut self, sampler: impl Sampler + 'static) -> Self {
        self.sampler = Box::new(sampler);
        self
    }

    pub fn with_exporter(mut self, exporter: impl SpanExporter + 'static) -> Self {
        self.exporter = Some(Box::new(exporter));
        self
    }

    pub fn build(self) -> TracerProvider {
        TracerProvider {
            name: self.name,
            version: self.version,
            sampler: Arc::new(self.sampler),
            exporter: self.exporter.map(Arc::new),
        }
    }
}

pub struct TracerProvider {
    name: String,
    version: Option<String>,
    sampler: Arc<Box<dyn Sampler>>,
    exporter: Option<Arc<Box<dyn SpanExporter>>>,
}

impl TracerProvider {
    pub fn builder(name: impl Into<String>) -> TracerProviderBuilder {
        TracerProviderBuilder::new(name)
    }

    pub fn tracer(&self) -> TracerInstance<'_> {
        TracerInstance { provider: self }
    }

    pub fn sampler(&self) -> &dyn Sampler {
        self.sampler.as_ref().as_ref()
    }

    pub async fn shutdown(&self) -> TraceResult<()> {
        if let Some(ref exporter) = self.exporter {
            exporter.shutdown().await?;
        }
        Ok(())
    }
}

pub struct TracerInstance<'a> {
    provider: &'a TracerProvider,
}

impl<'a> Tracer for TracerInstance<'a> {
    fn span(&self, name: &str) -> Box<dyn SpanHandle> {
        let span = Span::new(name, uuid::Uuid::new_v4());
        Box::new(SpanHandleImpl::new(span)) as Box<dyn SpanHandle>
    }

    fn span_with_parent(&self, name: &str, parent: &SpanContext) -> Box<dyn SpanHandle> {
        let span = Span::new(name, parent.trace_id);
        Box::new(SpanHandleImpl::new(span)) as Box<dyn SpanHandle>
    }

    fn span_with_kind(&self, name: &str, kind: SpanKind) -> Box<dyn SpanHandle> {
        let span = Span::new(name, uuid::Uuid::new_v4()).with_kind(kind);
        Box::new(SpanHandleImpl::new(span)) as Box<dyn SpanHandle>
    }

    fn name(&self) -> &str {
        &self.provider.name
    }

    fn version(&self) -> Option<&str> {
        self.provider.version.as_deref()
    }
}

/// Sampler trait
pub trait Sampler: Send + Sync {
    fn should_sample(&self, trace_id: uuid::Uuid) -> bool;
}

/// Always on sampler
pub struct AlwaysOnSampler;

impl Sampler for AlwaysOnSampler {
    fn should_sample(&self, _trace_id: uuid::Uuid) -> bool {
        true
    }
}

/// Always off sampler
pub struct AlwaysOffSampler;

impl Sampler for AlwaysOffSampler {
    fn should_sample(&self, _trace_id: uuid::Uuid) -> bool {
        false
    }
}

/// Span exporter - secondary port
#[async_trait]
pub trait SpanExporter: Send + Sync {
    async fn export(&self, spans: Vec<Span>) -> TraceResult<()>;
    async fn shutdown(&self) -> TraceResult<()>;
}
