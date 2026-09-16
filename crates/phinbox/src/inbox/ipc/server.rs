//! Async JSON-RPC server over Unix domain socket.

use std::path::Path;
use std::time::Duration;

use serde::Deserialize;
use serde_json::{json, Value};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::{UnixListener, UnixStream};
use tokio::sync::broadcast;
use tokio::task::JoinHandle;

use crate::error::ElicitError;
use crate::inbox::{
    self, list_pending, load_pending, PendingRequest, RequestState,
    ResponseStatus, PHINBOX_VERSION,
};
use crate::spec::ElicitResponse;

use super::{RpcState, Response};

// ---------------------------------------------------------------------------
// Server lifecycle
// ---------------------------------------------------------------------------

/// Bind a Unix listener at `sock_path`, replace any stale socket file.
pub async fn bind_listener(sock_path: &Path) -> Result<UnixListener, ElicitError> {
    if let Some(parent) = sock_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if sock_path.exists() {
        let _ = std::fs::remove_file(sock_path);
    }
    let listener = UnixListener::bind(sock_path).map_err(|e| {
        ElicitError::Io(std::io::Error::new(
            e.kind(),
            format!("bind ipc socket {}: {e}", sock_path.display()),
        ))
    })?;
    Ok(listener)
}

/// Spawn the accept loop. Returns a join handle; the daemon drops or aborts
/// it during shutdown. Each connection is its own task.
pub fn spawn_accept(state: RpcState, listener: UnixListener) -> JoinHandle<()> {
    tokio::spawn(async move {
        loop {
            tokio::select! {
                () = state.shutdown.notified() => break,
                accepted = listener.accept() => {
                    match accepted {
                        Ok((stream, _addr)) => {
                            let st = state.clone();
                            tokio::spawn(async move {
                                if let Err(e) = handle_conn(st, stream).await {
                                    tracing::debug!("ipc conn closed: {e}");
                                }
                            });
                        }
                        Err(e) => {
                            tracing::debug!("ipc accept error: {e}");
                            tokio::time::sleep(Duration::from_millis(50)).await;
                        }
                    }
                }
            }
        }
    })
}

async fn handle_conn(state: RpcState, stream: UnixStream) -> std::io::Result<()> {
    let (read_half, mut write_half) = stream.into_split();
    let mut reader = BufReader::new(read_half);
    let mut line = String::new();

    loop {
        line.clear();
        let n = reader.read_line(&mut line).await?;
        if n == 0 {
            return Ok(());
        }
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        let parsed: Result<super::Request, _> = serde_json::from_str(trimmed);
        let req = match parsed {
            Ok(r) => r,
            Err(e) => {
                let resp = Response::err(Value::Null, super::ERR_PARSE, e.to_string());
                write_frame(&mut write_half, &resp).await?;
                continue;
            }
        };

        if req.method == "inbox.subscribe" {
            return handle_subscribe(state, &req, &mut write_half).await;
        }

        let id = req.id.clone().unwrap_or(Value::Null);
        let resp = dispatch(&state, req).await;
        write_frame(&mut write_half, &resp_to_envelope(resp, id)).await?;
    }
}

fn resp_to_envelope(r: Response, fallback_id: Value) -> Response {
    let mut r = r;
    if r.id.is_null() {
        r.id = fallback_id;
    }
    r
}

async fn write_frame<W: AsyncWriteExt + Unpin>(w: &mut W, resp: &Response) -> std::io::Result<()> {
    let s = serde_json::to_string(resp)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
    w.write_all(s.as_bytes()).await?;
    w.write_all(b"\n").await?;
    w.flush().await
}

// ---------------------------------------------------------------------------
// Method dispatch
// ---------------------------------------------------------------------------

