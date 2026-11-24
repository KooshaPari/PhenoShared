//! Hermetic `SelfCheck` for docs/ops/cross-language-parity.md anchors +
//! structural invariant harness across Python/TS/Go OKF fixtures + Python/Go/TypeScript
//! reference OKF adapter stubs (C08 L75).
//!
//! Local: `pwsh ./scripts/cross-language-parity-check.ps1 -SelfCheck`

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn cross_language_parity_doc_self_check_validates_anchors() {
    let script = repo_root().join("scripts/cross-language-parity-check.ps1");
    assert!(
        script.is_file(),
        "expected cross-language parity check script at {}",
        script.display()
    );

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "cross-language-parity-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Cross-language parity SelfCheck passed")
            && stdout.contains("structural invariant harness")
            && stdout.contains("Python/Go/TypeScript adapter stubs"),
        "expected SelfCheck success with structural harness + Python/Go/TypeScript adapters, got:\n{stdout}"
    );
}
