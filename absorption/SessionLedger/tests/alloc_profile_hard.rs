//! Hermetic `SelfCheck` for docs/ops/alloc-profile.md hard blocking dhat CI (C00 L8).
//!
//! Local: `pwsh ./scripts/alloc-profile-check.ps1 -SelfCheck`
//!
//! Does not compile `dhat` — the hard PR dhat smoke stays in
//! `.github/workflows/alloc-profile-hard.yml`.

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn alloc_profile_hard_doc_self_check_validates_anchors() {
    let script = repo_root().join("scripts/alloc-profile-check.ps1");
    assert!(script.is_file(), "missing {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "alloc-profile-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Alloc profile hard CI SelfCheck passed"),
        "expected hard SelfCheck success line, got:\n{stdout}"
    );
}