async fn dispatch(state: &RpcState, req: super::Request) -> Response {
    let id = req.id.clone().unwrap_or(Value::Null);
    match req.method.as_str() {
        "daemon.ping" => Response::ok(
            id,
            json!({
                "now_ms": inbox::unix_now_ms(),
                "started_ms": state.started_ms,
                "version": PHINBOX_VERSION,
                "sock": state.sock_path.to_string_lossy(),
            }),
        ),

        "daemon.shutdown" => {
            state.shutdown.notify_waiters();
            Response::ok(id, json!({ "ok": true }))
        }

        "inbox.list" => match list_pending(&state.root) {
            Ok(reqs) => Response::ok(id, json!({ "requests": reqs })),
            Err(e) => Response::err(id, super::ERR_IO, e.to_string()),
        },

        "inbox.get" => match parse_params::<RidParams>(&req.params) {
            Ok(p) => match inbox::load_request(&state.root, &p.rid) {
                Ok(Some(r)) => Response::ok(id, json!({ "request": r })),
                Ok(None) => Response::err(id, super::ERR_NOT_FOUND, format!("rid={}", p.rid)),
                Err(e) => Response::err(id, super::ERR_IO, e.to_string()),
            },
            Err(e) => Response::err(id, super::ERR_INVALID_PARAMS, e.clone()),
        },

        "inbox.answer" => match parse_params::<AnswerParams>(&req.params) {
            Ok(p) => match finalize_via_state(state, &p.rid, p.response).await {
                Ok(updated) => Response::ok(id, json!({ "request": updated })),
                Err(e) => e,
            },
            Err(e) => Response::err(id, super::ERR_INVALID_PARAMS, e.clone()),
        },

        "inbox.cancel" => match parse_params::<RidParams>(&req.params) {
            Ok(p) => match finalize_via_state(state, &p.rid, ElicitResponse::Cancelled { notes: None }).await {
                Ok(updated) => Response::ok(id, json!({ "request": updated })),
                Err(e) => e,
            },
            Err(e) => Response::err(id, super::ERR_INVALID_PARAMS, e.clone()),
        },

        _ => Response::err(id, super::ERR_METHOD_NOT_FOUND, req.method.clone()),
    }
}

fn parse_params<T: for<'de> Deserialize<'de>>(params: &Value) -> Result<T, String> {
    if params.is_null() {
        return serde_json::from_value(Value::Object(Default::default()))
            .map_err(|e| e.to_string());
    }
    serde_json::from_value(params.clone()).map_err(|e| e.to_string())
}

/// Finalize a request with the given response.
async fn finalize_via_state(
    state: &RpcState,
    rid: &str,
    response: ElicitResponse,
) -> Result<PendingRequest, Response> {
    let mut pending = match load_pending(&state.root, rid) {
        Ok(Some(p)) => p,
        Ok(None) => return Err(Response::err(Value::Null, super::ERR_NOT_FOUND, format!("rid={rid}"))),
        Err(e) => return Err(Response::err(Value::Null, super::ERR_IO, e.to_string())),
    };
    if !matches!(pending.state, RequestState::Pending) {
        return Err(Response::err(
            Value::Null,
            super::ERR_BAD_STATE,
            format!("rid={rid} already finalized (state={:?})", pending.state),
        ));
    }
    let new_state = match &response {
        ElicitResponse::Cancelled { .. } => RequestState::Cancelled,
        ElicitResponse::TimedOut { .. } => RequestState::Expired,
        ElicitResponse::Failed { .. } => RequestState::Expired,
        ElicitResponse::Answered { .. } => RequestState::Answered,
    };
    pending.state = new_state;
    pending.response = Some(response);
    match crate::inbox::finalize(&state.root, &pending) {
        Ok(_path) => {
            let status = match &pending.response {
                Some(ElicitResponse::Cancelled { .. }) => ResponseStatus::Cancelled,
                Some(ElicitResponse::TimedOut { .. }) => ResponseStatus::TimedOut,
                Some(_) => ResponseStatus::Answered,
                None => ResponseStatus::Pending,
            };
            state.notify_answered(rid, status);
            Ok(pending)
        }
        Err(e) => Err(Response::err(Value::Null, super::ERR_IO, e.to_string())),
    }
}

// ---------------------------------------------------------------------------
// Subscribe (server-streaming via line-delimited JSON)
// ---------------------------------------------------------------------------

async fn handle_subscribe<W: AsyncWriteExt + Unpin>(
    state: RpcState,
    req: &super::Request,
    w: &mut W,
) -> std::io::Result<()> {
    let id = req.id.clone().unwrap_or(Value::Null);

    let pending = list_pending(&state.root).unwrap_or_default();
    let snapshot = json!({
        "jsonrpc": "2.0",
        "id": id,
        "result": {
            "kind": "snapshot",
            "requests": pending,
        }
    });
    write_frame(w, &serde_json::from_value::<Response>(snapshot).unwrap_or_else(|_| {
        Response::ok(id.clone(), json!({ "kind": "snapshot", "requests": pending }))
    }))
    .await?;

    let mut rx = state.changes.subscribe();
    loop {
        tokio::select! {
            () = state.shutdown.notified() => return Ok(()),
            evt = rx.recv() => match evt {
                Ok(change) => {
                    let payload = serde_json::to_value(&change).unwrap_or(Value::Null);
                    let resp = Response::ok(id.clone(), payload);
                    write_frame(w, &resp).await?;
                }
                Err(broadcast::error::RecvError::Lagged(_)) => continue,
                Err(broadcast::error::RecvError::Closed) => return Ok(()),
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Params
// ---------------------------------------------------------------------------

#[derive(Debug, Default, Deserialize)]
struct AnswerParams {
    rid: String,
    response: ElicitResponse,
}

#[derive(Debug, Default, Deserialize)]
struct RidParams {
    rid: String,
}
