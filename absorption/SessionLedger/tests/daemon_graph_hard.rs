//! Hermetic `SelfCheck` for docs/ops/daemon-graph-hard.md blocking live tokio CI (C00 L7).
//!
//! Local: `pwsh ./scripts/daemon-graph-hard-check.ps1 -SelfCheck`
//!
//! Live tokio graph suite stays in `.github/workflows/daemon-graph-hard.yml`.

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn daemon_graph_hard_self_check_validates_policy_and_anchors() {
    let script = repo_root().join("scripts/daemon-graph-hard-check.ps1");
    assert!(script.is_file(), "expected daemon-graph-hard script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "daemon-graph-hard-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Daemon graph hard CI SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
