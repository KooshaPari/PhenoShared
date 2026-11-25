//! Streaming token deltas for REPL rendering.

use serde::{Deserialize, Serialize};

/// The kind of stream content in a delta.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum StreamKind {
    /// Plain markdown/text content.
    Text,
    /// A tool-call was announced (arguments streaming).
    ToolCall,
    /// Model is thinking (not for direct display, e.g. some reasoning models).
    Reasoning,
}

/// A single streamed delta from the model output.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StreamDelta {
    pub kind: StreamKind,
    pub text: String,
}

/// One unit delivered by the stream consumer to the renderer.
///
/// `chunks` are fattened into render events by the sink; the sink exposes
/// callbacks (`on_text`, `on_tool_call`) so the terminal can repaint live.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StreamChunk {
    /// Accumulated delta for this turn.
    pub delta: StreamDelta,
    /// Running token counter (for progress).
    pub total_tokens: usize,
    /// Whether this is the final chunk.
    pub done: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stream_chunk_roundtrip() {
        let c = StreamChunk {
            delta: StreamDelta { kind: StreamKind::Text, text: "hello".into() },
            total_tokens: 5,
            done: false,
        };
        let s = serde_json::to_string(&c).unwrap();
        let back: StreamChunk = serde_json::from_str(&s).unwrap();
        assert_eq!(back, c);
    }

    #[test]
    fn reasoning_not_text() {
        assert_ne!(StreamKind::Reasoning, StreamKind::Text);
    }
}
