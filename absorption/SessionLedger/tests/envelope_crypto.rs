//! Hermetic `SelfCheck` for docs/ops/crypto-inventory.md hard envelope-crypto CI (C02 L22).
//!
//! Local: `pwsh ./scripts/envelope-crypto-check.ps1 -SelfCheck`
//!
//! Requires `--features envelope-crypto` (marker feature for the soft `src/envelope.rs` helper).

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn envelope_crypto_doc_self_check_validates_anchors() {
    let script = repo_root().join("scripts/envelope-crypto-check.ps1");
    assert!(script.is_file(), "expected envelope-crypto check script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "envelope-crypto-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Envelope-crypto SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
