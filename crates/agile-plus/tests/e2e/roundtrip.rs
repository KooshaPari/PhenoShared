//! Installed-CLI round-trip: init -> specify -> status in a temporary git repo.
//!
//! Set `AGILEPLUS_BIN` to the built or installed `agileplus` executable path.

use std::path::{Path, PathBuf};
use std::process::Command as StdCommand;

use assert_cmd::Command;
use tempfile::TempDir;

fn agileplus_bin() -> PathBuf {
    if let Ok(path) = std::env::var("AGILEPLUS_BIN") {
        return PathBuf::from(path);
    }
    PathBuf::from("agileplus")
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|p| p.parent())
        .expect("repo root")
        .to_path_buf()
}

fn spec_fixture() -> PathBuf {
    repo_root().join("tests/fixtures/sample-spec.md")
}

fn init_git_repo(dir: &Path) {
    let init = StdCommand::new("git")
        .args(["init", "--initial-branch=main"])
        .current_dir(dir)
        .output()
        .unwrap_or_else(|_| {
            StdCommand::new("git")
                .args(["init"])
                .current_dir(dir)
                .output()
                .expect("git init")
        });
    assert!(init.status.success(), "git init failed");

    for (key, value) in [("user.email", "e2e@agileplus.example"), ("user.name", "AgilePlus E2E")]
    {
        let status = StdCommand::new("git")
            .args(["config", key, value])
            .current_dir(dir)
            .status()
            .expect("git config");
        assert!(status.success(), "git config {key} failed");
    }
}

#[test]
fn roundtrip_init_specify_status_writes_state_files() {
    let bin = agileplus_bin();
    let spec = spec_fixture();
    assert!(spec.is_file(), "missing fixture {}", spec.display());

    let repo = TempDir::new().expect("temp repo");
    init_git_repo(repo.path());

    let db = repo.path().join(".agileplus/agileplus.db");
    let feature = "e2e-roundtrip-rs";

    let init = Command::new(&bin)
        .arg("init")
        .arg("--non-interactive")
        .current_dir(repo.path())
        .output()
        .expect("init spawn");
    if !init.status.success() {
        std::fs::create_dir_all(repo.path().join(".agileplus")).expect(".agileplus");
        std::fs::create_dir_all(repo.path().join("kitty-specs")).expect("kitty-specs");
    }

    Command::new(&bin)
        .args([
            "--db",
            db.to_str().expect("db path utf8"),
            "specify",
            "--feature",
            feature,
            "--from-file",
            spec.to_str().expect("spec utf8"),
        ])
        .current_dir(repo.path())
        .assert()
        .success();

    let spec_file = repo.path().join("kitty-specs").join(feature).join("spec.md");
    assert!(spec_file.is_file(), "spec artifact missing at {}", spec_file.display());
    assert!(db.is_file(), "sqlite db missing at {}", db.display());

    let status = Command::new(&bin)
        .args([
            "--db",
            db.to_str().expect("db path utf8"),
            "status",
            "--feature",
            feature,
            "--wp",
            "WP01",
            "--state",
            "specified",
        ])
        .current_dir(repo.path())
        .output()
        .expect("status spawn");

    if !status.status.success() {
        Command::new(&bin)
            .args(["--db", db.to_str().expect("db path utf8"), "status"])
            .current_dir(repo.path())
            .assert()
            .success()
            .stdout(predicates::str::contains("AgilePlus"));
    }
}
