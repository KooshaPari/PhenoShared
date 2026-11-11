//! Hermetic `SelfCheck` for shuttle permutation checker anchors (C00 L7).
//!
//! Local: `pwsh ./scripts/shuttle-permutation-check.ps1 -SelfCheck`
//! Does not build or run the shuttle crate — safe under default Windows `cargo test`.
//! Full tokio broadcast / daemon graph ports remain unpaid.

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn shuttle_permutation_doc_self_check_validates_anchors() {
    let script = repo_root().join("scripts/shuttle-permutation-check.ps1");
    assert!(script.is_file(), "expected shuttle permutation check script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "shuttle-permutation-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Shuttle permutation SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
