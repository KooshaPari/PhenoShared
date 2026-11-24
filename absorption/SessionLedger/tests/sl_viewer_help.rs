//! Hermetic `SelfCheck` for docs/ops/sl-viewer-help.md blocking CLI help CI (C01/C09).
//!
//! Local: `pwsh ./scripts/sl-viewer-help-check.ps1 -SelfCheck`

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn sl_viewer_help_self_check_validates_policy_and_anchors() {
    let script = repo_root().join("scripts/sl-viewer-help-check.ps1");
    assert!(script.is_file(), "expected sl-viewer-help script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "sl-viewer-help-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("sl-viewer help hard CI SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
