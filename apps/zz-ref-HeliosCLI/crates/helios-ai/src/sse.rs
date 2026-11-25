//! Server-Sent Events parsing for streaming responses.

use super::types::StreamChunk;

/// An event parsed from an SSE line.
#[derive(Debug)]
pub enum SseEvent {
    /// A content token from the stream.
    Token(String),
    /// The stream has ended.
    Done,
}

/// Parse a single SSE line into an [`SseEvent`].
///
/// SSE format from OpenAI-compatible APIs:
/// - `data: {"choices":[{"delta":{"content":"..."}}]}` -> Token
/// - `data: [DONE]` -> Done
/// - Anything else -> None
pub fn parse_sse_line(line: &str) -> Option<SseEvent> {
    let line = line.trim();

    if line.is_empty() {
        return None;
    }

    let data = line.strip_prefix("data: ")?;

    if data == "[DONE]" {
        return Some(SseEvent::Done);
    }

    let chunk: StreamChunk = serde_json::from_str(data).ok()?;
    let delta_content =
        chunk.choices.first().and_then(|c| c.delta.as_ref()).and_then(|d| d.content.clone())?;

    if delta_content.is_empty() {
        return None;
    }

    Some(SseEvent::Token(delta_content))
}
