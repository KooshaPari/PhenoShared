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

use std::{sync::atomic::AtomicU64, time::Duration};

use futures_util::{SinkExt, StreamExt};
use serde_json::{json, Value};
use tokio::net::TcpStream;
use tokio_tungstenite::{tungstenite::Message, MaybeTlsStream, WebSocketStream};

use crate::{CdpError, Result};

type Socket = WebSocketStream<MaybeTlsStream<TcpStream>>;

static CALL_SEQUENCE: AtomicU64 = AtomicU64::new(0);

/// One CDP connection.
pub struct Cdp {
    socket: Socket,
    timeout: Duration,
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
        })
    }

    /// Override the per-command timeout.
    pub fn with_timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
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
