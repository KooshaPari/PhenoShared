//! Hermetic `SelfCheck` for C11 L111 user-initiated update check.
//!
//! Local: `pwsh ./scripts/update-check-check.ps1 -SelfCheck`

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn update_check_self_check_validates_anchors() {
    let script = repo_root().join("scripts/update-check-check.ps1");
    assert!(script.is_file(), "expected update check script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "update-check-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Update check SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
