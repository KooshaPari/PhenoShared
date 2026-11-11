//! Hermetic `SelfCheck` for soft Alertmanager packaging evidence (C05).
//!
//! Local: `pwsh ./scripts/alertmanager-soft-check.ps1 -SelfCheck`
//!
//! Does not start Alertmanager or claim live webhook traffic.

use std::path::PathBuf;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[cfg(target_os = "windows")]
#[test]
fn alertmanager_soft_doc_self_check_validates_anchors() {
    let script = repo_root().join("scripts/alertmanager-soft-check.ps1");
    assert!(script.is_file(), "missing {}", script.display());

    let output = std::process::Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "alertmanager-soft-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Soft Alertmanager SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}

#[cfg(not(target_os = "windows"))]
#[test]
fn alertmanager_soft_doc_self_check_validates_anchors() {
    let script = repo_root().join("scripts/alertmanager-soft-check.ps1");
    let doc = repo_root().join("docs/ops/alertmanager-soft.md");
    assert!(script.is_file(), "missing {}", script.display());
    assert!(doc.is_file(), "missing {}", doc.display());

    let raw = std::fs::read_to_string(&doc).expect("read alertmanager-soft.md");
    assert!(
        raw.contains("pwsh ./scripts/alertmanager-soft-check.ps1 -SelfCheck"),
        "missing expected self-check invocation in {}",
        doc.display()
    );
}
