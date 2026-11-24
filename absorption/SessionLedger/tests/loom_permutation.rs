//! Hermetic `SelfCheck` for loom permutation checker anchors (C00 L7).
//!
//! Local: `pwsh ./scripts/loom-permutation-check.ps1 -SelfCheck`
//! Does not build or run the loom crate — safe under default Windows `cargo test`.
//! Live tokio ports: `docs/ops/daemon-graph-hard.md`.

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn loom_permutation_doc_self_check_validates_anchors() {
    let script = repo_root().join("scripts/loom-permutation-check.ps1");
    assert!(script.is_file(), "expected loom permutation check script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "loom-permutation-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Loom permutation SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
