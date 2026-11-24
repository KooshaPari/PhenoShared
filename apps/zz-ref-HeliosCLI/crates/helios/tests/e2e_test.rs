//! End-to-end tests for the helios unified binary

use std::process::Command;

fn helios_bin() -> Command {
    // Build the binary first if not already built
    let mut cmd = Command::new("cargo");
    cmd.args(["run", "-p", "helios", "--"]);
    cmd
}

#[test]
fn test_helios_status_subcommand() {
    let output = helios_bin().args(["status"]).output().expect("failed to execute helios status");

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        output.status.success() || stdout.contains("harness"),
        "helios status should succeed or output harness info, got: {}",
        stdout
    );
}

#[test]
fn test_helios_help_shows_subcommands() {
    let output = helios_bin().args(["--help"]).output().expect("failed to execute helios --help");

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("run"), "help should mention 'run' subcommand");
    assert!(stdout.contains("checkpoint"), "help should mention 'checkpoint' subcommand");
    assert!(stdout.contains("rollback"), "help should mention 'rollback' subcommand");
    assert!(stdout.contains("status"), "help should mention 'status' subcommand");
}

#[test]
fn test_helios_run_echo() {
    let output = helios_bin()
        .args(["run", "echo hello from helios"])
        .output()
        .expect("failed to execute helios run");

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.contains("hello from helios"),
        "helios run should execute the command and capture output, got: {}",
        stdout
    );
}

#[test]
fn test_helios_run_with_working_dir() {
    let output = helios_bin()
        .args(["run", "--dir", ".", "pwd"])
        .output()
        .expect("failed to execute helios run --dir");

    let stdout = String::from_utf8_lossy(&output.stdout);
    // pwd should output the current directory
    assert!(!stdout.trim().is_empty(), "helios run --dir pwd should output a path");
}

#[test]
fn test_helios_help_shows_record_subcommand() {
    let output = helios_bin().args(["--help"]).output().expect("failed to execute helios --help");

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("record"), "help should mention 'record' subcommand, got: {}", stdout);
}

#[test]
fn test_helios_record_with_missing_script_fails() {
    let output = helios_bin()
        .args(["record", "nonexistent.kla.yaml", "--output", "./test_output"])
        .output()
        .expect("failed to execute helios record");

    // Should fail because the script file doesn't exist
    let stderr = String::from_utf8_lossy(&output.stderr);
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        !output.status.success()
            || stderr.contains("Failed to load script")
            || stdout.contains("Failed to load script"),
        "helios record with missing script should fail, got stdout: {}, stderr: {}",
        stdout,
        stderr
    );
}
