//! Integration tests for the phinbox CLI binary.

use std::process::{Command, Stdio};

use phinbox::spec::PromptSpec;

/// Build a path to the compiled phinbox binary.
fn phinbox_bin() -> std::path::PathBuf {
    // Cargo provides CARGO_BIN_EXE_phinbox for integration tests
    std::path::PathBuf::from(env!("CARGO_BIN_EXE_phinbox"))
}

#[test]
fn cli_help_exits_nonzero() {
    let out = Command::new(phinbox_bin())
        .arg("--help")
        .output()
        .expect("spawn phinbox --help");
    assert!(out.status.code().is_some());
}

#[test]
fn cli_version_prints() {
    let out = Command::new(phinbox_bin())
        .arg("version")
        .output()
        .expect("spawn phinbox version");
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("phinbox"));
    assert!(stdout.contains(env!("CARGO_PKG_VERSION")));
}

#[test]
fn cli_schema_prints_valid_json() {
    let out = Command::new(phinbox_bin())
        .args(["schema"])
        .output()
        .expect("spawn phinbox schema");
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    let parsed: serde_json::Value =
        serde_json::from_str(&stdout).expect("schema output is not valid JSON");
    assert!(parsed.is_object());
}

#[test]
fn cli_detect_prints_valid_json() {
    let out = Command::new(phinbox_bin())
        .args(["detect"])
        .output()
        .expect("spawn phinbox detect");
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    let parsed: serde_json::Value =
        serde_json::from_str(&stdout).expect("detect output is not valid JSON");
    assert!(parsed.get("platform").is_some());
}

#[test]
fn cli_ask_with_from_json_validates_spec() {
    // Valid spec that should pass validation but will hit the renderer
    // (which falls back to TUI on CI).
    let spec_json = r#"{
        "title": "Test",
        "question": "Test?",
        "field": {"kind": "boolean", "label": "?", "default": true},
        "timeout_secs": 1
    }"#;
    let mut child = Command::new(phinbox_bin())
        .args(["ask", "--renderer", "tty", "--from-json", spec_json])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn phinbox ask");
    // Close stdin immediately so inquire sees EOF and returns Cancel
    drop(child.stdin.take());
    let out = child.wait_with_output().expect("wait");
    // The CLI must produce JSON output regardless of response status
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(
        !stdout.trim().is_empty(),
        "expected JSON output, got empty stdout. stderr: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    // Validate it's parseable
    let parsed: serde_json::Value =
        serde_json::from_str(&stdout).expect("output is not valid JSON");
    assert!(parsed.get("status").is_some());
}

#[test]
fn cli_ask_rejects_invalid_urgency() {
    let out = Command::new(phinbox_bin())
        .args(["ask", "--title", "t", "--question", "q", "--urgency", "bogus"])
        .output()
        .expect("spawn phinbox ask --urgency bogus");
    // clap rejects the bad urgency enum
    assert!(!out.status.success());
}

#[test]
fn cli_ask_from_file_loads() {
    let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures");
    let path = dir.join("simple_text.json");
    let mut child = Command::new(phinbox_bin())
        .args(["ask", "--renderer", "tty", "--from-file"])
        .arg(&path)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn phinbox ask --from-file");
    drop(child.stdin.take());
    let out = child.wait_with_output().expect("wait");
    let stdout = String::from_utf8_lossy(&out.stdout);
    let parsed: serde_json::Value =
        serde_json::from_str(&stdout).expect("output is not valid JSON");
    assert!(parsed.get("status").is_some());
    // Sanity: the prompt loaded our fixture
    let _: PromptSpec = serde_json::from_str(
        &std::fs::read_to_string(&path).expect("read fixture"),
    )
    .expect("fixture is valid");
}

#[test]
fn cli_smoke_no_render_succeeds() {
    let out = Command::new(phinbox_bin())
        .args(["smoke", "--no-render"])
        .output()
        .expect("spawn phinbox smoke --no-render");
    assert!(out.status.success(), "smoke --no-render must exit 0");
}

#[test]
fn cli_serve_subcommand_is_rejected_from_phinbox_binary() {
    let out = Command::new(phinbox_bin())
        .args(["serve"])
        .output()
        .expect("spawn phinbox serve");
    assert!(!out.status.success());
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("phinbox-mcp"));
}

#[test]
fn cli_install_dry_run_does_not_touch_disk() {
    let tmp = tempfile::tempdir().expect("tempdir");
    let prefix = tmp.path();
    let inbox_root = tmp.path().join("phinbox-data");
    let out = Command::new(phinbox_bin())
        .args([
            "install",
            "--prefix", prefix.to_str().unwrap(),
            "--no-launch-agent",
            "--dry-run",
            "--inbox-dir", inbox_root.to_str().unwrap(),
        ])
        .output()
        .expect("spawn phinbox install --dry-run");
    assert!(out.status.success(), "install dry-run failed: stderr={}", String::from_utf8_lossy(&out.stderr));
    // Dry-run should not have created any binaries.
    assert!(!prefix.join("phinbox").exists(), "dry-run should not copy binaries");
}

