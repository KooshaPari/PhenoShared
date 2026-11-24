//! # Phenotype Observability
//!
//! Standardized header types and telemetry structures for the Phenotype ecosystem.
//!
//! This crate provides canonical implementations for cross-cutting observability concerns:
//! - Request/Response headers (tracing, cost, latency)
//! - Telemetry events (request lifecycle, provider failover)
//! - Header builders and extractors
//!
//! ## Header Types
//!
//! - `EventId` - Unique request identifier for distributed tracing
//! - `RequestId` - Correlation ID for request aggregation
//! - `ResponseCost` - Cost tracking in USD millionths
//! - `TimeToFirstToken` - Latency metric in milliseconds
//! - `FallbackStep` - Provider selection in failover chains
//!
//! ## Telemetry Events
//!
//! - `RequestStarted` - Logged when a request initiates
//! - `ResponseReceived` - Logged when a response completes
//! - `ProviderFallback` - Logged during failover transitions
//!
//! ## Example
//!
//! ```ignore
//! use phenotype_observability::headers::{EventId, RequestId};
//! use phenotype_observability::telemetry::TelemetryEvent;
//!
//! // Create headers
//! let event_id = EventId::new();
//! let request_id = RequestId::new();
//!
//! // Emit telemetry
//! let event = TelemetryEvent::request_started(
//!     request_id.clone(),
//!     "gpt-4".to_string(),
//!     150,
//! );
//! ```

pub mod error;
pub mod headers;
pub mod telemetry;

pub use error::{ObservabilityError, Result};
pub use headers::{
    EventId, FallbackStep, HeaderBuilder, RequestId, ResponseCost, TimeToFirstToken,
};
pub use telemetry::{
    ProviderFallbackEvent, RequestStartedEvent, ResponseReceivedEvent, TelemetryEvent,
};

#[cfg(test)]
mod tests;
