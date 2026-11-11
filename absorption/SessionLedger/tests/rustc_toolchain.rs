//! Hermetic `SelfCheck` for exact rustc toolchain pin (C06 L60).
//!
//! Local: `pwsh ./scripts/rustc-toolchain-check.ps1 -SelfCheck`

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn rustc_toolchain_pin_self_check_validates_exact_channel() {
    let script = repo_root().join("scripts/rustc-toolchain-check.ps1");
    assert!(script.is_file(), "expected rustc toolchain check script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "rustc-toolchain-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Exact rustc toolchain pin SelfCheck passed"),
        "expected SelfCheck success line, got:\n{stdout}"
    );
}
