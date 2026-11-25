//! L8 alloc-profile hermetic wiring: JSON SSOT + script `SelfCheck`.
//!
//! The optional `dhat` heap measurement lives in `tests/alloc_profile_dhat.rs`
//! (`--features alloc-profile`). Default CI graphs exercise only this file.

use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn load_profile() -> (u64, u64) {
    let path = repo_root().join("docs/ops/alloc-profile.json");
    let raw = std::fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    let value: serde_json::Value = serde_json::from_str(&raw)
        .unwrap_or_else(|error| panic!("parse {}: {error}", path.display()));

    assert_eq!(
        value.get("schema").and_then(serde_json::Value::as_str),
        Some("sessionledger.alloc-profile.v1")
    );
    assert_eq!(value.get("profiler").and_then(serde_json::Value::as_str), Some("dhat"));

    let max_bytes = value
        .get("max_bytes_ceiling")
        .and_then(serde_json::Value::as_u64)
        .expect("max_bytes_ceiling must be a positive integer");
    let total_blocks = value
        .get("total_blocks_ceiling")
        .and_then(serde_json::Value::as_u64)
        .expect("total_blocks_ceiling must be a positive integer");

    assert!(max_bytes > 0, "max_bytes_ceiling must be positive");
    assert!(total_blocks > 0, "total_blocks_ceiling must be positive");
    (max_bytes, total_blocks)
}

#[test]
fn alloc_profile_config_exposes_positive_ceilings() {
    let (max_bytes, total_blocks) = load_profile();
    assert!(
        max_bytes >= 1024 * 1024,
        "max_bytes ceiling should stay >= 1 MiB for debug smoke (got {max_bytes})"
    );
    assert!(
        total_blocks >= 1_000,
        "total_blocks ceiling should stay generous (got {total_blocks})"
    );
}

#[test]
fn alloc_profile_script_self_check_parses_args_and_ceilings() {
    let script = repo_root().join("scripts/alloc-profile-check.ps1");
    assert!(script.is_file(), "missing {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output();

    match output {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let stderr = String::from_utf8_lossy(&output.stderr);
            assert!(
                output.status.success(),
                "alloc-profile-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
            );
            assert!(
                stdout.contains("Self-check passed"),
                "expected self-check success line, got:\n{stdout}"
            );
            assert!(
                stdout.contains("Max bytes ceiling:"),
                "expected max bytes ceiling echo, got:\n{stdout}"
            );
            assert!(
                stdout.contains("Total blocks ceiling:"),
                "expected total blocks ceiling echo, got:\n{stdout}"
            );
            assert!(stdout.contains("Profiler: dhat"), "expected profiler echo, got:\n{stdout}");
        }
        Err(error) => {
            // On non-Windows targets, a `NotFound` error means pwsh isn't
            // installed — fall back to the portable SelfCheck. Any other
            // I/O error (permission, broken pipe, etc.) is treated as a
            // hard failure since it likely means the test environment is
            // misconfigured (e.g., spawn denial, missing CWD). Windows has
            // no portable fallback path, so any spawn failure is fatal.
            if cfg!(target_os = "windows") {
                panic!("failed to spawn pwsh for self-check: {error}");
            } else if error.kind() == std::io::ErrorKind::NotFound {
                let (max_bytes, total_blocks) = load_profile();
                println!(
                    "pwsh unavailable; running portable alloc-profile SelfCheck fallback.\nSelf-check passed\nMax bytes ceiling: {max_bytes}\nTotal blocks ceiling: {total_blocks}\nProfiler: dhat"
                );
                assert!(
                    max_bytes >= 1024 * 1024,
                    "max_bytes ceiling should stay >= 1 MiB for debug smoke (got {max_bytes})"
                );
                assert!(
                    total_blocks >= 1_000,
                    "total_blocks ceiling should stay generous (got {total_blocks})"
                );
            } else {
                panic!("failed to spawn pwsh for self-check (non-NotFound): {error}");
            }
        }
    }
}
