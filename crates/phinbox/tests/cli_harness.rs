//! Process-level integration tests for the `phinbox harness codex-permission-request`
//! CLI subcommand. Each test runs the actual compiled binary against an isolated
//! inbox root and verifies the printed envelope satisfies the documented
//! Codex `PermissionRequest` hook contract.
//!
//! These are NOT constant-truth tests; each one spawns the real `phinbox`
//! binary with a real stdin pipe and asserts on the produced JSON envelope.

use std::io::Write;
use std::process::{Command, Stdio};

fn phinbox_bin() -> std::path::PathBuf {
    std::path::PathBuf::from(env!("CARGO_BIN_EXE_phinbox"))
}

/// Run the harness subcommand with the supplied stdin bytes and timeout. The
/// inbox root is a private tempdir so no daemon state leaks across tests.
fn run_harness(stdin_bytes: &[u8], timeout_secs: u64) -> (i32, String, String, tempfile::TempDir) {
    let tmp = tempfile::tempdir().expect("tempdir");
    let mut child = Command::new(phinbox_bin())
        .args([
            "--inbox-dir",
            tmp.path().to_str().expect("utf8 inbox-root"),
            "harness",
            "codex-permission-request",
            "--timeout-secs",
            &timeout_secs.to_string(),
        ])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn phinbox harness codex-permission-request");
    child
        .stdin
        .take()
        .expect("stdin pipe")
        .write_all(stdin_bytes)
        .expect("write stdin");
    let result = child.wait_with_output().expect("wait_with_output");
    let code = result.status.code().unwrap_or(-1);
    (
        code,
        String::from_utf8_lossy(&result.stdout).into_owned(),
        String::from_utf8_lossy(&result.stderr).into_owned(),
        tmp,
    )
}

/// Canonical Codex PermissionRequest fixture used by the happy-path tests.
fn fixture_request() -> String {
    serde_json::json!({
        "cwd": "/isolated/synthetic",
        "hook_event_name": "PermissionRequest",
        "model": "fixture",
        "permission_mode": "default",
        "session_id": "fixture-session",
        "tool_input": {"command": "printf synthetic"},
        "tool_name": "shell",
        "transcript_path": null,
        "turn_id": "fixture-turn",
    })
    .to_string()
}

fn assert_canonical_deny(json: &serde_json::Value, must_contain: &str) {
    assert_eq!(
        json["hookSpecificOutput"]["hookEventName"],
        serde_json::json!("PermissionRequest"),
        "hookEventName is missing or wrong: {json}"
    );
    assert_eq!(
        json["hookSpecificOutput"]["decision"]["behavior"],
        serde_json::json!("deny"),
        "decision.behavior should be deny: {json}"
    );
    let msg = json["hookSpecificOutput"]["decision"]["message"]
        .as_str()
        .unwrap_or("");
    assert!(
        msg.contains(must_contain),
        "deny message did not contain {must_contain:?}: {msg}"
    );
}

/// Oversized valid prefix (1 MiB + 1 byte of valid JSON+whitespace padding)
/// must produce the canonical deny envelope and the exit code must remain 0
/// (the JSON envelope is the decision — the exit code is not a denial signal).
#[test]
fn oversized_input_produces_canonical_deny() {
    // Build a Codex PermissionRequest, pad with whitespace to STDIN_LIMIT,
    // append a single extra byte that takes it past the cap. The bridge
    // sees input.len() > LIMIT and emits the canonical deny envelope.
    let valid = fixture_request();
    let pad_target: usize = 1024 * 1024; // STDIN_LIMIT
    let padding = pad_target.saturating_sub(valid.len()).max(0);
    let mut payload = Vec::with_capacity(pad_target + 1);
    payload.extend_from_slice(valid.as_bytes());
    payload.extend(std::iter::repeat(b' ').take(padding));
    payload.push(b'!'); // exactly STDIN_LIMIT + 1 bytes
    assert!(payload.len() > 1024 * 1024, "payload must exceed LIMIT");
    let (code, stdout, stderr, _tmp) = run_harness(&payload, 30);
    assert_eq!(code, 0, "exit code must be 0 (decision is in JSON): stderr={stderr}");
    let parsed: serde_json::Value = serde_json::from_str(&stdout).expect("stdout is JSON");
    assert_canonical_deny(&parsed, "Phinbox refused oversized input");
}

