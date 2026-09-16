//! JSON-RPC 2.0 over a local Unix domain socket.
//!
//! This is the multi-process IPC layer for `phinbox`. The daemon binds a
//! socket under the inbox root; clients (Swift app, CLI, other agents) connect,
//! write one JSON-RPC request per line, and read responses line-by-line.
//!
//! Framing: every message is a single JSON object terminated by `\n`. No
//! `Content-Length` headers, no SSE, no websockets -- line-delimited JSON-RPC,
//! which is exactly what stdio LSP-style clients also use (we just swap stdio
//! for a UDS).
//!
//! Methods:
//! - `daemon.ping`               -> `Pong { now_ms, version }`
//! - `daemon.shutdown`           -> `{ ok: true }`, then daemon stops
//! - `inbox.list`                -> `{ requests: [PendingRequest] }`
//! - `inbox.get`     (`rid`)     -> `{ request: PendingRequest }` or not-found
//! - `inbox.answer`   (`rid`, `response`) -> `{ request: PendingRequest }` after finalization
//! - `inbox.cancel`   (`rid`)    -> `{ request: PendingRequest }` (writes Cancelled response)
//! - `inbox.subscribe`           -> server-streaming: emits `{ kind: "added|answered|removed", request? }`

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tokio::sync::{broadcast, Notify};
use tokio::net::UnixListener;

use crate::inbox::{self, PendingRequest, ResponseStatus};

mod client;
mod server;

pub use client::Client;
pub use server::{bind_listener, spawn_accept};

// ---------------------------------------------------------------------------
// Socket path
// ---------------------------------------------------------------------------

/// Returns the canonical IPC socket path for a given inbox root.
#[must_use]
pub fn ipc_socket_path(root: &Path) -> PathBuf {
    root.join("ipc.sock")
}

/// Best-effort: read the lockfile in `root` and return the IPC socket path.
/// Returns `None` if the lockfile is missing, malformed, or `ipc_sock` is empty
/// (older daemons predating IPC).
#[must_use]
pub fn live_socket(root: &Path) -> Option<PathBuf> {
    let payload = crate::inbox::daemon::lockfile::read_lockfile(root)?;
    let sock = payload.ipc_sock?;
    if sock.as_os_str().is_empty() {
        return None;
    }
    Some(sock)
}

// ---------------------------------------------------------------------------
// JSON-RPC envelope
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Request {
    pub jsonrpc: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub id: Option<Value>,
    pub method: String,
    #[serde(default)]
    pub params: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Response {
    pub jsonrpc: String,
    pub id: Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<RpcError>,
}

impl Response {
    fn ok(id: Value, result: Value) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            id,
            result: Some(result),
            error: None,
        }
    }

    fn err(id: Value, code: i32, message: impl Into<String>) -> Self {
        Self {
            jsonrpc: "2.0".into(),
            id,
            result: None,
            error: Some(RpcError {
                code,
                message: message.into(),
                data: None,
            }),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RpcError {
    pub code: i32,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
}

// JSON-RPC 2.0 standard error codes (negative = protocol, positive = app).
pub const ERR_PARSE: i32 = -32700;
pub const ERR_INVALID_REQUEST: i32 = -32600;
pub const ERR_METHOD_NOT_FOUND: i32 = -32601;
pub const ERR_INVALID_PARAMS: i32 = -32602;
pub const ERR_INTERNAL: i32 = -32603;

// App-level error codes (1xxx range).
pub const ERR_NOT_FOUND: i32 = 1001;
pub const ERR_BAD_STATE: i32 = 1002;
pub const ERR_IO: i32 = 1003;

// ---------------------------------------------------------------------------
// Server state (shared with the daemon)
// ---------------------------------------------------------------------------

/// Shared state the IPC server needs.
///
/// Cheap to clone: every field is either a path/Arc or already inside a Mutex.
#[derive(Clone)]
pub struct RpcState {
    pub root: PathBuf,
    pub sock_path: PathBuf,
    pub started_ms: i64,
    pub shutdown: Arc<Notify>,
    pub changes: broadcast::Sender<ChangeEvent>,
    pub listener_slot: Arc<Mutex<Option<UnixListener>>>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum ChangeEvent {
    Added { request: PendingRequest },
    Answered { rid: String, status: ResponseStatus },
    Removed { rid: String },
}

impl RpcState {
    pub fn new(root: PathBuf, sock_path: PathBuf) -> Self {
        let (tx, _rx) = broadcast::channel(64);
        Self {
            root,
            sock_path,
            started_ms: inbox::unix_now_ms() as i64,
            shutdown: Arc::new(Notify::new()),
            changes: tx,
            listener_slot: Arc::new(Mutex::new(None)),
        }
    }

    pub fn notify_added(&self, req: &PendingRequest) {
        let _ = self.changes.send(ChangeEvent::Added { request: req.clone() });
    }

    pub fn notify_answered(&self, rid: &str, status: ResponseStatus) {
        let _ = self.changes.send(ChangeEvent::Answered {
            rid: rid.to_string(),
            status,
        });
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn monotonic_id() -> u64 {
    use std::sync::atomic::{AtomicU64, Ordering};
    static CTR: AtomicU64 = AtomicU64::new(1);
    CTR.fetch_add(1, Ordering::Relaxed)
}

/// Serialize a `RpcState`'s key facts for inclusion in the lockfile.
#[must_use]
pub fn state_summary(state: &RpcState) -> HashMap<&'static str, String> {
    let mut m = HashMap::new();
    m.insert("sock_path", state.sock_path.to_string_lossy().to_string());
    m.insert("started_ms", state.started_ms.to_string());
    m
}
