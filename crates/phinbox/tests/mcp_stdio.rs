//! Integration test that spawns the MCP server and exercises the
//! JSON-RPC protocol via stdin/stdout.
//!
//! The MCP protocol requires a synchronous `initialize` handshake before
//! any other method. We send messages one at a time and read each response
//! before sending the next, otherwise the rmcp transport will see EOF on
//! stdin before it can dispatch the queued requests.

use std::io::{BufRead, BufReader, Write};
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::thread;
use std::time::Duration;

use phinbox::spec::PromptSpec;

fn mcp_bin() -> std::path::PathBuf {
    std::path::PathBuf::from(env!("CARGO_BIN_EXE_phinbox-mcp"))
}

struct McpHandle {
    stdin: std::process::ChildStdin,
    stdout_rx: mpsc::Receiver<String>,
    stderr_rx: mpsc::Receiver<String>,
    child: std::process::Child,
}

impl McpHandle {
    fn spawn() -> Self {
        let mut child = Command::new(mcp_bin())
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .expect("spawn phinbox-mcp");

        let stdin = child.stdin.take().expect("stdin");
        let stdout = child.stdout.take().expect("stdout");
        let stderr = child.stderr.take().expect("stderr");

        let (out_tx, out_rx) = mpsc::channel::<String>();
        let (err_tx, err_rx) = mpsc::channel::<String>();
        thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line in reader.lines().map_while(Result::ok) {
                if out_tx.send(line).is_err() {
                    break;
                }
            }
        });
        thread::spawn(move || {
            let reader = BufReader::new(stderr);
            for line in reader.lines().map_while(Result::ok) {
                if err_tx.send(line).is_err() {
                    break;
                }
            }
        });

        McpHandle { stdin, stdout_rx: out_rx, stderr_rx: err_rx, child }
    }

    fn send(&mut self, msg: &serde_json::Value) {
        writeln!(self.stdin, "{}", serde_json::to_string(msg).unwrap()).expect("write");
        self.stdin.flush().expect("flush");
    }

    /// Read responses until we see one whose `id` matches `id`.
    fn recv_id(&self, id: i64, timeout: Duration) -> Option<serde_json::Value> {
        let deadline = std::time::Instant::now() + timeout;
        let mut collected = String::new();
        loop {
            let remaining = deadline.saturating_duration_since(std::time::Instant::now());
            if remaining.is_zero() {
                return None;
            }
            match self.stdout_rx.recv_timeout(remaining) {
                Ok(line) => {
                    if let Ok(v) = serde_json::from_str::<serde_json::Value>(&line) {
                        if v.get("id").and_then(|i| i.as_i64()) == Some(id) {
                            return Some(v);
                        }
                    } else {
                        collected.push_str(&line);
                        collected.push('\n');
                    }
                }
                Err(mpsc::RecvTimeoutError::Timeout) => return None,
                Err(mpsc::RecvTimeoutError::Disconnected) => return None,
            }
        }
    }

    fn shutdown(mut self) -> (String, String) {
        drop(self.stdin);
        let _ = self.child.wait();
        let mut err = String::new();
        while let Ok(line) = self.stderr_rx.try_recv() {
            err.push_str(&line);
            err.push('\n');
        }
        (String::new(), err)
    }
}

fn perform_handshake(h: &mut McpHandle) {
    let init = serde_json::json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": { "name": "phinbox-test", "version": "0.0.1" }
        }
    });
    h.send(&init);
    let resp = h.recv_id(1, Duration::from_secs(3)).expect("initialize response");
    assert_eq!(resp["jsonrpc"], "2.0");
    assert!(
        resp["result"]["serverInfo"]["name"].as_str() == Some("phinbox"),
        "expected server name 'phinbox', got {resp}"
    );
    let initialized = serde_json::json!({
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    });
    h.send(&initialized);
}

#[test]
fn mcp_server_lists_tools() {
    let mut h = McpHandle::spawn();
    perform_handshake(&mut h);

    let request = serde_json::json!({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    });
    h.send(&request);
    let resp = h.recv_id(2, Duration::from_secs(3)).expect("tools/list response");
    assert_eq!(resp["jsonrpc"], "2.0");
    let tools = resp["result"]["tools"].as_array().expect("tools array");
    let names: Vec<&str> = tools.iter().filter_map(|t| t["name"].as_str()).collect();
    assert!(
        names.contains(&"phinbox_mcp"),
        "tools list should include phinbox_mcp, got {names:?}"
    );
    h.shutdown();
}

#[test]
fn mcp_server_rejects_unknown_tool() {
    let mut h = McpHandle::spawn();
    perform_handshake(&mut h);

    let request = serde_json::json!({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "no_such_tool",
            "arguments": {}
        }
    });
    h.send(&request);
    let resp = h.recv_id(3, Duration::from_secs(3)).expect("tools/call response");
    assert!(resp.get("error").is_some(), "expected error response, got {resp}");
    h.shutdown();
}

#[test]
fn mcp_server_validates_prompt_spec() {
    let mut h = McpHandle::spawn();
    perform_handshake(&mut h);

    let request = serde_json::json!({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "phinbox_mcp",
            "arguments": {
                "title": "",
                "question": "q",
                "field": { "kind": "boolean", "label": "?" }
            }
        }
    });
    h.send(&request);
    let resp = h.recv_id(4, Duration::from_secs(3)).expect("tools/call response");
    let r = &resp["result"];
    let is_error = r.get("is_error").and_then(|v| v.as_bool()).unwrap_or(false);
    let has_invalid = serde_json::to_string(r)
        .is_ok_and(|s| s.contains("invalid"));
    assert!(
        is_error || resp.get("error").is_some() || has_invalid,
        "expected error response for invalid spec. got {resp}"
    );
    h.shutdown();
}

#[test]
fn mcp_server_schema_export_is_loadable() {
    // This validates that the JSON Schema we publish via the library
    // matches the schema we'd hand to an MCP client. Drift here would
    // be a contract break.
    let schema = phinbox::schema_json();
    let prompt_spec_schema = schemars::schema_for!(PromptSpec);
    let published = serde_json::to_value(prompt_spec_schema).unwrap();
    assert_eq!(schema, published);
}
