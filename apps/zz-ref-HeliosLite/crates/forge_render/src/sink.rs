//! `RenderSink` — an optional-targeting, event-streaming renderer.
//!
//! The sink accepts high-level render events and **either**:
//! - pushes NDJSON lines into a `channel::Sender<String>` for a live terminal /
//!   file / external sink (Tracera / ShareCLI later), **or**
//! - drops them when no target is attached (default no-op, zero overhead).
//!
//! This keeps rendering cheap in headless/CI mode while enabling interactive
//! views when a terminal is present.

use std::sync::mpsc::Sender;

use super::event::RenderEvent;
use super::{RenderError, ser_err};

/// A stream target for NDJSON render events.
#[derive(Debug, Clone)]
pub struct StreamTarget {
    tx: Sender<String>,
}

impl StreamTarget {
    pub fn new(tx: Sender<String>) -> Self {
        Self { tx }
    }

    /// Serialize and push one event line to the target.
    pub fn emit(&self, event: &RenderEvent) -> Result<(), RenderError> {
        let line = serde_json::to_string(event).map_err(ser_err)?;
        self.tx.send(line).map_err(|_| RenderError::ChannelClosed)
    }
}

/// The render sink — the single point where lifecycle events become pixels.
///
/// It holds an optional [`StreamTarget`]. When absent, all methods are cheap
/// no-ops, so attaching a renderer is a pure opt-in.
#[derive(Debug, Clone, Default)]
pub struct RenderSink {
    target: Option<StreamTarget>,
}

impl RenderSink {
    /// Create a sink with no target (no-op mode).
    pub fn null() -> Self {
        Self { target: None }
    }

    /// Create a sink that streams NDJSON lines to `tx`.
    pub fn to_target(tx: Sender<String>) -> Self {
        Self { target: Some(StreamTarget::new(tx)) }
    }

    /// Whether a terminal target is attached.
    pub fn is_attached(&self) -> bool {
        self.target.is_some()
    }

    /// Emit a lifecycle event (no-op when detached).
    pub fn emit(&self, event: RenderEvent) -> Result<(), RenderError> {
        if let Some(t) = &self.target {
            t.emit(&event)?;
        }
        Ok(())
    }

    /// Begin a new tool-call block.
    pub fn block_created(&self, block: super::event::RenderBlock) -> Result<(), RenderError> {
        self.emit(RenderEvent::BlockCreated(block))
    }

    /// Stream text for the model reply.
    pub fn stream_text(&self, id: &str, text: &str) -> Result<(), RenderError> {
        self.emit(RenderEvent::StreamText { id: id.to_string(), text: text.to_string() })
    }
}

#[cfg(test)]
mod tests {
    use std::sync::mpsc;

    use super::*;
    use crate::event::{RenderBlock, RenderPhase, RenderStatus};

    #[test]
    fn null_sink_is_detached_and_silent() {
        let s = RenderSink::null();
        assert!(!s.is_attached());
        // Should not error.
        s.stream_text("id", "hello").unwrap();
    }

    #[test]
    fn attached_sink_streams_ndjson_recoverable() {
        let (tx, rx) = mpsc::channel();
        let sink = RenderSink::to_target(tx);
        assert!(sink.is_attached());
        sink.stream_text("t1", "refactor").unwrap();
        let line = rx.recv_timeout(std::time::Duration::from_secs(1)).unwrap();
        let ev: RenderEvent = serde_json::from_str(&line).unwrap();
        match ev {
            RenderEvent::StreamText { id, text } => {
                assert_eq!(id, "t1");
                assert_eq!(text, "refactor");
            }
            other => panic!("unexpected event: {other:?}"),
        }
    }

    #[test]
    fn block_created_emits_event() {
        let (tx, rx) = mpsc::channel();
        let sink = RenderSink::to_target(tx);
        let b = RenderBlock {
            id: "b1".into(),
            tool: "shell".into(),
            summary: "cargo test".into(),
            depth: 0,
            phase: RenderPhase::Created,
            status: RenderStatus::Pending,
            lazy: true,
            args_json: None,
        };
        sink.block_created(b).unwrap();
        let line = rx.recv_timeout(std::time::Duration::from_secs(1)).unwrap();
        assert!(line.contains("BlockCreated"));
    }
}
