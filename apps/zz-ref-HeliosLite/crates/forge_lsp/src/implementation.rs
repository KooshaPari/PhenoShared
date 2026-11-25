//! `ImplementationProvider` — forwards `textDocument/implementation` to a
//! real LSP server (`rust-analyzer`, `typescript-language-server`).
//!
//! Per LSP spec the server returns either `Location[]`,
//! `LocationLink[]`, or `null`. We normalize the first two to
//! `Vec<Location>` (re-using [`crate::definition::Location`]) and treat
//! `null`/missing as an empty list — the common "no implementation
//! found" case.
//!
//! [`Location`]: crate::definition::Location

use std::path::Path;

use serde_json::{Value, json};

use crate::definition::Location;
use crate::lsp_client::{
    LspClient, LspRequest, Position, Range, TextDocumentIdentifier, TextDocumentPositionParams,
};

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// Errors that `ImplementationProvider::implementation` can surface.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ImplementationError {
    /// The LSP server returned an error response.
    ServerError(String),
    /// The LSP server returned a non-Location payload.
    InvalidResponse(String),
}

impl std::fmt::Display for ImplementationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ImplementationError::ServerError(m) => write!(f, "lsp server error: {m}"),
            ImplementationError::InvalidResponse(m) => {
                write!(f, "invalid implementation response: {m}")
            }
        }
    }
}

impl std::error::Error for ImplementationError {}

pub type ImplementationResult = Result<Vec<Location>, ImplementationError>;

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/// Forwards `textDocument/implementation` to an LSP client.
///
/// Generic over `C: LspClient` (rather than `Box<dyn LspClient>`) so we
/// can share a single concrete client (e.g. `ProcessLspClient` or a
/// test mock) via `Arc` without paying for dynamic dispatch. This
/// matches the convention used by [`crate::hover::HoverProvider`] and
/// [`crate::definition::DefinitionProvider`].
pub struct ImplementationProvider<C: LspClient + ?Sized> {
    client: std::sync::Arc<C>,
}

impl<C: LspClient + ?Sized> ImplementationProvider<C> {
    pub fn new(client: std::sync::Arc<C>) -> Self {
        Self { client }
    }

    pub fn name(&self) -> &'static str {
        self.client.server_name()
    }

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

    /// Run `textDocument/implementation` for `uri` at `position`.
    pub fn implementation(&self, uri: &str, position: Position) -> ImplementationResult {
        let params = TextDocumentPositionParams {
            text_document: TextDocumentIdentifier { uri: uri.to_string() },
            position,
        };
        let request = LspRequest::new(
            next_request_id(),
            "textDocument/implementation",
            serde_json::to_value(&params).map_err(|e| {
                ImplementationError::InvalidResponse(format!("serialize params: {e}"))
            })?,
        );
        let response = self
            .client
            .send(request)
            .map_err(ImplementationError::ServerError)?;
        if let Some(err) = response.error {
            return Err(ImplementationError::ServerError(format!(
                "{} (code {})",
                err.message, err.code
            )));
        }
        match response.result {
            None => Ok(Vec::new()),
            Some(ref raw) if raw.is_null() => Ok(Vec::new()),
            Some(ref raw) => parse_implementations(raw),
        }
    }
}

// ---------------------------------------------------------------------------
// Parsing — same shape as definition; isolated so we can evolve the two
// independently.
// ---------------------------------------------------------------------------

fn parse_implementations(raw: &Value) -> ImplementationResult {
    match raw {
        Value::Null => Ok(Vec::new()),
        Value::Array(_) => {
            let arr = raw.as_array().ok_or_else(|| {
                ImplementationError::InvalidResponse("expected array".to_string())
            })?;
            let mut out = Vec::with_capacity(arr.len());
            for item in arr {
                out.push(parse_single_location(item)?);
            }
            Ok(out)
        }
        Value::Object(_) => {
            if let Some(items) = raw.get("items") {
                let arr = items.as_array().ok_or_else(|| {
                    ImplementationError::InvalidResponse("items not an array".to_string())
                })?;
                let mut out = Vec::with_capacity(arr.len());
                for item in arr {
                    out.push(parse_single_location(item)?);
                }
                return Ok(out);
            }
            Ok(vec![parse_single_location(raw)?])
        }
        _ => Err(ImplementationError::InvalidResponse(format!(
            "unexpected payload kind: {raw}"
        ))),
    }
}

