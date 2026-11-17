//! `forge_render` — **streaming output + interactive tool-call rendering**.
//!
//! This crate gives helioslite a first-class, interactive view of the agent's
//! work:
//!
//! - **Streaming tokens** — the REPL can render partial model output as it
//!   arrives (`StreamChunk`) rather than waiting for the full turn.
//! - **Interactive tool-call blocks** — each tool invocation renders as a
//!   collapsible / expandable block with:
//!   - a folded one-line summary (`name`, short args)
//!   - an expanded view streaming stdout/stderr in near-real-time
//!   - a per-call status (`Running`, `Ok`, `Failed`, `Interrupted`)
//! - **NDJSON-friendly render events** — a fire-and-forget stream of render
//!   events that tooling (and `forge_audit` / Tracera sinks) can subscribe to.
//!
//! ## Design
//!
//! Rendering is deliberately **orthogonal** to tool execution. Tools stay pure;
//! the renderer observes lifecycle events via `RenderSink` and decides how to
//! paint them. This mirrors the existing hook pattern in `forge_app` and keeps
//! the tool layer free of ANSI / terminal concerns.

pub mod event;
pub mod sink;
pub mod stream;

pub use event::{RenderBlock, RenderEvent, RenderPhase, RenderStatus};
pub use sink::RenderSink;
pub use stream::{StreamChunk, StreamDelta, StreamKind};

use thiserror::Error;

/// Errors produced by the render pipeline.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum RenderError {
    /// A render event payload failed to serialize as a UTF-8 line.
    #[error("render event serialization failed: {0}")]
    Serialize(String),
    /// The supplied event was malformed (e.g. missing required fields).
    #[error("malformed render event: {0}")]
    Malformed(String),
    /// Channel closed before the event could be flushed.
    #[error("render channel closed")]
    ChannelClosed,
}

/// Cheap helper to turn a serde error into a [`RenderError`].
pub fn ser_err(e: impl std::fmt::Display) -> RenderError {
    RenderError::Serialize(e.to_string())
}
