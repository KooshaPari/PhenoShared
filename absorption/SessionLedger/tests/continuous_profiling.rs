//! Hermetic `SelfCheck` for continuous profiling agent anchors (C05 L45).
//!
//! Local: `pwsh ./scripts/continuous-profiling-agent.ps1 -SelfCheck`
//!
//! Does not start sl-daemon or open sockets for soft HTTP push.

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

#[test]
fn continuous_profiling_doc_self_check_validates_anchors() {
    let script = repo_root().join("scripts/continuous-profiling-agent.ps1");
    assert!(script.is_file(), "expected continuous profiling agent script at {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for SelfCheck: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "continuous-profiling-agent.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Self-check passed: continuous profiling agent stub is coherent."),
        "expected SelfCheck success line, got:\n{stdout}"
    );
    assert!(
        stdout.contains("http_soft"),
        "expected SelfCheck to mention http_soft push_backend, got:\n{stdout}"
    );
}
