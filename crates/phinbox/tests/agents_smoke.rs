//! Cross-client smoke tests — verify each installed agent has a valid
//! elicate MCP config entry, and the MCP server responds to the standard
//! handshake.

use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::thread;
use std::time::Duration;

// ─── helpers ────────────────────────────────────────────────────────
fn phinbox_bin() -> PathBuf {
    PathBuf::from(env!("CARGO_BIN_EXE_phinbox"))
}

fn home() -> PathBuf {
    dirs::home_dir().expect("$HOME")
}

fn agent_config_exists(path: &str) -> bool {
    let p = home().join(path);
    p.exists()
}

fn config_contains(path: &str, needle: &str) -> bool {
    let p = home().join(path);
    match fs::read_to_string(&p) {
        Ok(content) => content.contains(needle),
        Err(_) => false,
    }
}

// ─── per-agent config presence tests ────────────────────────────────

#[test]
fn forgecode_plugin_toml_exists() {
    let p = home()
        .join("CodeProjects/Phenotype/repos/phenotype-tooling")
        .join(".forgecode/plugins/phinbox/plugin.toml");
    assert!(
        p.exists(),
        "forgecode plugin.toml missing at {}",
        p.display()
    );
    let content = fs::read_to_string(&p).unwrap();
    assert!(
        content.contains("phinbox-mcp"),
        "plugin.toml must reference phinbox-mcp"
    );
}

#[test]
fn codex_mcp_toml_has_phinbox() {
    if !agent_config_exists(".codex/mcp.toml") {
        eprintln!("SKIP: ~/.codex/mcp.toml not found");
        return;
    }
    assert!(
        config_contains(".codex/mcp.toml", "phinbox"),
        "~/.codex/mcp.toml must register phinbox"
    );
}

#[test]
fn cursor_mcp_json_has_phinbox() {
    if !agent_config_exists(".cursor/mcp.json") {
        eprintln!("SKIP: ~/.cursor/mcp.json not found");
        return;
    }
    assert!(
        config_contains(".cursor/mcp.json", "phinbox"),
        "~/.cursor/mcp.json must register phinbox"
    );
}

#[test]
fn claude_json_has_phinbox() {
    if !agent_config_exists(".claude.json") {
        eprintln!("SKIP: ~/.claude.json not found");
        return;
    }
    assert!(
        config_contains(".claude.json", "phinbox"),
        "~/.claude.json must register phinbox in mcpServers"
    );
}

#[test]
fn kilo_jsonc_has_phinbox() {
    if !agent_config_exists(".config/kilo/kilo.jsonc") {
        eprintln!("SKIP: ~/.config/kilo/kilo.jsonc not found");
        return;
    }
    assert!(
        config_contains(".config/kilo/kilo.jsonc", "phinbox"),
        "~/.config/kilo/kilo.jsonc must register phinbox"
    );
}

#[test]
fn droid_mcp_json_has_phinbox() {
    if !agent_config_exists(".factory/mcp.json") {
        eprintln!("SKIP: ~/.factory/mcp.json not found");
        return;
    }
    assert!(
        config_contains(".factory/mcp.json", "phinbox"),
        "~/.factory/mcp.json must register phinbox"
    );
}

#[test]
fn phinbox_mcp_is_on_path() {
    assert!(
        which::which("phinbox-mcp").is_ok(),
        "phinbox-mcp must be on $PATH"
    );
}

// ─── MCP handshake smoke test ──────────────────────────────────────

