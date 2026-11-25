//! Minimal CDP transport: one WebSocket, serialized request/response.
//!
//! # Why serialized
//!
//! The protocol allows concurrent commands. This client issues one command at a
//! time and reads until the matching `id` comes back, discarding events. That is
//! enough for a single agent driving a single page, and it removes an entire
//! class of routing bugs. Concurrency across agents is provided by giving each
//! agent its own browser and its own profile generation, not by multiplexing one
//! connection.

use std::{
    sync::{atomic::AtomicU64, Arc},
    time::Duration,
};

use futures_util::{SinkExt, StreamExt};
use serde_json::{json, Value};
use tokio::net::TcpStream;
use tokio_tungstenite::{tungstenite::Message, MaybeTlsStream, WebSocketStream};

use crate::{CdpError, Result};

type Socket = WebSocketStream<MaybeTlsStream<TcpStream>>;

static CALL_SEQUENCE: AtomicU64 = AtomicU64::new(0);

/// A lease-fencing check invoked before every CDP command.
///
/// Implementors return `Err(reason)` when the caller no longer holds the
/// lease for the browser; the transport refuses to write the frame and
/// surfaces the reason as a protocol error.
pub trait FenceCheck: Send + Sync {
    /// Return `Ok(())` when the fence is satisfied, or `Err(reason)`.
    fn check(&self) -> std::result::Result<(), String>;
}

/// Evaluate a fence, returning its failure reason if any.
fn evaluate_fence(fence: &Option<Arc<dyn FenceCheck>>) -> std::result::Result<(), String> {
    match fence {
        Some(fence) => fence.check(),
        None => Ok(()),
    }
}

/// One CDP connection.
pub struct Cdp {
    socket: Socket,
    timeout: Duration,
    fence: Option<Arc<dyn FenceCheck>>,
}

impl std::fmt::Debug for Cdp {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Cdp")
            .field("timeout", &self.timeout)
            .finish_non_exhaustive()
    }
}

impl Cdp {
    /// Connect to a browser or target WebSocket endpoint.
    pub async fn connect(ws_url: &str) -> Result<Self> {
        let (socket, _response) = tokio_tungstenite::connect_async(ws_url)
            .await
            .map_err(|err| CdpError::Protocol(format!("websocket connect failed: {err}")))?;
        Ok(Self {
            socket,
            timeout: Duration::from_secs(30),
            fence: None,
        })
    }

    /// Override the per-command timeout.
    pub fn with_timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
    }

    /// Install or clear the lease fence checked before every command.
    pub fn set_fence(&mut self, fence: Option<Arc<dyn FenceCheck>>) {
        self.fence = fence;
    }

    /// Send one command and wait for its result.
    ///
    /// `session` targets a flattened session, which is how a page inside the
    /// browser connection is addressed after `Target.attachToTarget`.
    pub async fn call(
        &mut self,
        method: &str,
        params: Value,
        session: Option<&str>,
    ) -> Result<Value> {
        let id = CALL_SEQUENCE
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed)
            .wrapping_add(1);

        let mut message = json!({ "id": id, "method": method, "params": params });
        if let Some(session) = session {
            message["sessionId"] = Value::String(session.to_string());
        }

        let text = message.to_string();
        if let Err(reason) = evaluate_fence(&self.fence) {
            return Err(CdpError::Protocol(reason));
        }
        self.socket
            .send(Message::Text(text.into()))
            .await
            .map_err(|err| CdpError::Protocol(format!("websocket send failed: {err}")))?;

        let deadline = tokio::time::Instant::now() + self.timeout;
        loop {
            let remaining = deadline.saturating_duration_since(tokio::time::Instant::now());
            if remaining.is_zero() {
                return Err(CdpError::Timeout(format!(
                    "{method} produced no response within {}s",
                    self.timeout.as_secs()
                )));
            }

            let frame = tokio::time::timeout(remaining, self.socket.next())
                .await
                .map_err(|_| {
                    CdpError::Timeout(format!(
                        "{method} produced no response within {}s",
                        self.timeout.as_secs()
                    ))
                })?;

            let Some(frame) = frame else {
                return Err(CdpError::Protocol(
                    "devtools connection closed while awaiting a response".into(),
                ));
            };
            let frame =
                frame.map_err(|err| CdpError::Protocol(format!("websocket read failed: {err}")))?;

            let payload = match frame {
                Message::Text(text) => text.to_string(),
                Message::Binary(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
                Message::Close(_) => {
                    return Err(CdpError::Protocol(
                        "devtools connection closed while awaiting a response".into(),
                    ))
                },
                _ => continue,
            };

            let value: Value = match serde_json::from_str(&payload) {
                Ok(value) => value,
                Err(_) => continue,
            };

            // A response carries our id. Everything else is an event.
            if value.get("id").and_then(Value::as_u64) != Some(id) {
                continue;
            }

            if let Some(error) = value.get("error") {
                let message = error
                    .get("message")
                    .and_then(Value::as_str)
                    .unwrap_or("unknown devtools error");
                return Err(CdpError::DevTools {
                    method: method.to_string(),
                    message: message.to_string(),
                });
            }

            return Ok(value.get("result").cloned().unwrap_or(Value::Null));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct AlwaysOk;
    impl FenceCheck for AlwaysOk {
        fn check(&self) -> std::result::Result<(), String> {
            Ok(())
        }
    }

    struct AlwaysErr {
        reason: String,
    }
    impl FenceCheck for AlwaysErr {
        fn check(&self) -> std::result::Result<(), String> {
            Err(self.reason.clone())
        }
    }

    #[test]
    fn evaluate_fence_none_is_ok() {
        assert!(evaluate_fence(&None).is_ok());
    }

    #[test]
    fn evaluate_fence_ok_passes() {
        let f: Option<Arc<dyn FenceCheck>> = Some(Arc::new(AlwaysOk));
        assert!(evaluate_fence(&f).is_ok());
    }

    #[test]
    fn evaluate_fence_err_propagates_reason() {
        let f: Option<Arc<dyn FenceCheck>> = Some(Arc::new(AlwaysErr {
            reason: "lease lost".to_string(),
        }));
        assert_eq!(evaluate_fence(&f), Err("lease lost".to_string()));
    }
}
