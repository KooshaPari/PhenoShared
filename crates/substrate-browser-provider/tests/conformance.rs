//! The protocol's own conformance list, run against the real binary over the
//! real transport.
//!
//! `BROWSER_PROVIDER_PROTOCOL.md` names ten scenarios a certified provider must
//! pass. This drives the shipped `browser-provider` binary over stdio NDJSON,
//! so it exercises the wire format, the dispatch table and a real browser at
//! once.

use std::process::Stdio;

use serde_json::{json, Value};
use tokio::{
    io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader},
    process::{Child, ChildStdin, ChildStdout, Command},
};

const PAGE: &str = r#"<!doctype html>
<html><head><title>Conformance</title></head><body>
  <h1>Conformance page</h1>
  <button onclick="document.getElementById('out').textContent='clicked'">Go</button>
  <p id="out">idle</p>
  <form onsubmit="event.preventDefault(); document.getElementById('res').textContent='submitted:'+document.getElementById('q').value;">
    <input id="q" aria-label="Query" />
    <button type="submit">Send</button>
  </form>
  <p id="res"></p>
</body></html>"#;

async fn serve() -> std::net::SocketAddr {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind");
    let addr = listener.local_addr().expect("addr");
    tokio::spawn(async move {
        loop {
            let Ok((mut socket, _)) = listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let mut buffer = [0u8; 4096];
                let _ = socket.read(&mut buffer).await;
                let response = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {}\r\n\
                     Connection: close\r\n\r\n{}",
                    PAGE.len(),
                    PAGE
                );
                let _ = socket.write_all(response.as_bytes()).await;
                let _ = socket.shutdown().await;
            });
        }
    });
    addr
}

struct Client {
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
    next_id: u64,
}

impl Client {
    async fn spawn(root: &std::path::Path) -> Self {
        let mut child = Command::new(env!("CARGO_BIN_EXE_browser-provider"))
            .arg("--root")
            .arg(root)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .expect("spawn provider");
        let stdin = child.stdin.take().expect("stdin");
        let stdout = BufReader::new(child.stdout.take().expect("stdout"));
        Self {
            child,
            stdin,
            stdout,
            next_id: 1,
        }
    }

    async fn call(&mut self, method: &str, params: Value) -> Value {
        let id = self.next_id;
        self.next_id += 1;
        let request =
            json!({ "protocol_version": "0.1", "id": id, "method": method, "params": params });
        self.stdin
            .write_all(format!("{request}\n").as_bytes())
            .await
            .expect("write");
        self.stdin.flush().await.expect("flush");
        let mut line = String::new();
        self.stdout.read_line(&mut line).await.expect("read");
        serde_json::from_str(&line).unwrap_or_else(|err| {
            panic!("provider emitted a non-JSON line: {err}\n{line}");
        })
    }

    async fn ok(&mut self, method: &str, params: Value) -> Value {
        let response = self.call(method, params).await;
        assert_eq!(
            response.get("ok").and_then(Value::as_bool),
            Some(true),
            "{method} failed: {response}"
        );
        response.get("result").cloned().unwrap_or(Value::Null)
    }

    async fn shutdown(mut self) {
        drop(self.stdin);
        let _ = self.child.wait().await;
    }
}

#[tokio::test]
async fn satisfies_the_protocols_ten_conformance_scenarios() {
    if !substrate_browser_broker::browser_available() {
        eprintln!("skipping: no browser");
        return;
    }

    let addr = serve().await;
    let dir = tempfile::tempdir().expect("tempdir");
    let mut client = Client::spawn(dir.path()).await;

    // 1. provider.describe
    let describe = client.ok("provider.describe", json!({})).await;
    assert_eq!(
        describe.get("provider_id").and_then(Value::as_str),
        Some("substrate_browser_broker")
    );
    let core = describe["capabilities"]["core_methods"]
        .as_array()
        .expect("core methods");
    assert!(
        core.len() >= 10,
        "describe must advertise the core: {core:?}"
    );

    // 2. provider.status is coherent
    let status = client.ok("provider.status", json!({})).await;
    assert_eq!(
        status.get("availability").and_then(Value::as_str),
        Some("ready")
    );

    // 3. session.ensure creates a session
    let ensured = client
        .ok(
            "session.ensure",
            json!({ "principal": "alice", "profile": "conf", "client_session_id": "conf-1" }),
        )
        .await;
    let session_id = ensured
        .get("session_id")
        .and_then(Value::as_str)
        .expect("session id")
        .to_string();
    assert!(!session_id.is_empty());

    // 4. page.open navigates
    let opened = client
        .ok("page.open", json!({ "url": format!("http://{addr}/") }))
        .await;
    assert_eq!(
        opened.get("page_id").and_then(Value::as_str),
        Some("page_1")
    );

    // 5. page.snapshot returns usable text and an actionable reference
    let snapshot = client.ok("page.snapshot", json!({})).await;
    assert!(
        snapshot["text"]
            .as_str()
            .unwrap_or_default()
            .contains("Conformance page"),
        "snapshot text: {:?}",
        snapshot["text"]
    );
    let elements = snapshot["elements"].as_array().expect("elements");
    assert!(
        !elements.is_empty(),
        "snapshot must expose actionable elements"
    );

    let button_ref = elements
        .iter()
        .find(|node| node["role"] == "button" && node["name"] == "Go")
        .and_then(|node| node["element_ref"].as_str())
        .expect("Go button reference")
        .to_string();

    // 6. page.click activates it
    client
        .ok("page.click", json!({ "element_ref": button_ref }))
        .await;

    // 7. page.wait observes the deterministic change
    let waited = client
        .ok(
            "page.wait",
            json!({ "text_present": "clicked", "timeout_ms": 5000 }),
        )
        .await;
    assert_eq!(waited.get("satisfied").and_then(Value::as_bool), Some(true));

    // 8. page.type fills an input and submits
    let after_click = client.ok("page.snapshot", json!({})).await;
    let textbox_ref = after_click["elements"]
        .as_array()
        .expect("elements")
        .iter()
        .find(|node| node["role"] == "textbox")
        .and_then(|node| node["element_ref"].as_str())
        .expect("textbox reference")
        .to_string();
    client
        .ok(
            "page.type",
            json!({ "element_ref": textbox_ref, "text": "abc", "submit": true }),
        )
        .await;
    let submitted = client
        .ok(
            "page.wait",
            json!({ "text_present": "submitted:abc", "timeout_ms": 5000 }),
        )
        .await;
    assert_eq!(
        submitted.get("satisfied").and_then(Value::as_bool),
        Some(true)
    );

    // 9. page.screenshot returns an image
    let shot = client.ok("page.screenshot", json!({})).await;
    let image = shot.get("image").and_then(Value::as_str).expect("image");
    assert!(image.len() > 100, "screenshot too small");
    assert_eq!(
        shot.get("media_type").and_then(Value::as_str),
        Some("image/png")
    );

    // 10. session.close cleans up
    let closed = client.ok("session.close", json!({})).await;
    assert_eq!(closed.get("closed").and_then(Value::as_bool), Some(true));

    // And the protocol's error contract: unknown methods are refused, not crashed.
    let unsupported = client.call("page.teleport", json!({})).await;
    assert_eq!(unsupported.get("ok").and_then(Value::as_bool), Some(false));
    assert_eq!(
        unsupported["error"]["code"].as_str(),
        Some("unsupported_method")
    );

    client.shutdown().await;
}
