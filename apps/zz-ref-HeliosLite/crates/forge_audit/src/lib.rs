//! NDJSON audit log with per-call tool events.
//!
//! Records every tool call (start/end/decision) as one JSON object per line.
//! The audit log is the substrate for the interactive tool-call view, the
//! LLM guardian policy's evidence trail, and outbound sinks (Tracera /
//! AgilePlus / ShareCLI).

mod event;
mod sink;
mod store;

pub use event::{AuditEvent, ToolCallDecision, ToolCallEvent, ToolCallPhase};
pub use sink::AuditSink;
pub use store::{AuditStore, MemoryAuditStore, OnDiskAuditStore};

/// A convenience tuple for wiring into the existing hook chain.
pub type AuditHandle = std::sync::Arc<Box<dyn AuditStore + Send + Sync>>;
