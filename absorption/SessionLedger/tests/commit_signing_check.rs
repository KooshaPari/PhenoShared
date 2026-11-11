//! Hermetic `SelfCheck` for bounded commit-signing header scan (C04 L34).
//!
//! Local: `pwsh ./scripts/commit-signing-check.ps1 -SelfCheck`

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn commit_signing_check_self_check_validates_bounded_header_scan() {
    let script = repo_root().join("scripts/commit-signing-check.ps1");
    assert!(script.is_file(), "expected commit-signing check script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "commit-signing-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Commit signing check SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
