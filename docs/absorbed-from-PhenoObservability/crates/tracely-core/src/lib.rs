//! `tracely-core` — Unified observability for the Phenotype ecosystem.
//!
//! ## SSOT
//!
//! This crate is the **canonical Single Source of Truth** for `tracely-core`.
//! The standalone `KooshaPari/Tracely` repository contains a copy of this crate
//! that will be archived — do not make changes there. Update here instead.
//!
//! Absorbs:
//! - `helix-logging` (structured logging with correlation IDs)
//! - `helix-tracing` (distributed tracing with TraceContext and span management)
//!
//! # Quick start
//!
//! ```rust
//! use tracely_core::{logging, tracing as trc};
//!
//! // Initialize structured logging
//! logging::init(logging::LoggerConfig::default());
//!
//! // Initialize tracing subscriber
//! trc::init_tracing(trc::TracingConfig::default()).ok();
//!
//! // Create a trace context
//! let ctx = trc::TraceContext::new();
//! println!("trace_id={} span_id={}", ctx.trace_id, ctx.span_id);
//! ```

pub mod alerting;
pub mod dashboards;
pub mod file_exporter;
pub mod logging;
pub mod tracing;

// Re-export the most commonly used items at crate root
pub use file_exporter::{FileExporter, SpanData};
pub use logging::{LogContext, LoggerConfig};
pub use tracing::{TraceContext, TracingConfig};
