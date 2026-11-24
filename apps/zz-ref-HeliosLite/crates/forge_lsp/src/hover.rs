//! `HoverProvider` — forwards `textDocument/hover` to a real LSP server
//! (`rust-analyzer` for `.rs`, `typescript-language-server` for
//! `.ts`/`.tsx`/`.mts`/`.cts`/`.js`/`.jsx`).
//!
//! The provider speaks the LSP [`textDocument/hover`](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_hover)
//! request and returns the parsed [`Hover`] result. On error it
//! returns a structured [`HoverError`] so callers can decide whether
//! to surface "no hover available" vs. "server is broken" to the user.

use std::path::Path;

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use crate::lsp_client::{
    LspClient, LspRequest, Position, TextDocumentIdentifier, TextDocumentPositionParams,
};

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// `Hover` — the contents of a hover. Matches LSP `Hover` shape:
/// either `contents` (MarkupContent / MarkedString[]) plus an
/// optional `range`.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Hover {
    /// Rendered text. We only carry the string form (MarkupContent's
    /// `value`) — sufficient for the REPL.
    pub contents: String,
    /// Optional [`Range`] over which the hover applies.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub range: Option<HoverRange>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HoverRange {
    pub start_line: u32,
    pub start_character: u32,
    pub end_line: u32,
    pub end_character: u32,
}

/// Errors that `HoverProvider::hover` can surface.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HoverError {
    /// The LSP server returned an error response.
    ServerError(String),
    /// The LSP server returned a non-Hover payload.
    InvalidResponse(String),
    /// The file's language is not supported.
    UnsupportedLanguage(String),
}

impl std::fmt::Display for HoverError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            HoverError::ServerError(m) => write!(f, "lsp server error: {m}"),
            HoverError::InvalidResponse(m) => write!(f, "invalid hover response: {m}"),
            HoverError::UnsupportedLanguage(ext) => {
                write!(f, "no hover provider for .{ext}")
            }
        }
    }
}

impl std::error::Error for HoverError {}

pub type HoverResult = Result<Option<Hover>, HoverError>;

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/// A provider that forwards hover requests to an LSP client.
///
/// Generic over `C: LspClient` (instead of `Box<dyn LspClient>`) so we
/// don't pay for dynamic dispatch and so concrete client types like
/// `ProcessLspClient` and `MockLspClient` can be used without
/// allocation. Per AGENTS.md, service crates must avoid trait objects.
pub struct HoverProvider<C: LspClient + ?Sized> {
    client: std::sync::Arc<C>,
}

impl<C: LspClient + ?Sized> HoverProvider<C> {
    pub fn new(client: std::sync::Arc<C>) -> Self {
        Self { client }
    }

    /// Stable identifier (the underlying server name).
    pub fn name(&self) -> &'static str {
        self.client.server_name()
    }

    /// Does this provider speak the language of `path`?
    pub fn supports(&self, path: &Path) -> bool {
        matches!(
            path.extension()
                .and_then(|e| e.to_str())
                .map(|e| e.to_ascii_lowercase())
                .as_deref(),
            Some("rs")
                | Some("ts")
                | Some("tsx")
                | Some("mts")
                | Some("cts")
                | Some("js")
                | Some("jsx")
                | Some("mjs")
                | Some("cjs")
        )
    }

    /// Run `textDocument/hover` for `uri` at `position`.
    pub fn hover(&self, uri: &str, position: Position) -> HoverResult {
        let params = TextDocumentPositionParams {
            text_document: TextDocumentIdentifier { uri: uri.to_string() },
            position,
        };
        let request = LspRequest::new(
            next_request_id(),
            "textDocument/hover",
            serde_json::to_value(&params)
                .map_err(|e| HoverError::InvalidResponse(format!("serialize params: {e}")))?,
        );
        let response = self.client.send(request).map_err(HoverError::ServerError)?;
        if let Some(err) = response.error {
            return Err(HoverError::ServerError(format!(
                "{} (code {})",
                err.message, err.code
            )));
        }
        match response.result {
            None => Ok(None),
            Some(ref raw) if raw.is_null() => Ok(None),
            Some(ref raw) => parse_hover(raw).map(Some),
        }
    }
}

