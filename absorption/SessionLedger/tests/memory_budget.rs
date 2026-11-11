//! Contract checks for the L8 RSS / memory-budget smoke.

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn memory_budget_config_exposes_positive_ceiling() {
    let path = repo_root().join("docs/ops/memory-budget.json");
    let raw = std::fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    let value: serde_json::Value = serde_json::from_str(&raw)
        .unwrap_or_else(|error| panic!("parse {}: {error}", path.display()));

    assert_eq!(
        value.get("schema").and_then(serde_json::Value::as_str),
        Some("sessionledger.memory-budget.v1")
    );

    let ceiling = value
        .get("ingest_rss_ceiling_bytes")
        .and_then(serde_json::Value::as_u64)
        .expect("ingest_rss_ceiling_bytes must be a positive integer");
    assert!(ceiling > 0, "ceiling must be positive");
    assert!(
        ceiling >= 64 * 1024 * 1024,
        "ceiling should stay generous for debug ingest smoke (got {ceiling})"
    );
}

#[test]
fn rss_budget_script_self_check_parses_args_and_ceiling() {
    let script = repo_root().join("scripts/rss-budget-check.ps1");
    assert!(script.is_file(), "missing {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for self-check: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "rss-budget-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Self-check passed"),
        "expected self-check success line, got:\n{stdout}"
    );
    assert!(stdout.contains("Ceiling:"), "expected ceiling echo, got:\n{stdout}");
}
