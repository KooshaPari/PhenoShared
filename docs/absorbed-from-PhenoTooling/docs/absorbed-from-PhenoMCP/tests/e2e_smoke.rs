// SPDX-License-Identifier: MIT OR Apache-2.0

//! End-to-end smoke test for the `pheno-mcp` binary.
//!
//! This test exercises the actual compiled binary the way a real user
//! (or CI pipeline) would: spawn it, capture stdout/stderr/exit code,
//! and assert it starts cleanly. Designed to be fast, deterministic,
//! and dependency-free beyond `std::process`.

use std::io::Read;
use std::path::PathBuf;
use std::process::{Command, Output, Stdio};
use std::time::{Duration, Instant};

fn binary_path() -> PathBuf {
    // cargo places integration-test binaries in target/debug/ alongside
    // the workspace binaries; the test runs after `cargo build` so the
    // artifact is already on disk.
    let mut p = PathBuf::from(env!("CARGO_BIN_EXE_pheno-mcp"));
    if !p.exists() {
        // Fallback: CARGO_MANIFEST_DIR/target/debug/pheno-mcp
        let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        p = manifest.join("target").join("debug").join("pheno-mcp");
    }
    p
}

fn command_output_with_timeout(cmd: &mut Command, timeout: Duration) -> Output {
    let mut child = cmd
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn command");

    let stdout_handle = child.stdout.take().map(|mut stdout| {
        std::thread::spawn(move || {
            let mut buf = Vec::new();
            stdout.read_to_end(&mut buf).ok();
            buf
        })
    });
    let stderr_handle = child.stderr.take().map(|mut stderr| {
        std::thread::spawn(move || {
            let mut buf = Vec::new();
            stderr.read_to_end(&mut buf).ok();
            buf
        })
    });

    let started = Instant::now();
    loop {
        match child.try_wait() {
            Ok(Some(status)) => {
                let stdout = stdout_handle
                    .map(|h| h.join().unwrap_or_default())
                    .unwrap_or_default();
                let stderr = stderr_handle
                    .map(|h| h.join().unwrap_or_default())
                    .unwrap_or_default();
                return Output {
                    status,
                    stdout,
                    stderr,
                };
            }
            Ok(None) => {
                if started.elapsed() >= timeout {
                    let _ = child.kill();
                    let _ = child.wait();
                    panic!("command exceeded timeout of {timeout:?}");
                }
                std::thread::sleep(Duration::from_millis(50));
            }
            Err(e) => panic!("failed to wait on child: {e}"),
        }
    }
}

#[test]
fn pheno_mcp_binary_runs_and_exits_zero() {
    let bin = binary_path();
    assert!(
        bin.exists(),
        "expected compiled binary at {} — run `cargo build` first",
        bin.display()
    );

    let timeout = Duration::from_secs(5);
    let mut cmd = Command::new(&bin);
    cmd.arg("--help")
        .env("NO_COLOR", "1")
        .env("RUST_LOG", "off");
    let out = command_output_with_timeout(&mut cmd, timeout);

    let stderr = String::from_utf8_lossy(&out.stderr);
    let stdout = String::from_utf8_lossy(&out.stdout);

    // --help is a non-error path: exit 0, no panic on stderr.
    assert!(
        out.status.success(),
        "pheno-mcp --help exited with {status:?}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}",
        status = out.status
    );
    assert!(
        !stderr.contains("panicked") && !stderr.contains("error["),
        "pheno-mcp --help emitted panic/error to stderr:\n{stderr}"
    );
}

#[test]
fn pheno_mcp_binary_prints_brand_string() {
    let bin = binary_path();
    assert!(
        bin.exists(),
        "expected compiled binary at {} — run `cargo build` first",
        bin.display()
    );

    let out = Command::new(&bin)
        .env("NO_COLOR", "1")
        .env("RUST_LOG", "off")
        .output()
        .expect("spawn pheno-mcp binary");

    let stdout = String::from_utf8_lossy(&out.stdout);
    // The main.rs prelude prints the brand — this confirms the binary
    // is the one we expect, not some other `pheno-mcp` on PATH.
    assert!(
        stdout.contains("PhenoMCP") || stderr_has_brand(&out.stderr),
        "pheno-mcp stdout did not contain expected brand string.\nstdout: {stdout}"
    );
}

fn stderr_has_brand(stderr: &[u8]) -> bool {
    String::from_utf8_lossy(stderr).contains("PhenoMCP")
}
