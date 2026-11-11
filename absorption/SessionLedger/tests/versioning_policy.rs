//! Hermetic `SelfCheck` for C11 L119 versioning policy / tagged CHANGELOG.
//! Local: `pwsh ./scripts/versioning-policy-check.ps1 -SelfCheck`

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn versioning_policy_self_check_validates_anchors() {
    let script = repo_root().join("scripts/versioning-policy-check.ps1");
    assert!(script.is_file(), "expected versioning policy check at {}", script.display());
    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|e| panic!("spawn pwsh: {e}"));
    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "versioning-policy-check.ps1 failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Versioning policy SelfCheck passed"),
        "expected success line, got:\n{stdout}"
    );
}