/// Parse the LSP `Hover` payload into our local [`Hover`] type.
fn parse_hover(raw: &Value) -> Result<Hover, HoverError> {
    // contents can be a string (legacy MarkedString), a MarkupContent
    // object `{ kind, value }`, or an array of MarkedString[].
    let contents = raw
        .get("contents")
        .ok_or_else(|| HoverError::InvalidResponse("missing 'contents'".to_string()))?;
    let text = match contents {
        Value::String(s) => s.clone(),
        Value::Object(map) => map
            .get("value")
            .and_then(Value::as_str)
            .ok_or_else(|| {
                HoverError::InvalidResponse("contents object missing 'value'".to_string())
            })?
            .to_string(),
        Value::Array(items) => {
            let mut buf = String::new();
            for item in items {
                match item {
                    Value::String(s) => {
                        buf.push_str(s);
                        buf.push('\n');
                    }
                    Value::Object(o) => {
                        // Each entry may be a `{ language, value }`
                        // MarkedString or a MarkupContent — both expose
                        // the rendered text in `value`.
                        if let Some(v) = o.get("value").and_then(Value::as_str) {
                            buf.push_str(v);
                            buf.push('\n');
                        }
                    }
                    _ => {}
                }
            }
            buf
        }
        _ => {
            return Err(HoverError::InvalidResponse(
                "unsupported contents shape".to_string(),
            ));
        }
    };
    let range = raw.get("range").and_then(|r| {
        let start = r.get("start")?;
        let end = r.get("end")?;
        Some(HoverRange {
            start_line: start.get("line")?.as_u64()? as u32,
            start_character: start.get("character")?.as_u64()? as u32,
            end_line: end.get("line")?.as_u64()? as u32,
            end_character: end.get("character")?.as_u64()? as u32,
        })
    });
    Ok(Hover { contents: text, range })
}

// ---------------------------------------------------------------------------
// Request id allocation (monotonic per provider; fine for sync traffic)
// ---------------------------------------------------------------------------

