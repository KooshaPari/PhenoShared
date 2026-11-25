//! H14.1 — Server-Sent Events (SSE) passthrough for `/v1/chat/completions`.
//!
//! Streams OpenAI-compatible chat completion chunks from the upstream
//! cliproxy++ provider to the downstream client with minimal transformation.
//!
//! Contract:
//! - Upstream emits lines like `data: {"id":"…","object":"chat.completion.chunk",…}`
//! - Sentinel `data: [DONE]` terminates the stream
//! - Empty lines separate SSE events
//! - Comment lines start with `:` and are ignored
//!
//! This module is transport-only. ComboVariant resolution + path construction
//! lives in [`crate::delegate`].

use std::time::Duration;

use bytes::Bytes;
use futures_util::{stream::Stream, StreamExt};
use tokio::io::{AsyncBufReadExt, BufReader};

/// A parsed SSE event from the upstream provider.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SseEvent {
    /// Event payload, sans the `data: ` prefix and trailing newline.
    pub data: String,
    /// Optional `event: <type>` field.
    pub event: Option<String>,
    /// Optional `id: <id>` field for resumability.
    pub id: Option<String>,
}

impl SseEvent {
    /// Sentinel marker emitted by OpenAI-compatible providers to signal
    /// end-of-stream.
    pub const DONE_SENTINEL: &'static str = "[DONE]";

    /// True if this event is the OpenAI end-of-stream sentinel.
    pub fn is_done(&self) -> bool {
        self.data.trim() == Self::DONE_SENTINEL
    }

    /// Render this event back into a wire-format SSE frame.
    pub fn render(&self) -> String {
        let mut out = String::with_capacity(self.data.len() + 32);
        if let Some(event) = &self.event {
            out.push_str("event: ");
            out.push_str(event);
            out.push_str("\n");
        }
        if let Some(id) = &self.id {
            out.push_str("id: ");
            out.push_str(id);
            out.push_str("\n");
        }
        out.push_str("data: ");
        out.push_str(&self.data);
        out.push_str("\n\n");
        out
    }
}

/// Parse a single SSE event from a multi-line `data: …` block.
///
/// Per the SSE spec, multiple `data:` lines within one event are joined
/// with `\n`. We collapse them into a single string.
fn parse_event_block(lines: &[String]) -> Option<SseEvent> {
    if lines.is_empty() {
        return None;
    }
    let mut data_parts: Vec<&str> = Vec::new();
    let mut event: Option<String> = None;
    let mut id: Option<String> = None;
    for raw in lines {
        let line = raw.trim_end_matches('\r');
        if line.is_empty() {
            continue;
        }
        if let Some(rest) = line.strip_prefix(':') {
            // Comment line — ignored.
            let _ = rest;
            continue;
        }
        if let Some(rest) = line.strip_prefix("data:") {
            let value = rest.strip_prefix(' ').unwrap_or(rest);
            data_parts.push(value);
        } else if let Some(rest) = line.strip_prefix("event:") {
            event = Some(rest.trim().to_string());
        } else if let Some(rest) = line.strip_prefix("id:") {
            id = Some(rest.trim().to_string());
        }
        // Other fields (retry:, etc.) are ignored for H14.1 scope.
    }
    if data_parts.is_empty() && event.is_none() && id.is_none() {
        return None;
    }
    let data = data_parts.join("\n");
    Some(SseEvent { data, event, id })
}

/// Adapter that wraps a byte stream (e.g. from `reqwest::Response::bytes_stream`)
/// and yields parsed [`SseEvent`]s.
pub fn sse_stream<S>(byte_stream: S) -> impl Stream<Item = Result<SseEvent, std::io::Error>>
where
    S: Stream<Item = Result<Bytes, reqwest::Error>> + Unpin,
{
    async_stream::stream! {
        let mut buf_lines: Vec<String> = Vec::new();
        let reader = BufReader::new(ByteStreamAdapter(byte_stream));
        let mut lines = reader.lines();
        while let Some(line) = lines.next_line().await.transpose() {
            match line {
                Ok(l) => {
                    if l.is_empty() {
                        // Event boundary — flush.
                        if let Some(ev) = parse_event_block(&buf_lines) {
                            yield Ok(ev);
                        }
                        buf_lines.clear();
                    } else {
                        buf_lines.push(l);
                    }
                }
                Err(e) => {
                    yield Err(e);
                    return;
                }
            }
        }
        // Trailing event without final blank line.
        if let Some(ev) = parse_event_block(&buf_lines) {
            yield Ok(ev);
        }
    }
}

