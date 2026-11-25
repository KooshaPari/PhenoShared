//! Smoke: `sl-daemon completions` emits non-empty clap_complete scripts.

use std::process::Command;

fn sl_daemon_bin() -> Command {
    // Prefer the binary under test when cargo provides it.
    if let Ok(path) = std::env::var("CARGO_BIN_EXE_sl-daemon") {
        return Command::new(path);
    }
    let mut cmd = Command::new("cargo");
    cmd.args(["run", "-q", "-p", "sl-daemon", "--"]);
    cmd
}

#[test]
fn completions_emit_for_common_shells() {
    for shell in ["bash", "zsh", "fish", "powershell"] {
        let output = sl_daemon_bin()
            .args(["completions", shell])
            .output()
            .unwrap_or_else(|err| panic!("failed to run completions {shell}: {err}"));
        assert!(
            output.status.success(),
            "completions {shell} exited {:?}: {}",
            output.status.code(),
            String::from_utf8_lossy(&output.stderr)
        );
        let stdout = String::from_utf8_lossy(&output.stdout);
        assert!(
            stdout.len() > 200,
            "completions {shell} output too short ({} bytes)",
            stdout.len()
        );
        assert!(
            stdout.contains("sl-daemon") || stdout.contains("SlDaemon"),
            "completions {shell} missing binary name marker"
        );
    }
}