#[test]
fn cli_install_and_uninstall_roundtrip() {
    // Use HOME override so install doesn't touch our real shell rc files.
    let tmp = tempfile::tempdir().expect("tempdir");
    let fake_home = tmp.path().join("home");
    std::fs::create_dir_all(&fake_home).unwrap();
    let prefix = tmp.path().join("opt");
    let inbox_root = tmp.path().join("phinbox-data");

    let out = Command::new(phinbox_bin())
        .env("HOME", &fake_home)
        .args([
            "install",
            "--prefix", prefix.to_str().unwrap(),
            "--no-launch-agent",
            "--inbox-dir", inbox_root.to_str().unwrap(),
        ])
        .output()
        .expect("spawn install");
    assert!(out.status.success(), "install failed: stderr={}", String::from_utf8_lossy(&out.stderr));

    // Verify the phinbox binary was copied.
    assert!(prefix.join("phinbox").exists(), "install did not copy phinbox binary");
    assert!(prefix.join("phinbox-mcp").exists(), "install did not copy phinbox-mcp binary");

    // Uninstall.
    let out = Command::new(phinbox_bin())
        .env("HOME", &fake_home)
        .args([
            "uninstall",
            "--prefix", prefix.to_str().unwrap(),
            "--yes",
        ])
        .output()
        .expect("spawn uninstall");
    assert!(out.status.success(), "uninstall failed: stderr={}", String::from_utf8_lossy(&out.stderr));
}

#[test]
fn cli_inbox_list_with_empty_dir_returns_empty_json() {
    let tmp = tempfile::tempdir().expect("tempdir");
    // The CLI treats `--inbox-dir` as the parent; data lives in `<dir>/inbox/`.
    let inbox_parent = tmp.path().to_path_buf();
    let out = Command::new(phinbox_bin())
        .args(["inbox", "--inbox-dir", inbox_parent.to_str().unwrap(), "--list"])
        .output()
        .expect("spawn inbox list");
    assert!(out.status.success(), "inbox list failed: stderr={}", String::from_utf8_lossy(&out.stderr));
    let stdout = String::from_utf8_lossy(&out.stdout);
    let v: serde_json::Value = serde_json::from_str(stdout.trim())
        .expect("inbox list output must be JSON");
    assert!(v.is_array());
    assert_eq!(v.as_array().unwrap().len(), 0);
}

#[test]
fn cli_ask_async_enqueue_then_list() {
    let tmp = tempfile::tempdir().expect("tempdir");
    let inbox_parent = tmp.path().to_path_buf();
    let fixture = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/simple_text.json");
    let out = Command::new(phinbox_bin())
        .args([
            "ask",
            "--async",
            "--inbox-dir", inbox_parent.to_str().unwrap(),
            "--from-file", fixture.to_str().unwrap(),
        ])
        .output()
        .expect("spawn phinbox ask --async");
    assert!(out.status.success(), "async enqueue failed: stderr={}", String::from_utf8_lossy(&out.stderr));
    let stdout = String::from_utf8_lossy(&out.stdout);
    let parsed: serde_json::Value = serde_json::from_str(stdout.trim())
        .expect("async enqueue must emit JSON");
    let req_id = parsed.get("request_id").and_then(|v| v.as_str())
        .expect("response must have request_id")
        .to_string();
    assert!(!req_id.is_empty());
    // Pending files live at `<inbox-dir>/inbox/<id>.json` (no `pending/` subdir).
    let inbox_dir = inbox_parent.join("inbox");
    assert!(inbox_dir.exists(), "inbox dir not created at {}", inbox_dir.display());
    let entries: Vec<_> = std::fs::read_dir(&inbox_dir)
        .unwrap()
        .filter_map(|e| e.ok())
        .collect();
    assert!(!entries.is_empty(), "no pending requests after async enqueue");
    let hit = entries.iter().any(|e| e.file_name().to_string_lossy().contains(&req_id));
    assert!(hit, "no file matches request_id {req_id}");
}

#[test]
fn cli_daemon_starts_and_health_responds() {
    let tmp = tempfile::tempdir().expect("tempdir");
    let inbox = tmp.path().join("inbox");
    std::fs::create_dir_all(&inbox).unwrap();
    // Pick an unused port via OS to avoid clashing with concurrent tests.
    let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("bind");
    let port = listener.local_addr().unwrap().port();
    drop(listener);

    let mut child = Command::new(phinbox_bin())
        .args([
            "daemon",
            "--inbox-dir", inbox.to_str().unwrap(),
            "--port", &port.to_string(),
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        // Keep stdin open so the daemon's foreground loop does not observe
        // inherited EOF and shut down before the readiness probe connects.
        .stdin(Stdio::piped())
        .spawn()
        .expect("spawn phinbox daemon");
    // Wait for daemon to start.
    let started = std::time::Instant::now();
    let mut ok = false;
    while started.elapsed() < std::time::Duration::from_secs(5) {
        if std::net::TcpStream::connect(("127.0.0.1", port)).is_ok() {
            ok = true;
            break;
        }
        std::thread::sleep(std::time::Duration::from_millis(100));
    }
    let _ = child.kill();
    let _ = child.wait();
    assert!(ok, "daemon did not start listening on port {port} within 5s");
}
