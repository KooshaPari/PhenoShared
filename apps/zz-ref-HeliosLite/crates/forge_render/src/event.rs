//! Rendering events for the interactive tool-call view + audit feeding.

use serde::{Deserialize, Serialize};

/// The lifecycle phase of a tool call / agent block on screen.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RenderPhase {
    /// The block has just been created (folded by default).
    Created,
    /// The tool is executing (expanded, streaming).
    Running,
    /// The tool finished (expanded, showing final output).
    Completed,
}

/// Settled disposition of a block.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RenderStatus {
    /// Finished cleanly.
    Ok,
    /// Finished with an error.
    Failed,
    /// Cancelled / interrupted.
    Interrupted,
    /// Still in flight.
    Pending,
}

/// A single tool-call block on the render surface.
///
/// Each block corresponds to one tool execution. It carries just enough
/// metadata to render a folded summary and, when expanded, a live stream.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RenderBlock {
    /// Stable id for the block (matches the tool call id when available).
    pub id: String,
    /// Tool name, e.g. `write`, `shell`, `task`.
    pub tool: String,
    /// Short human summary of the arguments (never the full payload).
    pub summary: String,
    /// Dropdown depth for tree layout of nested subagent blocks.
    pub depth: usize,
    /// Current lifecycle phase.
    pub phase: RenderPhase,
    /// Current settled status.
    pub status: RenderStatus,
    /// Whether the block content is loaded only when expanded (lazy).
    pub lazy: bool,
    /// Raw argument JSON, encoded for on-demand expansion display.
    pub args_json: Option<String>,
}

impl RenderBlock {
    pub fn header(&self) -> String {
        let glyph = match self.status {
            RenderStatus::Pending => "\u{25cf}",
            RenderStatus::Ok => "\u{2713}",
            RenderStatus::Failed => "\u{2717}",
            RenderStatus::Interrupted => "\u{2013}",
        };
        format!("{glyph} {}\u{a0}\u{a0}{}", self.tool, self.summary)
    }
}

/// A rendered event, serializable to NDJSON for `forge_audit` / sink feeds.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum RenderEvent {
    /// A tool block was created on screen.
    BlockCreated(RenderBlock),
    /// A tool block transitioned phase (e.g. running -> completed).
    BlockTransition {
        id: String,
        to: RenderPhase,
        status: RenderStatus,
    },
    /// Streaming text/markdown content for the model reply.
    StreamText { id: String, text: String },
    /// Appended stdout/stderr for an expanded tool-call block.
    StreamOutput {
        id: String,
        channel: OutputChannel,
        data: String,
    },
    /// The tool call produced a final structured result.
    BlockResult {
        id: String,
        truncated: bool,
        chars: usize,
    },
}

/// Which output channel a streamed chunk belongs to.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OutputChannel {
    Stdout,
    Stderr,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn block_header_shows_check_for_ok() {
        let b = RenderBlock {
            id: "b1".into(),
            tool: "write".into(),
            summary: "src/main.rs".into(),
            depth: 0,
            phase: RenderPhase::Completed,
            status: RenderStatus::Ok,
            lazy: true,
            args_json: None,
        };
        let h = b.header();
        assert!(h.contains("write"), "header = {h:?}");
        assert!(h.contains('\u{2713}'), "ok check glyph missing: {h:?}");
    }

    #[test]
    fn render_event_roundtrip_via_json() {
        let e = RenderEvent::StreamText { id: "turn-1".into(), text: "refactoring…".into() };
        let s = serde_json::to_string(&e).unwrap();
        let back: RenderEvent = serde_json::from_str(&s).unwrap();
        assert_eq!(back, e);
    }

    #[test]
    fn render_event_ndjson_line_has_no_newline() {
        let e = RenderEvent::StreamOutput {
            id: "t1".into(),
            channel: OutputChannel::Stderr,
            data: "panic".into(),
        };
        let s = serde_json::to_string(&e).unwrap();
        assert!(!s.contains('\n'));
    }
}
