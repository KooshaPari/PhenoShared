//! Hermetic `SelfCheck` for docs/ops/jemalloc-default-on.md blocking default-on CI (C00 L8).
//!
//! Local: `pwsh ./scripts/jemalloc-default-on-check.ps1 -SelfCheck`
//!
//! Platform default builds stay in `.github/workflows/jemalloc-default-on-hard.yml`.

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn jemalloc_default_on_self_check_validates_policy_and_anchors() {
    let script = repo_root().join("scripts/jemalloc-default-on-check.ps1");
    assert!(script.is_file(), "expected jemalloc-default-on script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "jemalloc-default-on-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Jemalloc default-on hard CI SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