/// Bridge `Stream<Item = Result<Bytes, reqwest::Error>>` into
/// `tokio::io::AsyncRead` for `BufReader`.
struct ByteStreamAdapter<S>(S);

impl<S> tokio::io::AsyncRead for ByteStreamAdapter<S>
where
    S: Stream<Item = Result<Bytes, reqwest::Error>> + Unpin,
{
    fn poll_read(
        mut self: std::pin::Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
        buf: &mut tokio::io::ReadBuf<'_>,
    ) -> std::task::Poll<std::io::Result<()>> {
        match std::pin::Pin::new(&mut self.0).poll_next(cx) {
            std::task::Poll::Ready(Some(Ok(bytes))) => {
                let len = bytes.len().min(buf.remaining());
                buf.put_slice(&bytes[..len]);
                std::task::Poll::Ready(Ok(()))
            }
            std::task::Poll::Ready(Some(Err(e))) => {
                std::task::Poll::Ready(Err(std::io::Error::other(e.to_string())))
            }
            std::task::Poll::Ready(None) => std::task::Poll::Ready(Ok(())),
            std::task::Poll::Pending => std::task::Poll::Pending,
        }
    }
}

/// Per-event timeout for upstream SSE providers that stall.
pub const DEFAULT_SSE_IDLE_TIMEOUT: Duration = Duration::from_secs(60);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_simple_data_line() {
        let lines = vec!["data: {\"id\":\"x\"}".to_string()];
        let ev = parse_event_block(&lines).expect("event");
        assert_eq!(ev.data, "{\"id\":\"x\"}");
        assert!(ev.event.is_none());
    }

    #[test]
    fn parse_done_sentinel() {
        let lines = vec!["data: [DONE]".to_string()];
        let ev = parse_event_block(&lines).expect("event");
        assert!(ev.is_done());
    }

    #[test]
    fn parse_multiline_data_joins_with_newline() {
        let lines = vec!["data: line1".to_string(), "data: line2".to_string()];
        let ev = parse_event_block(&lines).expect("event");
        assert_eq!(ev.data, "line1\nline2");
    }

    #[test]
    fn parse_ignores_comment_lines() {
        let lines = vec![
            ": this is a comment".to_string(),
            "data: payload".to_string(),
        ];
        let ev = parse_event_block(&lines).expect("event");
        assert_eq!(ev.data, "payload");
    }

    #[test]
    fn parse_event_with_type_and_id() {
        let lines = vec![
            "event: message".to_string(),
            "id: 42".to_string(),
            "data: hello".to_string(),
        ];
        let ev = parse_event_block(&lines).expect("event");
        assert_eq!(ev.event.as_deref(), Some("message"));
        assert_eq!(ev.id.as_deref(), Some("42"));
        assert_eq!(ev.data, "hello");
    }

    #[test]
    fn parse_empty_block_returns_none() {
        let lines: Vec<String> = vec![];
        assert!(parse_event_block(&lines).is_none());
    }

    #[test]
    fn render_roundtrips() {
        let ev = SseEvent {
            data: "{\"x\":1}".to_string(),
            event: Some("message".to_string()),
            id: Some("7".to_string()),
        };
        let rendered = ev.render();
        assert!(rendered.starts_with("event: message\n"));
        assert!(rendered.contains("id: 7\n"));
        assert!(rendered.contains("data: {\"x\":1}\n\n"));
    }

    #[test]
    fn done_sentinel_constant() {
        assert_eq!(SseEvent::DONE_SENTINEL, "[DONE]");
    }
}
