//! Hermetic `SelfCheck` for C01 L16 Fluent catalog stub (Phase-1).
//!
//! Local: `pwsh ./scripts/fluent-i18n-check.ps1 -SelfCheck`
//!
//! Proves the English + Spanish `.ftl` catalogs, JSON key parity, optional
//! `fluent-catalog` feature wiring, and docs anchors. Does not claim full viewer
//! migration to Fluent.

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn fluent_i18n_self_check_validates_anchors() {
    let script = repo_root().join("scripts/fluent-i18n-check.ps1");
    assert!(script.is_file(), "expected fluent i18n check script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "fluent-i18n-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("fluent i18n SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