fn parse_single_location(item: &Value) -> Result<Location, ImplementationError> {
    if let Some(uri) = item.get("targetUri").and_then(Value::as_str) {
        let range = item
            .get("targetRange")
            .ok_or_else(|| {
                ImplementationError::InvalidResponse(
                    "LocationLink missing 'targetRange'".to_string(),
                )
            })
            .and_then(range_from_value)?;
        return Ok(Location { uri: uri.to_string(), range });
    }
    if let (Some(uri), Some(range)) = (item.get("uri").and_then(Value::as_str), item.get("range")) {
        let range = range_from_value(range)?;
        return Ok(Location { uri: uri.to_string(), range });
    }
    Err(ImplementationError::InvalidResponse(format!(
        "object missing 'uri'+'range' or 'targetUri'+'targetRange': {item}"
    )))
}

fn range_from_value(v: &Value) -> Result<Range, ImplementationError> {
    let start = v
        .get("start")
        .ok_or_else(|| ImplementationError::InvalidResponse("range missing 'start'".to_string()))?;
    let end = v
        .get("end")
        .ok_or_else(|| ImplementationError::InvalidResponse("range missing 'end'".to_string()))?;
    Ok(Range {
        start: Position {
            line: start.get("line").and_then(Value::as_u64).ok_or_else(|| {
                ImplementationError::InvalidResponse("range.start.line".to_string())
            })? as u32,
            character: start
                .get("character")
                .and_then(Value::as_u64)
                .ok_or_else(|| {
                    ImplementationError::InvalidResponse("range.start.character".to_string())
                })? as u32,
        },
        end: Position {
            line: end
                .get("line")
                .and_then(Value::as_u64)
                .ok_or_else(|| ImplementationError::InvalidResponse("range.end.line".to_string()))?
                as u32,
            character: end
                .get("character")
                .and_then(Value::as_u64)
                .ok_or_else(|| {
                    ImplementationError::InvalidResponse("range.end.character".to_string())
                })? as u32,
        },
    })
}

