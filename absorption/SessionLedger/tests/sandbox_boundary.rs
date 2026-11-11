//! Hermetic `SelfCheck` for docs/ops/sandbox-boundary.md anchors (C04 L40).
//!
//! Local: `pwsh ./scripts/sandbox-boundary-check.ps1 -SelfCheck`

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn sandbox_boundary_doc_self_check_validates_anchors() {
    let script = repo_root().join("scripts/sandbox-boundary-check.ps1");
    assert!(script.is_file(), "expected sandbox boundary check script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "sandbox-boundary-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Sandbox boundary SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