#[test]
fn mcp_handshake_initialize_and_list_tools() {
    struct McpHandle {
        stdin: std::process::ChildStdin,
        stdout_rx: mpsc::Receiver<String>,
        stderr_rx: mpsc::Receiver<String>,
        child: std::process::Child,
    }

    impl McpHandle {
        fn spawn() -> Self {
            let mut child = Command::new("phinbox-mcp")
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .expect("failed to spawn phinbox-mcp");

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

            Self {
                stdin,
                stdout_rx: out_rx,
                stderr_rx: err_rx,
                child,
            }
        }

        fn send(&mut self, msg: &serde_json::Value) {
            writeln!(self.stdin, "{}", serde_json::to_string(msg).unwrap()).expect("write");
            self.stdin.flush().expect("flush");
        }

        fn recv_id(&self, id: i64, timeout: Duration) -> Option<serde_json::Value> {
            let deadline = std::time::Instant::now() + timeout;
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
                        }
                    }
                    Err(mpsc::RecvTimeoutError::Timeout) => return None,
                    Err(mpsc::RecvTimeoutError::Disconnected) => return None,
                }
            }
        }

        fn shutdown(mut self) -> String {
            drop(self.stdin);
            let _ = self.child.wait();
            let mut err = String::new();
            while let Ok(line) = self.stderr_rx.try_recv() {
                err.push_str(&line);
                err.push('\n');
            }
            err
        }
    }

    let mut h = McpHandle::spawn();

    let init = serde_json::json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": { "name": "smoke-test", "version": "0.0.1" }
        }
    });
    h.send(&init);
    let resp = h
        .recv_id(1, Duration::from_secs(3))
        .expect("initialize response");
    assert_eq!(resp["jsonrpc"], "2.0");

    let initialized = serde_json::json!({
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    });
    h.send(&initialized);

    let request = serde_json::json!({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    });
    h.send(&request);

    let parsed = h
        .recv_id(2, Duration::from_secs(3))
        .expect("tools/list response");

    assert_eq!(parsed["id"], 2, "expected id:2 in tools/list response");

    let tools = parsed["result"]["tools"]
        .as_array()
        .expect("tools/list result.tools is not an array");

    let names: Vec<&str> = tools.iter().filter_map(|t| t["name"].as_str()).collect();

    assert!(
        names.contains(&"phinbox_mcp"),
        "tools/list must include 'phinbox_mcp', got: {names:?}"
    );
    let _stderr = h.shutdown();
}

// ─── smoke: phinbox CLI ──────────────────────────────────────────

#[test]
fn phinbox_smoke_reports_ok() {
    let output = std::process::Command::new(phinbox_bin())
        .arg("smoke")
        .output()
        .expect("failed to run phinbox smoke");

    let stderr = String::from_utf8_lossy(&output.stderr);
    // smoke should exit 0 even if the popup times out (it reports OK or popup timeout)
    assert!(
        output.status.success(),
        "phinbox smoke exited with {:?} — stderr: {}",
        output.status,
        stderr.chars().take(500).collect::<String>()
    );
}

#[test]
fn phinbox_version_reports_semver() {
    let output = std::process::Command::new(phinbox_bin())
        .arg("--version")
        .output()
        .expect("failed to run phinbox --version");

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.contains("phinbox"),
        "expected 'phinbox' in --version output, got: {stdout}"
    );
    assert!(output.status.success(), "phinbox --version failed");
}

#[test]
fn phinbox_schema_exports_valid_json() {
    let output = std::process::Command::new(phinbox_bin())
        .arg("schema")
        .output()
        .expect("failed to run phinbox schema");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let parsed: serde_json::Value =
        serde_json::from_str(&stdout).expect("phinbox schema output is not valid JSON");

    assert!(
        parsed.get("properties").is_some(),
        "schema must have 'properties' key"
    );
    assert!(
        parsed.get("$schema").is_some(),
        "schema must have '$schema' key"
    );
}

#[test]
fn phinbox_detect_reports_platform() {
    let output = std::process::Command::new(phinbox_bin())
        .arg("detect")
        .output()
        .expect("failed to run phinbox detect");

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.contains("macos") || stdout.contains("linux") || stdout.contains("windows"),
        "detect must report a platform, got: {stdout}"
    );
    assert!(output.status.success());
}
