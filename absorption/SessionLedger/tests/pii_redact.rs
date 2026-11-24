//! Hermetic `SelfCheck` for C02 L24 in-tree PII redaction helper.
//!
//! Local: `pwsh ./scripts/pii-redact-check.ps1 -SelfCheck`
//!
//! Proves `src/pii_redact.rs` API anchors, Phase-0 ops doc, and the
//! privacy-hygiene cross-link. Does not claim multi-tenant isolation.

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn pii_redact_self_check_validates_anchors() {
    let script = repo_root().join("scripts/pii-redact-check.ps1");
    assert!(script.is_file(), "expected PII redaction check script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "pii-redact-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("PII redaction SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
