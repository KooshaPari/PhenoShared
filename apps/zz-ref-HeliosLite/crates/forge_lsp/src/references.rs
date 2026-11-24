//! `ReferencesProvider` and `TypeDefinitionProvider` — two related
//! LSP handlers that both return `Location[]`:
//!
//!   * `textDocument/references` — all usages of the symbol under the
//!     cursor (declaration + read sites, optional via `includeDeclaration`).
//!   * `textDocument/typeDefinition` — where the *type* of the symbol
//!     under the cursor is defined (e.g. jump from a variable to its
//!     `struct`/`interface`/`type alias` definition).
//!
//! Both are routed through the same JSON-RPC plumbing, so they share
//! parsing helpers and the same `Location` shape (re-exported from
//! [`crate::definition`]).
//!
//! [`Location`]: crate::definition::Location

use std::path::Path;

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use crate::definition::Location;
use crate::lsp_client::{
    LspClient, LspRequest, Position, Range, TextDocumentIdentifier, TextDocumentPositionParams,
};

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// Options for [`ReferencesProvider::references`].
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub struct ReferencesOptions {
    /// Whether to include the declaration site in the returned list.
    /// Most editors default to `true`; the LSP spec leaves this to
    /// the client.
    pub include_declaration: bool,
}

impl Default for ReferencesOptions {
    fn default() -> Self {
        Self { include_declaration: true }
    }
}

/// Errors that `ReferencesProvider::references` and
/// `TypeDefinitionProvider::type_definition` can surface.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReferencesError {
    /// The LSP server returned an error response.
    ServerError(String),
    /// The LSP server returned a non-Location payload.
    InvalidResponse(String),
}

impl std::fmt::Display for ReferencesError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ReferencesError::ServerError(m) => write!(f, "lsp server error: {m}"),
            ReferencesError::InvalidResponse(m) => {
                write!(f, "invalid references response: {m}")
            }
        }
    }
}

impl std::error::Error for ReferencesError {}

pub type ReferencesResult = Result<Vec<Location>, ReferencesError>;

/// LSP `ReferencesParams` — adds `context` (includeDeclaration) on top
/// of `TextDocumentPositionParams`.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct ReferencesParams {
    #[serde(rename = "textDocument")]
    text_document: TextDocumentIdentifier,
    position: Position,
    context: ReferencesContext,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ReferencesContext {
    #[serde(rename = "includeDeclaration")]
    include_declaration: bool,
}

// ---------------------------------------------------------------------------
// ReferencesProvider
// ---------------------------------------------------------------------------

/// Forwards `textDocument/references` to an LSP client.
///
/// Generic over `C: LspClient` (rather than `Box<dyn LspClient>`) so we
/// can share a single concrete client (e.g. `ProcessLspClient` or a
/// test mock) via `Arc` without paying for dynamic dispatch. Matches
/// the convention used by [`crate::hover::HoverProvider`].
pub struct ReferencesProvider<C: LspClient + ?Sized> {
    client: std::sync::Arc<C>,
}

impl<C: LspClient + ?Sized> ReferencesProvider<C> {
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

    /// Run `textDocument/references` for `uri` at `position`.
    pub fn references(
        &self,
        uri: &str,
        position: Position,
        options: ReferencesOptions,
    ) -> ReferencesResult {
        let params = ReferencesParams {
            text_document: TextDocumentIdentifier { uri: uri.to_string() },
            position,
            context: ReferencesContext { include_declaration: options.include_declaration },
        };
        let request = LspRequest::new(
            next_request_id(),
            "textDocument/references",
            serde_json::to_value(&params)
                .map_err(|e| ReferencesError::InvalidResponse(format!("serialize params: {e}")))?,
        );
        let response = self
            .client
            .send(request)
            .map_err(ReferencesError::ServerError)?;
        if let Some(err) = response.error {
            return Err(ReferencesError::ServerError(format!(
                "{} (code {})",
                err.message, err.code
            )));
        }
        match response.result {
            None => Ok(Vec::new()),
            Some(ref raw) if raw.is_null() => Ok(Vec::new()),
            Some(ref raw) => parse_locations(raw),
        }
    }
}

// ---------------------------------------------------------------------------
// TypeDefinitionProvider
// ---------------------------------------------------------------------------

/// Forwards `textDocument/typeDefinition` to an LSP client.
///
/// Generic over `C: LspClient` (rather than `Box<dyn LspClient>`) so
/// we can share a single concrete client via `Arc`. Matches the
/// convention used by [`crate::definition::DefinitionProvider`].
pub struct TypeDefinitionProvider<C: LspClient + ?Sized> {
    client: std::sync::Arc<C>,
}

