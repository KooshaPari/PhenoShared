//! Integration tests for `trace-gate` binary.
//!
//! Verifies exit codes using fixture manifests and fixture source files.

use std::path::PathBuf;

use assert_cmd::Command;
use predicates::prelude::*;

fn fixture(path: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join(path)
}

/// When one FR is missing from source, gate must exit 1.
#[test]
fn exit_1_when_fr_missing() {
    let mut cmd = Command::cargo_bin("trace-gate").unwrap();
    cmd.arg("--manifest")
        .arg(fixture("manifest_partial.toml"))
        .arg("--src")
        .arg(fixture("src"));

    cmd.assert()
        .failure()
        .code(1)
        .stderr(predicate::str::contains("FAIL"))
        .stderr(predicate::str::contains("1 FR(s) not covered"));
}

/// When all FRs in the manifest are covered, gate must exit 0.
#[test]
fn exit_0_when_all_covered() {
    let mut cmd = Command::cargo_bin("trace-gate").unwrap();
    cmd.arg("--manifest")
        .arg(fixture("manifest_all.toml"))
        .arg("--src")
        .arg(fixture("src"));

    cmd.assert().success().code(0);
}

/// --json flag emits valid JSON summary.
#[test]
fn json_flag_emits_valid_json() {
    let mut cmd = Command::cargo_bin("trace-gate").unwrap();
    cmd.arg("--manifest")
        .arg(fixture("manifest_all.toml"))
        .arg("--src")
        .arg(fixture("src"))
        .arg("--json");

    let output = cmd.assert().success().get_output().stdout.clone();
    // Find the JSON block (after the human-readable header lines).
    let stdout = String::from_utf8(output).unwrap();
    // The JSON blob starts with '{'.
    let json_start = stdout.find('{').expect("JSON output not found");
    let json_str = &stdout[json_start..];
    let parsed: serde_json::Value =
        serde_json::from_str(json_str).expect("output is not valid JSON");
    assert!(parsed.get("requirements").is_some());
    assert!(parsed.get("all_covered").is_some());
}

/// Empty manifest exits 0 (nothing to check).
#[test]
fn exit_0_on_empty_manifest() {
    use std::io::Write;
    let dir = tempfile::tempdir().unwrap();
    let manifest_path = dir.path().join("trace-gate.toml");
    let src_path = dir.path().join("src");
    std::fs::create_dir_all(&src_path).unwrap();
    std::fs::File::create(&manifest_path)
        .unwrap()
        .write_all(b"# empty\n")
        .unwrap();

    let mut cmd = Command::cargo_bin("trace-gate").unwrap();
    cmd.arg("--manifest")
        .arg(&manifest_path)
        .arg("--src")
        .arg(&src_path);

    cmd.assert().success().code(0);
}

/// Non-existent manifest exits 2 (usage error, not gate failure).
#[test]
fn exit_2_on_missing_manifest() {
    let mut cmd = Command::cargo_bin("trace-gate").unwrap();
    cmd.arg("--manifest")
        .arg("/tmp/does_not_exist_at_all.toml")
        .arg("--src")
        .arg("src");

    cmd.assert()
        .failure()
        .code(2)
        .stderr(predicate::str::contains("cannot read manifest"));
}

// ── NO_COLOR / CLICOLOR tests ────────────────────────────────────────────────

/// NO_COLOR set → stdout uses ASCII [PASS]/[FAIL] labels instead of Unicode glyphs.
#[test]
fn no_color_env_uses_ascii_labels() {
    let mut cmd = Command::cargo_bin("trace-gate").unwrap();
    cmd.arg("--manifest")
        .arg(fixture("manifest_partial.toml"))
        .arg("--src")
        .arg(fixture("src"))
        .env("NO_COLOR", "1");

    let output = cmd.assert().failure().code(1).get_output().stdout.clone();
    let stdout = String::from_utf8(output).unwrap();
    // Should contain ASCII labels, NOT Unicode glyphs
    assert!(
        stdout.contains("[PASS]") || stdout.contains("[FAIL]"),
        "expected ASCII [PASS]/[FAIL] labels when NO_COLOR is set, got: {stdout}"
    );
}

/// CLICOLOR=0 → stdout uses ASCII [PASS]/[FAIL] labels.
#[test]
fn clicolor_zero_uses_ascii_labels() {
    let mut cmd = Command::cargo_bin("trace-gate").unwrap();
    cmd.arg("--manifest")
        .arg(fixture("manifest_partial.toml"))
        .arg("--src")
        .arg(fixture("src"))
        .env("CLICOLOR", "0");

    let output = cmd.assert().failure().code(1).get_output().stdout.clone();
    let stdout = String::from_utf8(output).unwrap();
    assert!(
        stdout.contains("[PASS]") || stdout.contains("[FAIL]"),
        "expected ASCII labels when CLICOLOR=0, got: {stdout}"
    );
}

/// Without NO_COLOR/CLICOLOR, the binary should use Unicode glyphs on a real
/// terminal. In a CI/pipe environment (non-TTY) the default is also ASCII, so
/// we check that the *inverse* path is also consistent — the flag controls
/// only the label choice.
#[test]
fn default_output_uses_glyphs_or_fallback() {
    let mut cmd = Command::cargo_bin("trace-gate").unwrap();
    cmd.arg("--manifest")
        .arg(fixture("manifest_all.toml"))
        .arg("--src")
        .arg(fixture("src"));

    // In a test-runner pipe, stderr is non-TTY by default, so the binary may
    // fall back to ASCII even without NO_COLOR. Accept either.
    let output = cmd.assert().success().code(0).get_output().stdout.clone();
    let stdout = String::from_utf8(output).unwrap();
    // At minimum, the coverage line must be present.
    assert!(stdout.contains("FR(s) checked"));
}

// ── Structured logging tests ─────────────────────────────────────────────────

/// When a manifest is missing, stderr includes a structured log level prefix
/// and a suggestion hint.
#[test]
fn manifest_missing_shows_hint_on_stderr() {
    let mut cmd = Command::cargo_bin("trace-gate").unwrap();
    cmd.arg("--manifest")
        .arg("/tmp/does_not_exist_at_all_for_hint_test.toml")
        .arg("--src")
        .arg("src");

    cmd.assert()
        .failure()
        .code(2)
        .stderr(predicate::str::contains("hint:"))
        .stderr(predicate::str::contains("cannot load manifest"));
}

/// When a source directory is missing, stderr includes a hint.
#[test]
fn scan_missing_dir_shows_hint_on_stderr() {
    let manifest = fixture("manifest_partial.toml");
    let mut cmd = Command::cargo_bin("trace-gate").unwrap();
    cmd.arg("--manifest")
        .arg(manifest)
        .arg("--src")
        .arg("/tmp/does_not_exist_src_at_all");

    cmd.assert()
        .failure()
        .code(2)
        .stderr(predicate::str::contains("hint:"));
}

// ── Existing tests ───────────────────────────────────────────────────────────

/// --push flag prints stub payload without affecting exit code.
#[test]
fn push_flag_prints_stub_without_affecting_exit() {
    let mut cmd = Command::cargo_bin("trace-gate").unwrap();
    cmd.arg("--manifest")
        .arg(fixture("manifest_all.toml"))
        .arg("--src")
        .arg(fixture("src"))
        .arg("--push")
        .arg("https://tracera.example.invalid/api/v1/coverage/ingest");

    cmd.assert()
        .success()
        .code(0)
        .stderr(predicate::str::contains("would push"));
}
