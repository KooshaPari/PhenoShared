//! Hermetic `SelfCheck` for docs/ops/crypto-inventory.md anchors (C02 L22).
//!
//! Local: `pwsh ./scripts/crypto-inventory-check.ps1 -SelfCheck`
//!
//! Covers inventory + Phase-0 KMS/at-rest deferred vs recommended deploy
//! guidance (no in-tree KMS implementation).

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn crypto_inventory_doc_self_check_validates_anchors() {
    let script = repo_root().join("scripts/crypto-inventory-check.ps1");
    assert!(script.is_file(), "expected crypto inventory check script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "crypto-inventory-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Crypto inventory SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