impl<C: LspClient + ?Sized> TypeDefinitionProvider<C> {
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

    /// Run `textDocument/typeDefinition` for `uri` at `position`.
    pub fn type_definition(&self, uri: &str, position: Position) -> ReferencesResult {
        let params = TextDocumentPositionParams {
            text_document: TextDocumentIdentifier { uri: uri.to_string() },
            position,
        };
        let request = LspRequest::new(
            next_request_id(),
            "textDocument/typeDefinition",
            serde_json::to_value(&params)
                .map_err(|e| ReferencesError::InvalidResponse(format!("serialize params: {e}")))?,
        );
        let response = self
            .client
            .send(request)
            .map_err(ReferencesError::ServerError)?;
        if let Some(err) = response.error {
            return Err(ReferencesError::ServerError(format!(
                "{} (code {})",
                err.message, err.code
            )));
        }
        match response.result {
            None => Ok(Vec::new()),
            Some(ref raw) if raw.is_null() => Ok(Vec::new()),
            Some(ref raw) => parse_locations(raw),
        }
    }
}

// ---------------------------------------------------------------------------
// Parsing — same shape as definition; isolated so we can evolve the two
// independently.
// ---------------------------------------------------------------------------

fn parse_locations(raw: &Value) -> ReferencesResult {
    match raw {
        Value::Null => Ok(Vec::new()),
        Value::Array(_) => {
            let arr = raw
                .as_array()
                .ok_or_else(|| ReferencesError::InvalidResponse("expected array".to_string()))?;
            let mut out = Vec::with_capacity(arr.len());
            for item in arr {
                out.push(parse_single_location(item)?);
            }
            Ok(out)
        }
        Value::Object(_) => {
            if let Some(items) = raw.get("items") {
                let arr = items.as_array().ok_or_else(|| {
                    ReferencesError::InvalidResponse("items not an array".to_string())
                })?;
                let mut out = Vec::with_capacity(arr.len());
                for item in arr {
                    out.push(parse_single_location(item)?);
                }
                return Ok(out);
            }
            Ok(vec![parse_single_location(raw)?])
        }
        _ => Err(ReferencesError::InvalidResponse(format!(
            "unexpected payload kind: {raw}"
        ))),
    }
}

fn parse_single_location(item: &Value) -> Result<Location, ReferencesError> {
    if let Some(uri) = item.get("targetUri").and_then(Value::as_str) {
        let range = item
            .get("targetRange")
            .ok_or_else(|| {
                ReferencesError::InvalidResponse("LocationLink missing 'targetRange'".to_string())
            })
            .and_then(range_from_value)?;
        return Ok(Location { uri: uri.to_string(), range });
    }
    if let (Some(uri), Some(range)) = (item.get("uri").and_then(Value::as_str), item.get("range")) {
        let range = range_from_value(range)?;
        return Ok(Location { uri: uri.to_string(), range });
    }
    Err(ReferencesError::InvalidResponse(format!(
        "object missing 'uri'+'range' or 'targetUri'+'targetRange': {item}"
    )))
}

