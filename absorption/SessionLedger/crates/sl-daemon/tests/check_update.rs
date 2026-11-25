//! Smoke: `sl-daemon check-update` compares versions without network (`--latest`).

use std::process::Command;

fn sl_daemon_bin() -> Command {
    if let Ok(path) = std::env::var("CARGO_BIN_EXE_sl-daemon") {
        return Command::new(path);
    }
    let mut cmd = Command::new("cargo");
    cmd.args(["run", "-q", "-p", "sl-daemon", "--"]);
    cmd
}

#[test]
fn check_update_reports_up_to_date_with_matching_latest() {
    let output = sl_daemon_bin()
        .args(["check-update", "--latest", "v0.1.0"])
        .output()
        .unwrap_or_else(|err| panic!("failed to run check-update: {err}"));
    assert!(
        output.status.success(),
        "expected exit 0 for matching latest, got {:?}: {}",
        output.status.code(),
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("up to date"), "expected up-to-date message, got:\n{stdout}");
}

#[test]
fn check_update_reports_update_available_with_newer_latest() {
    let output = sl_daemon_bin()
        .args(["check-update", "--latest", "v99.0.0"])
        .output()
        .unwrap_or_else(|err| panic!("failed to run check-update: {err}"));
    assert_eq!(
        output.status.code(),
        Some(1),
        "expected exit 1 for newer latest, stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.contains("update available"),
        "expected update-available message, got:\n{stdout}"
    );
}

#[test]
fn check_update_json_output_is_valid() {
    let output = sl_daemon_bin()
        .args(["check-update", "--latest", "v99.0.0", "--json"])
        .output()
        .unwrap_or_else(|err| panic!("failed to run check-update --json: {err}"));
    assert_eq!(output.status.code(), Some(1));
    let stdout = String::from_utf8_lossy(&output.stdout);
    let value: serde_json::Value =
        serde_json::from_str(&stdout).unwrap_or_else(|err| panic!("invalid JSON: {err}\n{stdout}"));
    assert_eq!(value.get("status").and_then(|v| v.as_str()), Some("update_available"));
}
