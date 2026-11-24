//! Hermetic `SelfCheck` for docs/ops/load-macro-gate.md blocking macro-route CI (C08 L73).
//!
//! Local: `pwsh ./scripts/load-macro-gate-check.ps1 -SelfCheck`
//!
//! Live macro-tier daemon smoke stays in `.github/workflows/load-macro-gate-hard.yml`.

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn load_macro_gate_self_check_validates_policy_and_anchors() {
    let script = repo_root().join("scripts/load-macro-gate-check.ps1");
    assert!(script.is_file(), "expected load-macro gate script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "load-macro-gate-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Load macro gate hard CI SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