// ---------------------------------------------------------------------------
// Request id allocation (same scheme as hover/definition/completion)
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
    use std::sync::{Arc, Mutex};

    pub struct MockLspClient {
        pub name: &'static str,
        pub scripted: Mutex<Option<Result<LspResponse, String>>>,
        pub captured: Mutex<Vec<LspRequest>>,
    }

    impl MockLspClient {
        pub fn new(name: &'static str, response: LspResponse) -> Self {
            Self {
                name,
                scripted: Mutex::new(Some(Ok(response))),
                captured: Mutex::new(Vec::new()),
            }
        }

        pub fn failing(name: &'static str, err: &str) -> Self {
            Self {
                name,
                scripted: Mutex::new(Some(Err(err.to_string()))),
                captured: Mutex::new(Vec::new()),
            }
        }

        #[allow(dead_code)]
        pub fn last_request(&self) -> Option<LspRequest> {
            self.captured.lock().unwrap().last().cloned()
        }
    }

    impl crate::lsp_client::LspClient for MockLspClient {
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
    fn implementation_supports_common_languages() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(Value::Null),
        ));
        let p = ImplementationProvider::new(client);
        assert!(p.supports(Path::new("foo.rs")));
        assert!(p.supports(Path::new("foo.ts")));
        assert!(p.supports(Path::new("foo.tsx")));
        assert!(p.supports(Path::new("foo.JS")));
        assert!(p.supports(Path::new("foo.mts")));
        assert!(p.supports(Path::new("foo.cts")));
        assert!(!p.supports(Path::new("foo.py")));
        assert!(!p.supports(Path::new("foo")));
    }

    #[test]
    fn implementation_returns_empty_when_server_returns_null() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(Value::Null),
        ));
        let p = ImplementationProvider::new(client);
        let locs = p
            .implementation("file:///foo.rs", Position { line: 0, character: 0 })
            .unwrap();
        assert!(locs.is_empty());
    }

    #[test]
    fn implementation_parses_single_location() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(json!({
                "uri": "file:///impl.rs",
                "range": {
                    "start": {"line": 12, "character": 0},
                    "end":   {"line": 12, "character": 5}
                }
            })),
        ));
        let p = ImplementationProvider::new(client);
        let locs = p
            .implementation("file:///foo.rs", Position { line: 5, character: 2 })
            .unwrap();
        assert_eq!(locs.len(), 1);
        assert_eq!(
            locs.first().map(|x| x.uri.as_str()),
            Some("file:///impl.rs")
        );
        assert_eq!(locs.first().map(|x| x.range.start.line), Some(12));
        assert_eq!(locs.first().map(|x| x.range.end.character), Some(5));
    }

    #[test]
    fn implementation_parses_array_of_locations() {
        let client = Arc::new(MockLspClient::new(
            "tsserver",
            ok_response(json!([
                {"uri":"file:///a.ts","range":{"start":{"line":1,"character":0},"end":{"line":1,"character":3}}},
                {"uri":"file:///b.ts","range":{"start":{"line":2,"character":0},"end":{"line":2,"character":3}}}
            ])),
        ));
        let p = ImplementationProvider::new(client);
        let locs = p
            .implementation("file:///iface.ts", Position { line: 9, character: 0 })
            .unwrap();
        assert_eq!(locs.len(), 2);
        assert_eq!(locs.first().map(|x| x.uri.as_str()), Some("file:///a.ts"));
        assert_eq!(locs.get(1).map(|x| x.uri.as_str()), Some("file:///b.ts"));
    }

    #[test]
    fn implementation_parses_location_link_payload() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(json!([
                {
                    "targetUri": "file:///impl.rs",
                    "targetRange": {
                        "start": {"line": 10, "character": 0},
                        "end":   {"line": 10, "character": 8}
                    },
                    "targetSelectionRange": {
                        "start": {"line": 10, "character": 3},
                        "end":   {"line": 10, "character": 6}
                    }
                }
            ])),
        ));
        let p = ImplementationProvider::new(client);
        let locs = p
            .implementation("file:///trait.rs", Position { line: 5, character: 5 })
            .unwrap();
        assert_eq!(locs.len(), 1);
        assert_eq!(
            locs.first().map(|x| x.uri.as_str()),
            Some("file:///impl.rs")
        );
        assert_eq!(locs.first().map(|x| x.range.start.line), Some(10));
        assert_eq!(locs.first().map(|x| x.range.end.character), Some(8));
    }

    #[test]
    fn implementation_parses_envelope_with_items() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(json!({"items": [
                {"uri":"file:///x.rs","range":{"start":{"line":1,"character":0},"end":{"line":1,"character":1}}}
            ]})),
        ));
        let p = ImplementationProvider::new(client);
        let locs = p
            .implementation("file:///foo.rs", Position { line: 0, character: 0 })
            .unwrap();
        assert_eq!(locs.len(), 1);
        assert_eq!(locs.first().map(|x| x.uri.as_str()), Some("file:///x.rs"));
    }

    #[test]
    fn implementation_propagates_server_error() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            err_response(-32601, "method not found"),
        ));
        let p = ImplementationProvider::new(client);
        let r = p.implementation("file:///foo.rs", Position { line: 0, character: 0 });
        assert!(matches!(r, Err(ImplementationError::ServerError(_))));
    }

    #[test]
    fn implementation_surfaces_transport_failure() {
        let client = Arc::new(MockLspClient::failing("rust-analyzer", "io: broken pipe"));
        let p = ImplementationProvider::new(client);
        let r = p.implementation("file:///foo.rs", Position { line: 0, character: 0 });
        assert!(matches!(r, Err(ImplementationError::ServerError(m)) if m == "io: broken pipe"));
    }

    #[test]
    fn implementation_rejects_malformed_payload() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(json!("just a string")),
        ));
        let p = ImplementationProvider::new(client);
        let r = p.implementation("file:///foo.rs", Position { line: 0, character: 0 });
        assert!(matches!(r, Err(ImplementationError::InvalidResponse(_))));
    }

    #[test]
    fn implementation_request_includes_method_and_uri() {
        // Capture via Arc so we can read the captured requests after
        // the provider (which owns the only strong `Arc<MockLspClient>`)
        // drops.
        let captured: Arc<Mutex<Vec<LspRequest>>> = Arc::new(Mutex::new(Vec::new()));
        let client = CaptureClient {
            name: "rust-analyzer",
            response: ok_response(Value::Null),
            captured: captured.clone(),
        };
        let p = ImplementationProvider::new(Arc::new(client));
        let _ = p
            .implementation("file:///x.rs", Position { line: 1, character: 2 })
            .unwrap();
        let captured = captured.lock().unwrap();
        assert_eq!(captured.len(), 1);
        assert_eq!(
            captured.first().map(|c| c.method),
            Some("textDocument/implementation")
        );
    }

    /// LspClient wrapper that funnels every captured request through a
    /// shared `Arc<Mutex<Vec<_>>>` so the test can read requests even
    /// after the owning `Box<dyn LspClient>` is dropped.
    struct CaptureClient {
        name: &'static str,
        response: LspResponse,
        captured: Arc<Mutex<Vec<LspRequest>>>,
    }
    impl crate::lsp_client::LspClient for CaptureClient {
        fn server_name(&self) -> &'static str {
            self.name
        }
        fn send(&self, request: LspRequest) -> Result<LspResponse, String> {
            self.captured.lock().unwrap().push(request);
            Ok(self.response.clone())
        }
    }
}