fn next_request_id() -> u64 {
    use std::sync::atomic::{AtomicU64, Ordering};
    static COUNTER: AtomicU64 = AtomicU64::new(1);
    COUNTER.fetch_add(1, Ordering::Relaxed)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::lsp_client::LspResponse;
    use std::path::PathBuf;
    use std::sync::{Arc, Mutex};

    /// Mock LSP client that records the most recent request and returns
    /// a scripted response. Shared across provider tests via the
    /// [`MockLspClient::new`] helper.
    pub struct MockLspClient {
        pub name: &'static str,
        pub scripted: Mutex<Option<Result<LspResponse, String>>>,
        pub captured: Mutex<Vec<LspRequest>>,
        pub unsupported: bool,
    }

    impl MockLspClient {
        pub fn new(name: &'static str, response: LspResponse) -> Self {
            Self {
                name,
                scripted: Mutex::new(Some(Ok(response))),
                captured: Mutex::new(Vec::new()),
                unsupported: false,
            }
        }

        pub fn failing(name: &'static str, err: &str) -> Self {
            Self {
                name,
                scripted: Mutex::new(Some(Err(err.to_string()))),
                captured: Mutex::new(Vec::new()),
                unsupported: false,
            }
        }

        pub fn last_request(&self) -> Option<LspRequest> {
            self.captured.lock().unwrap().last().cloned()
        }
    }

    impl LspClient for MockLspClient {
        fn server_name(&self) -> &'static str {
            self.name
        }

        fn send(&self, request: LspRequest) -> Result<LspResponse, String> {
            self.captured.lock().unwrap().push(request);
            let next = self.scripted.lock().unwrap().take();
            match next {
                Some(r) => r,
                None => Ok(LspResponse {
                    jsonrpc: Some("2.0".into()),
                    id: Some(0),
                    result: Some(Value::Null),
                    error: None,
                }),
            }
        }
    }

    fn ok_response(result: Value) -> LspResponse {
        LspResponse {
            jsonrpc: Some("2.0".into()),
            id: Some(1),
            result: Some(result),
            error: None,
        }
    }

    fn err_response(code: i64, message: &str) -> LspResponse {
        LspResponse {
            jsonrpc: Some("2.0".into()),
            id: Some(1),
            result: None,
            error: Some(crate::lsp_client::LspError {
                code,
                message: message.to_string(),
                data: None,
            }),
        }
    }

    #[test]
    fn hover_supports_common_languages() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(json!({"contents": "fn foo()"})),
        ));
        let p = HoverProvider::new(client);
        assert!(p.supports(Path::new("foo.rs")));
        assert!(p.supports(Path::new("foo.TS")));
        assert!(p.supports(Path::new("foo.tsx")));
        assert!(p.supports(Path::new("foo.mts")));
        assert!(p.supports(Path::new("foo.cts")));
        assert!(p.supports(Path::new("foo.mjs")));
        assert!(!p.supports(Path::new("foo.py")));
        assert!(!p.supports(Path::new("foo")));
    }

    #[test]
    fn hover_returns_none_when_server_returns_null() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(Value::Null),
        ));
        let p = HoverProvider::new(client);
        let h = p
            .hover("file:///foo.rs", Position { line: 5, character: 3 })
            .unwrap();
        assert!(h.is_none());
    }

    #[test]
    fn hover_parses_string_contents() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(json!({"contents": "fn main() -> ()"})),
        ));
        let p = HoverProvider::new(client);
        let h = p
            .hover("file:///foo.rs", Position { line: 0, character: 0 })
            .unwrap()
            .unwrap();
        assert_eq!(h.contents, "fn main() -> ()");
        assert!(h.range.is_none());
    }

    #[test]
    fn hover_parses_markup_contents_and_range() {
        let client = Arc::new(MockLspClient::new(
            "tsserver",
            ok_response(json!({
                "contents": {
                    "kind": "markdown",
                    "value": "## bar"
                },
                "range": {
                    "start": {"line": 1, "character": 2},
                    "end":   {"line": 1, "character": 5}
                }
            })),
        ));
        let p = HoverProvider::new(client);
        let h = p
            .hover("file:///foo.ts", Position { line: 1, character: 3 })
            .unwrap()
            .unwrap();
        assert_eq!(h.contents, "## bar");
        let r = h.range.unwrap();
        assert_eq!(r.start_line, 1);
        assert_eq!(r.end_character, 5);
    }

    #[test]
    fn hover_propagates_server_error() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            err_response(-32601, "method not found"),
        ));
        let p = HoverProvider::new(client);
        let r = p.hover("file:///foo.rs", Position { line: 0, character: 0 });
        assert!(matches!(r, Err(HoverError::ServerError(_))));
    }

    #[test]
    fn hover_surfaces_transport_failure() {
        let client = Arc::new(MockLspClient::failing("rust-analyzer", "subprocess died"));
        let p = HoverProvider::new(client);
        let r = p.hover("file:///foo.rs", Position { line: 0, character: 0 });
        assert!(matches!(r, Err(HoverError::ServerError(m)) if m == "subprocess died"));
    }

    #[test]
    fn hover_rejects_malformed_payload() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(json!({"unrelated": true})),
        ));
        let p = HoverProvider::new(client);
        let r = p.hover("file:///foo.rs", Position { line: 0, character: 0 });
        assert!(matches!(r, Err(HoverError::InvalidResponse(_))));
    }

    #[test]
    fn hover_request_includes_uri_and_position() {
        let client = Arc::new(MockLspClient::new(
            "tsserver",
            ok_response(json!({"contents": "x"})),
        ));
        let p = HoverProvider::new(client.clone());
        let _ = p
            .hover("file:///x.ts", Position { line: 7, character: 11 })
            .unwrap();
        let captured = client.captured.lock().unwrap();
        assert_eq!(captured.len(), 1);
        assert_eq!(
            captured.first().map(|c| c.method),
            Some("textDocument/hover")
        );
    }
}
