//! Hermetic `SelfCheck` for docs/ops/signing-readiness.md hard blocking CI (C11 L112).
//!
//! Local: `pwsh ./scripts/signing-readiness-check.ps1 -SelfCheck`
//!
//! Does not access Authenticode or notarization credentials — the hard PR/release
//! gate stays in `.github/workflows/signing-hard.yml` and `release.yml`.

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn signing_hard_doc_self_check_validates_anchors() {
    let script = repo_root().join("scripts/signing-readiness-check.ps1");
    assert!(script.is_file(), "missing {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "signing-readiness-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Platform signing readiness hard SelfCheck passed"),
        "expected hard SelfCheck success line, got:\n{stdout}"
    );
}
