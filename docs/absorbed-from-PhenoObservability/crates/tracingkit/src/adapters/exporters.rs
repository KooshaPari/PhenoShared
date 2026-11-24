//! Span Exporters

use async_trait::async_trait;
use phenotype_observably_macros::async_instrumented;

use crate::application::SpanExporter;
use crate::domain::{Span, TraceResult};

/// Console exporter for debugging
pub struct ConsoleExporter;

impl ConsoleExporter {
    pub fn new() -> Self {
        Self
    }
}

impl Default for ConsoleExporter {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl SpanExporter for ConsoleExporter {
    #[async_instrumented]
    async fn export(&self, spans: Vec<Span>) -> TraceResult<()> {
        for span in spans {
            println!("Span: {} - {:?}", span.name, span.status);
        }
        Ok(())
    }

    #[async_instrumented]
    async fn shutdown(&self) -> TraceResult<()> {
        Ok(())
    }
}

/// Memory exporter for testing
pub struct MemoryExporter {
    spans: std::sync::Arc<parking_lot::RwLock<Vec<Span>>>,
}

impl MemoryExporter {
    pub fn new() -> Self {
        Self {
            spans: std::sync::Arc::new(parking_lot::RwLock::new(Vec::new())),
        }
    }

    pub fn spans(&self) -> Vec<Span> {
        self.spans.read().clone()
    }
}

impl Default for MemoryExporter {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl SpanExporter for MemoryExporter {
    #[async_instrumented]
    async fn export(&self, spans: Vec<Span>) -> TraceResult<()> {
        self.spans.write().extend(spans);
        Ok(())
    }

    #[async_instrumented]
    async fn shutdown(&self) -> TraceResult<()> {
        Ok(())
    }
}