fn range_from_value(v: &Value) -> Result<Range, ReferencesError> {
    let start = v
        .get("start")
        .ok_or_else(|| ReferencesError::InvalidResponse("range missing 'start'".to_string()))?;
    let end = v
        .get("end")
        .ok_or_else(|| ReferencesError::InvalidResponse("range missing 'end'".to_string()))?;
    Ok(Range {
        start: Position {
            line: start
                .get("line")
                .and_then(Value::as_u64)
                .ok_or_else(|| ReferencesError::InvalidResponse("range.start.line".to_string()))?
                as u32,
            character: start
                .get("character")
                .and_then(Value::as_u64)
                .ok_or_else(|| {
                    ReferencesError::InvalidResponse("range.start.character".to_string())
                })? as u32,
        },
        end: Position {
            line: end
                .get("line")
                .and_then(Value::as_u64)
                .ok_or_else(|| ReferencesError::InvalidResponse("range.end.line".to_string()))?
                as u32,
            character: end
                .get("character")
                .and_then(Value::as_u64)
                .ok_or_else(|| {
                    ReferencesError::InvalidResponse("range.end.character".to_string())
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

    // -----------------------------------------------------------------------
    // references tests
    // -----------------------------------------------------------------------

    #[test]
    fn references_supports_common_languages() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(Value::Null),
        ));
        let p = ReferencesProvider::new(client);
        assert!(p.supports(Path::new("foo.rs")));
        assert!(p.supports(Path::new("foo.ts")));
        assert!(p.supports(Path::new("foo.TS")));
        assert!(p.supports(Path::new("foo.tsx")));
        assert!(p.supports(Path::new("foo.mts")));
        assert!(p.supports(Path::new("foo.cts")));
        assert!(p.supports(Path::new("foo.mjs")));
        assert!(!p.supports(Path::new("foo.py")));
        assert!(!p.supports(Path::new("foo")));
    }

    #[test]
    fn references_default_options_include_declaration() {
        // Sanity: the default option set is include_declaration=true.
        let opts = ReferencesOptions::default();
        assert!(opts.include_declaration);
    }

    #[test]
    fn references_returns_empty_when_server_returns_null() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(Value::Null),
        ));
        let p = ReferencesProvider::new(client);
        let locs = p
            .references(
                "file:///foo.rs",
                Position { line: 0, character: 0 },
                ReferencesOptions::default(),
            )
            .unwrap();
        assert!(locs.is_empty());
    }

    #[test]
    fn references_parses_array_of_locations() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(json!([
                {"uri":"file:///a.rs","range":{"start":{"line":1,"character":0},"end":{"line":1,"character":3}}},
                {"uri":"file:///b.rs","range":{"start":{"line":2,"character":0},"end":{"line":2,"character":3}}},
                {"uri":"file:///c.rs","range":{"start":{"line":3,"character":0},"end":{"line":3,"character":3}}}
            ])),
        ));
        let p = ReferencesProvider::new(client);
        let locs = p
            .references(
                "file:///foo.rs",
                Position { line: 5, character: 2 },
                ReferencesOptions::default(),
            )
            .unwrap();
        assert_eq!(locs.len(), 3);
        assert_eq!(locs.first().map(|x| x.uri.as_str()), Some("file:///a.rs"));
        assert_eq!(locs.get(2).map(|x| x.uri.as_str()), Some("file:///c.rs"));
    }

    #[test]
    fn references_parses_location_link_payload() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(json!([
                {
                    "targetUri": "file:///lib.rs",
                    "targetRange": {
                        "start": {"line": 20, "character": 0},
                        "end":   {"line": 20, "character": 5}
                    },
                    "targetSelectionRange": {
                        "start": {"line": 20, "character": 3},
                        "end":   {"line": 20, "character": 6}
                    }
                }
            ])),
        ));
        let p = ReferencesProvider::new(client);
        let locs = p
            .references(
                "file:///foo.rs",
                Position { line: 0, character: 0 },
                ReferencesOptions::default(),
            )
            .unwrap();
        assert_eq!(locs.len(), 1);
        assert_eq!(locs.first().map(|x| x.uri.as_str()), Some("file:///lib.rs"));
        assert_eq!(locs.first().map(|x| x.range.start.line), Some(20));
    }

    #[test]
    fn references_request_method_is_references() {
        let captured: Arc<Mutex<Vec<LspRequest>>> = Arc::new(Mutex::new(Vec::new()));
        let client = CaptureClient {
            name: "rust-analyzer",
            response: ok_response(Value::Null),
            captured: captured.clone(),
        };
        let p = ReferencesProvider::new(Arc::new(client));
        let _ = p
            .references(
                "file:///x.rs",
                Position { line: 1, character: 2 },
                ReferencesOptions::default(),
            )
            .unwrap();
        let captured = captured.lock().unwrap();
        assert_eq!(captured.len(), 1);
        assert_eq!(
            captured.first().map(|c| c.method),
            Some("textDocument/references")
        );
    }

    #[test]
    fn references_request_passes_include_declaration() {
        let captured: Arc<Mutex<Vec<LspRequest>>> = Arc::new(Mutex::new(Vec::new()));
        let client = CaptureClient {
            name: "rust-analyzer",
            response: ok_response(Value::Null),
            captured: captured.clone(),
        };
        let p = ReferencesProvider::new(Arc::new(client));
        let _ = p
            .references(
                "file:///x.rs",
                Position { line: 1, character: 2 },
                ReferencesOptions { include_declaration: false },
            )
            .unwrap();
        let captured = captured.lock().unwrap();
        assert_eq!(captured.len(), 1);
        let params_str = serde_json::to_string(&captured[0].params).unwrap();
        assert!(
            params_str.contains("\"includeDeclaration\":false"),
            "expected includeDeclaration:false in {params_str}"
        );
    }

    #[test]
    fn references_propagates_server_error() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            err_response(-32601, "method not found"),
        ));
        let p = ReferencesProvider::new(client);
        let r = p.references(
            "file:///foo.rs",
            Position { line: 0, character: 0 },
            ReferencesOptions::default(),
        );
        assert!(matches!(r, Err(ReferencesError::ServerError(_))));
    }

    #[test]
    fn references_surfaces_transport_failure() {
        let client = Arc::new(MockLspClient::failing("rust-analyzer", "io: broken pipe"));
        let p = ReferencesProvider::new(client);
        let r = p.references(
            "file:///foo.rs",
            Position { line: 0, character: 0 },
            ReferencesOptions::default(),
        );
        assert!(matches!(r, Err(ReferencesError::ServerError(m)) if m == "io: broken pipe"));
    }

    #[test]
    fn references_rejects_malformed_payload() {
        let client = Arc::new(MockLspClient::new("rust-analyzer", ok_response(json!(42))));
        let p = ReferencesProvider::new(client);
        let r = p.references(
            "file:///foo.rs",
            Position { line: 0, character: 0 },
            ReferencesOptions::default(),
        );
        assert!(matches!(r, Err(ReferencesError::InvalidResponse(_))));
    }

    // -----------------------------------------------------------------------
    // typeDefinition tests
    // -----------------------------------------------------------------------

    #[test]
    fn type_definition_supports_common_languages() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(Value::Null),
        ));
        let p = TypeDefinitionProvider::new(client);
        assert!(p.supports(Path::new("foo.rs")));
        assert!(p.supports(Path::new("foo.ts")));
        assert!(p.supports(Path::new("foo.tsx")));
        assert!(p.supports(Path::new("foo.mjs")));
        assert!(!p.supports(Path::new("foo.py")));
    }

    #[test]
    fn type_definition_returns_empty_when_server_returns_null() {
        let client = Arc::new(MockLspClient::new("tsserver", ok_response(Value::Null)));
        let p = TypeDefinitionProvider::new(client);
        let locs = p
            .type_definition("file:///foo.ts", Position { line: 0, character: 0 })
            .unwrap();
        assert!(locs.is_empty());
    }

    #[test]
    fn type_definition_parses_single_location() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(json!({
                "uri": "file:///types.rs",
                "range": {
                    "start": {"line": 30, "character": 0},
                    "end":   {"line": 30, "character": 5}
                }
            })),
        ));
        let p = TypeDefinitionProvider::new(client);
        let locs = p
            .type_definition("file:///foo.rs", Position { line: 5, character: 2 })
            .unwrap();
        assert_eq!(locs.len(), 1);
        assert_eq!(
            locs.first().map(|x| x.uri.as_str()),
            Some("file:///types.rs")
        );
        assert_eq!(locs.first().map(|x| x.range.start.line), Some(30));
    }

    #[test]
    fn type_definition_parses_array_of_locations() {
        let client = Arc::new(MockLspClient::new(
            "tsserver",
            ok_response(json!([
                {"uri":"file:///a.ts","range":{"start":{"line":1,"character":0},"end":{"line":1,"character":3}}}
            ])),
        ));
        let p = TypeDefinitionProvider::new(client);
        let locs = p
            .type_definition("file:///foo.ts", Position { line: 0, character: 0 })
            .unwrap();
        assert_eq!(locs.len(), 1);
    }

    #[test]
    fn type_definition_request_method_is_type_definition() {
        let captured: Arc<Mutex<Vec<LspRequest>>> = Arc::new(Mutex::new(Vec::new()));
        let client = CaptureClient {
            name: "rust-analyzer",
            response: ok_response(Value::Null),
            captured: captured.clone(),
        };
        let p = TypeDefinitionProvider::new(Arc::new(client));
        let _ = p
            .type_definition("file:///x.rs", Position { line: 1, character: 2 })
            .unwrap();
        let captured = captured.lock().unwrap();
        assert_eq!(captured.len(), 1);
        assert_eq!(
            captured.first().map(|c| c.method),
            Some("textDocument/typeDefinition")
        );
    }

    #[test]
    fn type_definition_propagates_server_error() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            err_response(-32601, "method not found"),
        ));
        let p = TypeDefinitionProvider::new(client);
        let r = p.type_definition("file:///foo.rs", Position { line: 0, character: 0 });
        assert!(matches!(r, Err(ReferencesError::ServerError(_))));
    }

    #[test]
    fn type_definition_surfaces_transport_failure() {
        let client = Arc::new(MockLspClient::failing("rust-analyzer", "io: closed"));
        let p = TypeDefinitionProvider::new(client);
        let r = p.type_definition("file:///foo.rs", Position { line: 0, character: 0 });
        assert!(matches!(r, Err(ReferencesError::ServerError(m)) if m == "io: closed"));
    }

    #[test]
    fn type_definition_rejects_malformed_payload() {
        let client = Arc::new(MockLspClient::new(
            "rust-analyzer",
            ok_response(json!("a string")),
        ));
        let p = TypeDefinitionProvider::new(client);
        let r = p.type_definition("file:///foo.rs", Position { line: 0, character: 0 });
        assert!(matches!(r, Err(ReferencesError::InvalidResponse(_))));
    }
}