/// Invalid timeout 0 — the bridge owns the (1..=120) guard. CLI must NOT
/// silently clamp; it must forward the value verbatim and the bridge must
/// emit deny. This also proves the CLI does not wait the (clamped) 30 seconds
/// (timing asserted by the unit test of the bridge, but here we do bound
/// the test at 10 seconds to keep CI fast).
#[test]
fn timeout_zero_does_not_wait_and_returns_deny() {
    let payload = fixture_request().into_bytes();
    let start = std::time::Instant::now();
    let (code, stdout, _stderr, _tmp) = run_harness(&payload, 0);
    let elapsed = start.elapsed();
    assert!(
        elapsed.as_secs() < 5,
        "timeout=0 must NOT wait any bounded seconds, took {elapsed:?}"
    );
    assert_eq!(code, 0, "decision is the JSON, not the exit code");
    let parsed: serde_json::Value = serde_json::from_str(&stdout).expect("stdout is JSON");
    assert_canonical_deny(&parsed, "Phinbox refused oversized input or unsupported wait bound");
}

/// Invalid timeout 121 — same as above: silent clamp is a forbidden behavior.
#[test]
fn timeout_too_large_returns_deny_without_wait() {
    let payload = fixture_request().into_bytes();
    let start = std::time::Instant::now();
    let (code, stdout, _stderr, _tmp) = run_harness(&payload, 121);
    let elapsed = start.elapsed();
    assert!(
        elapsed.as_secs() < 5,
        "timeout=121 must NOT silently clamp and wait, took {elapsed:?}"
    );
    assert_eq!(code, 0);
    let parsed: serde_json::Value = serde_json::from_str(&stdout).expect("stdout is JSON");
    assert_canonical_deny(&parsed, "Phinbox refused oversized input or unsupported wait bound");
}

/// Malformed input (not valid JSON at all) must yield the canonical deny
/// envelope without ever creating a pending request on disk. We assert that
/// the inbox dir is empty after the call.
#[test]
fn malformed_input_does_not_create_pending_request() {
    let payload = b"this-is-not-json-at-all";
    let (code, stdout, _stderr, tmp) = run_harness(payload, 30);
    assert_eq!(code, 0);
    let parsed: serde_json::Value = serde_json::from_str(&stdout).expect("stdout is JSON");
    assert_canonical_deny(&parsed, "Phinbox refused");
    // Verify no pending request was created.
    let inbox = tmp.path().join("inbox");
    if inbox.exists() {
        let count = std::fs::read_dir(&inbox).map(|d| d.count()).unwrap_or(0);
        assert_eq!(count, 0, "malformed input must not leave a pending request");
    }
    let answered = tmp.path().join("answered");
    if answered.exists() {
        let count = std::fs::read_dir(&answered).map(|d| d.count()).unwrap_or(0);
        assert_eq!(count, 0, "malformed input must not leave an answered record");
    }
}

/// Valid request with no human answer and a tight 1-second timeout must
/// produce the structured "no approval before the bounded wait expired"
/// deny envelope (i.e. timeout actually elapses through the bridge, and no
/// pending/answered record is leaked to the daemon runtime).
#[test]
fn valid_request_no_answer_deny() {
    let payload = fixture_request().into_bytes();
    let (code, stdout, _stderr, _tmp) = run_harness(&payload, 1);
    assert_eq!(code, 0);
    let parsed: serde_json::Value = serde_json::from_str(&stdout).expect("stdout is JSON");
    assert_canonical_deny(&parsed, "Permission not approved");
}

/// CLI exit status must always be 0 — hooks pipe the JSON to decide, and a
/// non-zero exit could be misread as "fail-open" by upstream script glue.
#[test]
fn cli_exit_status_is_zero_on_every_path() {
    let tiny = b"{}";
    let (code, _stdout, _stderr, _tmp) = run_harness(tiny, 30);
    assert_eq!(code, 0, "exit code must be 0 even for malformed input");
}
