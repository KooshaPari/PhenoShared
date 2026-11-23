// SPDX-FileCopyrightText: 2026 Phenotype (fork addition)
// SPDX-License-Identifier: Apache-2.0

// Phenotype fork (0.3.1-hc.1): the native Windows binary is a real command
// surface, not a refusal. These tests run the built executable on Windows and
// hold it to the two halves that need no live Herdr Core: it starts, and it
// writes the documents it promises.
#![cfg(windows)]

use std::path::Path;
use std::process::{Command, Output};

use serde_json::Value;

struct Sandbox {
    _dir: tempfile::TempDir,
    config: std::path::PathBuf,
    state: std::path::PathBuf,
    socket: std::path::PathBuf,
}

impl Sandbox {
    fn new() -> Self {
        let dir = tempfile::tempdir().expect("temp dir");
        let root = dir.path();
        let config = root.join("config");
        let state = root.join("state");
        std::fs::create_dir_all(&config).expect("config dir");
        std::fs::create_dir_all(&state).expect("state dir");
        Self {
            socket: root.join("herdr-core.pipe"),
            config,
            state,
            _dir: dir,
        }
    }

    fn run(&self, args: &[&str]) -> Output {
        let mut command = Command::new(env!("CARGO_BIN_EXE_herdr-revive"));
        command
            .args(args)
            .env("HERDR_PLUGIN_CONFIG_DIR", &self.config)
            .env("HERDR_PLUGIN_STATE_DIR", &self.state)
            .env("HERDR_SOCKET_PATH", &self.socket);
        command.output().expect("the binary runs")
    }
}

fn json(output: &Output) -> Value {
    let stdout = String::from_utf8_lossy(&output.stdout);
    serde_json::from_str(&stdout).unwrap_or_else(|e| {
        panic!(
            "expected a JSON document, got {stdout:?} (error: {e}, stderr: {:?})",
            String::from_utf8_lossy(&output.stderr)
        )
    })
}

#[test]
fn the_windows_binary_offers_the_restore_surface() {
    let sandbox = Sandbox::new();
    let output = sandbox.run(&["--help"]);
    assert!(
        output.status.success(),
        "help failed: {:?}",
        String::from_utf8_lossy(&output.stderr)
    );
    let help = String::from_utf8_lossy(&output.stdout).to_ascii_lowercase();
    for action in ["save", "list", "preview", "restore", "config", "status"] {
        assert!(help.contains(action), "help is missing {action}: {help}");
    }
    assert!(
        !help.contains("not supported"),
        "the Windows build still refuses instead of acting: {help}"
    );
}

#[test]
fn config_prints_the_default_configuration() {
    let sandbox = Sandbox::new();
    let output = sandbox.run(&["--json", "config"]);
    assert!(
        output.status.success(),
        "config failed: {:?}",
        String::from_utf8_lossy(&output.stderr)
    );
    let document = json(&output);
    let text = document["config"].as_str().expect("config text");
    assert!(
        text.contains("auto_restore") && text.contains("retention"),
        "config text is not the real document: {text}"
    );
}

#[test]
fn list_reports_an_empty_store_as_an_empty_list() {
    let sandbox = Sandbox::new();
    let output = sandbox.run(&["--json", "list"]);
    assert!(
        output.status.success(),
        "list failed: {:?}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(json(&output)["snapshots"], Value::Array(Vec::new()));
}

#[test]
fn a_missing_socket_is_named_rather_than_guessed() {
    let sandbox = Sandbox::new();
    let output = sandbox.run(&["list"]);
    assert!(output.status.success(), "list needs no socket");

    let mut command = Command::new(env!("CARGO_BIN_EXE_herdr-revive"));
    command
        .args(["list"])
        .env("HERDR_PLUGIN_CONFIG_DIR", &sandbox.config)
        .env("HERDR_PLUGIN_STATE_DIR", &sandbox.state)
        .env_remove("HERDR_SOCKET_PATH");
    let output = command.output().expect("the binary runs");
    assert!(!output.status.success(), "a missing socket must fail");
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("HERDR_SOCKET_PATH"),
        "the failure must name the missing setting: {stderr}"
    );
}

#[test]
fn restore_without_a_saved_snapshot_fails_before_touching_anything() {
    let sandbox = Sandbox::new();
    let output = sandbox.run(&["restore", "--dry-run"]);
    assert!(
        !output.status.success(),
        "restore with no snapshot must fail"
    );
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        !stderr.trim().is_empty(),
        "a refused restore must say why it refused"
    );
    assert!(
        !Path::new(&sandbox.state).join("touched").exists(),
        "nothing should be written by a refused restore"
    );
}
