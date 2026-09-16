//! Sync IPC client used by CLI subcommands.

use std::path::PathBuf;

use serde_json::{json, Value};

use crate::error::ElicitError;
use crate::inbox;

use super::{live_socket, monotonic_id, Request, Response};

/// A small blocking client used by the CLI subcommands. Each call opens a new
/// socket connection -- the daemon's accept loop is already concurrent and the
/// latency on UDS is microseconds, so connection reuse isn't worth the
/// complexity for human-driven CLI use.
pub struct Client {
    sock: PathBuf,
}

impl Client {
    pub fn connect_to(sock: PathBuf) -> Result<Self, ElicitError> {
        if !sock.exists() {
            return Err(ElicitError::Io(std::io::Error::new(
                std::io::ErrorKind::NotFound,
                format!("ipc socket not found at {}", sock.display()),
            )));
        }
        Ok(Self { sock })
    }

    /// Convenience constructor that walks the inbox root + lockfile.
    pub fn connect_default() -> Result<Self, ElicitError> {
        let root = inbox::default_inbox_root();
        let sock = live_socket(&root)
            .ok_or_else(|| ElicitError::Io(std::io::Error::new(
                std::io::ErrorKind::NotFound,
                "no live phinbox daemon (no lockfile with ipc_sock)",
            )))?;
        Self::connect_to(sock)
    }

    pub fn call(&self, method: &str, params: Value) -> Result<Value, ElicitError> {
        let req = Request {
            jsonrpc: "2.0".into(),
            id: Some(json!(monotonic_id())),
            method: method.to_string(),
            params,
        };
        let line = serde_json::to_string(&req).map_err(ElicitError::Json)?;
        let mut s = std::os::unix::net::UnixStream::connect(&self.sock).map_err(|e| {
            ElicitError::Io(std::io::Error::new(
                e.kind(),
                format!("connect ipc {}: {e}", self.sock.display()),
            ))
        })?;
        use std::io::Write;
        s.write_all(line.as_bytes()).map_err(ElicitError::Io)?;
        s.write_all(b"\n").map_err(ElicitError::Io)?;
        let mut reader = std::io::BufReader::new(s);
        let mut buf = String::new();
        use std::io::BufRead;
        reader.read_line(&mut buf).map_err(ElicitError::Io)?;
        let resp: Response = serde_json::from_str(buf.trim()).map_err(ElicitError::Json)?;
        if let Some(err) = resp.error {
            return Err(ElicitError::Rpc {
                code: err.code,
                message: err.message,
            });
        }
        Ok(resp.result.unwrap_or(Value::Null))
    }
}
