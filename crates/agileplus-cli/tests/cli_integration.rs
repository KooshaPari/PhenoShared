//! Integration tests for the agileplus CLI binary.
//!
//! Uses assert_cmd + tempfile to test the binary end-to-end.

use std::io::{BufRead, BufReader, Read, Write};
use std::net::TcpListener;
use std::path::PathBuf;
use std::sync::mpsc;
use std::time::Duration;

use assert_cmd::Command;
use tempfile::TempDir;

fn fixtures_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
}

/// Initialize a temporary git repo for testing.
fn init_temp_git_repo() -> TempDir {
    let dir = TempDir::new().expect("temp dir");
    std::process::Command::new("git")
        .args(["init", "--initial-branch=main"])
        .current_dir(dir.path())
        .output()
        .unwrap_or_else(|_| {
            // Fall back to older git that doesn't support --initial-branch
            std::process::Command::new("git")
                .args(["init"])
                .current_dir(dir.path())
                .output()
                .expect("git init")
        });
    std::process::Command::new("git")
        .args(["config", "user.email", "test@example.com"])
        .current_dir(dir.path())
        .output()
        .expect("git config email");
    std::process::Command::new("git")
        .args(["config", "user.name", "Test User"])
        .current_dir(dir.path())
        .output()
        .expect("git config name");
    let current = std::process::Command::new("git")
        .args(["branch", "--show-current"])
        .current_dir(dir.path())
        .output()
        .expect("git branch --show-current")
        .stdout;
    if String::from_utf8_lossy(&current).trim() != "main" {
        std::process::Command::new("git")
            .args(["branch", "-M", "main"])
            .current_dir(dir.path())
            .output()
            .expect("rename branch to main");
    }
    let init_commit = std::process::Command::new("git")
        .args([
            "commit",
            "--allow-empty",
            "-m",
            "chore: initialize empty test repo",
        ])
        .current_dir(dir.path())
        .output()
        .expect("initial allow-empty commit");
    assert!(
        init_commit.status.success(),
        "initial allow-empty commit should succeed: {init_commit:?}"
    );
    dir
}

fn spawn_cockpit_recorder(expected_requests: usize) -> (String, mpsc::Receiver<serde_json::Value>) {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind recorder");
    listener
        .set_nonblocking(true)
        .expect("set listener nonblocking");
    let addr = listener.local_addr().expect("recorder addr");
    let (tx, rx) = mpsc::channel();

    std::thread::spawn(move || {
        let deadline = std::time::Instant::now() + Duration::from_secs(20);
        let mut handled = 0usize;
        while handled < expected_requests && std::time::Instant::now() < deadline {
            let (mut stream, _) = match listener.accept() {
                Ok(pair) => pair,
                Err(err) if err.kind() == std::io::ErrorKind::WouldBlock => {
                    std::thread::sleep(Duration::from_millis(25));
                    continue;
                }
                Err(err) => panic!("accept recorder connection: {err}"),
            };
            stream.set_nonblocking(false).expect("set stream blocking");
            stream
                .set_read_timeout(Some(Duration::from_secs(5)))
                .expect("set read timeout");

            let mut request_reader = BufReader::new(&mut stream);
            let mut headers = String::new();
            let mut content_length = 0usize;

            loop {
                let bytes = request_reader
                    .read_line(&mut headers)
                    .expect("read cockpit request headers");
                if bytes == 0 {
                    break;
                }

                if headers == "\r\n" || headers == "\n" {
                    break;
                }

                if headers.to_ascii_lowercase().starts_with("content-length:") {
                    let value = headers["content-length:".len()..].trim();
                    content_length = value.parse::<usize>().expect("content-length");
                }

                headers.clear();
            }

            let mut body = vec![0_u8; content_length];
            if content_length > 0 {
                request_reader
                    .read_exact(&mut body)
                    .expect("cockpit payload");
            }
            let payload: serde_json::Value =
                serde_json::from_slice(&body).expect("cockpit payload json");
            tx.send(payload).expect("send payload");
            stream
                .write_all(b"HTTP/1.1 200 OK\r\ncontent-length: 0\r\n\r\n")
                .expect("write response");
            handled += 1;
        }
    });

    (format!("http://{addr}/api/dashboard/cockpit"), rx)
}

#[test]
fn help_prints_usage() {
    Command::cargo_bin("agileplus")
        .unwrap()
        .arg("--help")
        .assert()
        .success()
        .stdout(predicates::str::contains("Spec-driven development engine"));
}

#[test]
fn init_docs_native_writes_config_and_directories() {
    let dir = TempDir::new().expect("temp dir");

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "init",
            "--layout",
            "docs-native",
            "--with-hooks",
            "--with-substrate",
            "--with-tracaera",
        ])
        .current_dir(dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("docs-native layout initialized"));

    let config = std::fs::read_to_string(dir.path().join(".agileplus").join("config.toml"))
        .expect("read agileplus config");
    assert!(config.contains(r#"artifact_root = "docs""#));
    assert!(config.contains(r#"spec_root = "docs/specs""#));
    assert!(config.contains(r#"machine_state = ".agileplus/agileplus.db""#));
    assert!(config.contains("hooks = true"));
    assert!(config.contains("substrate = true"));
    assert!(config.contains("tracaera = true"));
    assert!(dir.path().join("docs").join("specs").is_dir());
    assert!(dir.path().join("docs").join("traces").is_dir());
    assert!(dir.path().join(".agileplus").join("exports").is_dir());
    assert!(dir.path().join(".agileplus").join("hooks").is_dir());
}

#[test]
fn migrate_artifacts_copies_legacy_specs_and_exports_idempotently() {
    let dir = TempDir::new().expect("temp dir");
    let legacy_spec = dir
        .path()
        .join("specs")
        .join("legacy-feature")
        .join("spec.md");
    std::fs::create_dir_all(legacy_spec.parent().expect("legacy spec parent"))
        .expect("create legacy spec parent");
    std::fs::write(&legacy_spec, "# Legacy Feature\n\nFR-LEGACY-001\n").expect("write legacy spec");
    std::fs::write(dir.path().join("events.jsonl"), "{\"event\":\"legacy\"}\n")
        .expect("write root export");

    Command::cargo_bin("agileplus")
        .unwrap()
        .arg("migrate-artifacts")
        .current_dir(dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("Artifact migration completed"))
        .stdout(predicates::str::contains("Copied:  2"));

    assert!(dir
        .path()
        .join("docs")
        .join("specs")
        .join("legacy-feature")
        .join("spec.md")
        .is_file());
    assert!(dir
        .path()
        .join(".agileplus")
        .join("exports")
        .join("events.jsonl")
        .is_file());
    let report_path = dir
        .path()
        .join("docs")
        .join("reports")
        .join("artifact-migration-report.md");
    let first_report = std::fs::read_to_string(&report_path).expect("read migration report");
    assert!(first_report.contains("Copied: 2"));

    Command::cargo_bin("agileplus")
        .unwrap()
        .arg("migrate-artifacts")
        .current_dir(dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("Skipped: 2"));

    let second_report = std::fs::read_to_string(&report_path).expect("read second report");
    assert!(second_report.contains("Copied: 0"));
    assert!(second_report.contains("Skipped unchanged: 2"));
}

#[test]
fn migrate_artifacts_copies_nested_plans_recursively() {
    let dir = TempDir::new().expect("temp dir");
    let nested_plan = dir
        .path()
        .join("plans")
        .join("release")
        .join("q1")
        .join("plan.md");
    std::fs::create_dir_all(nested_plan.parent().expect("nested plan parent"))
        .expect("create nested plan parent");
    std::fs::write(&nested_plan, "# Q1 Release Plan\n").expect("write nested plan");
    std::fs::write(
        dir.path().join("plans").join("release").join("tasks.md"),
        "# Tasks\n- ship feature\n",
    )
    .expect("write sibling plan");

    Command::cargo_bin("agileplus")
        .unwrap()
        .arg("migrate-artifacts")
        .current_dir(dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("Copied:  2"));

    assert!(dir
        .path()
        .join("docs")
        .join("plans")
        .join("release")
        .join("q1")
        .join("plan.md")
        .is_file());
    assert!(dir
        .path()
        .join("docs")
        .join("plans")
        .join("release")
        .join("tasks.md")
        .is_file());
}

#[test]
fn migrate_artifacts_respects_custom_report_path_with_parent_creation() {
    let dir = TempDir::new().expect("temp dir");
    let legacy_spec = dir
        .path()
        .join("specs")
        .join("release-feature")
        .join("spec.md");
    std::fs::create_dir_all(legacy_spec.parent().expect("legacy spec parent"))
        .expect("create legacy spec parent");
    std::fs::write(&legacy_spec, "# Release Feature\n\nFR-001\n").expect("write legacy spec");

    let report_path = dir
        .path()
        .join("artifacts")
        .join("reports")
        .join("custom-migration-report.md");

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "migrate-artifacts",
            "--report",
            report_path.to_str().unwrap(),
        ])
        .current_dir(dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("Artifact migration completed"));

    let report_content = std::fs::read_to_string(&report_path).expect("read custom report");
    assert!(report_path.parent().expect("report parent").is_dir());
    assert!(report_content.contains("Copied: 1"));
    assert!(!dir
        .path()
        .join("docs")
        .join("reports")
        .join("artifact-migration-report.md")
        .exists());
}

#[test]
fn migrate_artifacts_rewrites_targets_when_source_content_changes() {
    let dir = TempDir::new().expect("temp dir");
    let legacy_spec = dir
        .path()
        .join("specs")
        .join("legacy-feature")
        .join("spec.md");
    std::fs::create_dir_all(legacy_spec.parent().expect("legacy spec parent"))
        .expect("create legacy spec parent");
    std::fs::write(&legacy_spec, "# Legacy Feature v1\n").expect("write legacy spec v1");

    Command::cargo_bin("agileplus")
        .unwrap()
        .arg("migrate-artifacts")
        .current_dir(dir.path())
        .assert()
        .success();

    let target = dir
        .path()
        .join("docs")
        .join("specs")
        .join("legacy-feature")
        .join("spec.md");
    let second_report = dir
        .path()
        .join("artifacts")
        .join("reports")
        .join("migration-report.md");
    std::fs::write(&legacy_spec, "# Legacy Feature v2\n").expect("write legacy spec v2");

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "migrate-artifacts",
            "--report",
            second_report.to_str().unwrap(),
        ])
        .current_dir(dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("Copied:  1"));

    let migrated = std::fs::read_to_string(&target).expect("read migrated spec");
    let second_content = std::fs::read_to_string(&second_report).expect("read second report");
    assert_eq!(migrated, "# Legacy Feature v2\n");
    assert!(second_content.contains("Copied: 1"));
    assert!(second_content.contains("Skipped unchanged: 0"));
}

#[test]
fn migrate_artifacts_handles_mixed_brownfield_exports_with_scope_guardrails() {
    let dir = TempDir::new().expect("temp dir");
    let plan_path = dir.path().join("plans").join("feature-plan.md");
    std::fs::create_dir_all(dir.path().join("plans")).expect("create plan root");
    std::fs::write(&plan_path, "# Plan\n").expect("write legacy plan");
    std::fs::write(dir.path().join("specs").join("spec.md"), "# Spec\n")
        .expect_err("spec dir not present");

    std::fs::create_dir_all(dir.path().join("specs").join("spec")).expect("create spec dir");
    std::fs::write(
        dir.path().join("specs").join("spec").join("spec.md"),
        "# Spec\n",
    )
    .expect("write legacy spec");

    std::fs::write(dir.path().join("events.jsonl"), "{\"event\":\"legacy\"}\n")
        .expect("write events export");
    std::fs::write(
        dir.path().join("evidence_ledger.jsonl"),
        "{\"ledger\":\"legacy\"}\n",
    )
    .expect("write evidence export");
    std::fs::write(
        dir.path().join("package.json"),
        r#"{"name":"should-not-migrate"}"#,
    )
    .expect("write unrelated export");

    Command::cargo_bin("agileplus")
        .unwrap()
        .arg("migrate-artifacts")
        .current_dir(dir.path())
        .assert()
        .success();

    let exports_dir = dir.path().join(".agileplus").join("exports");
    let exported = std::fs::read_dir(&exports_dir).expect("read exports dir");
    let exported_files: Vec<_> = exported
        .filter_map(|entry| entry.ok())
        .filter_map(|entry| entry.file_name().into_string().ok())
        .collect::<Vec<_>>();
    assert!(exported_files.contains(&"events.jsonl".to_string()));
    assert!(exported_files.contains(&"evidence_ledger.jsonl".to_string()));
    assert!(!exported_files.contains(&"package.json".to_string()));
}

#[test]
fn specify_help_prints_subcommand_usage() {
    Command::cargo_bin("agileplus")
        .unwrap()
        .args(["specify", "--help"])
        .assert()
        .success()
        .stdout(predicates::str::contains("feature"));
}

#[test]
fn research_help_prints_subcommand_usage() {
    Command::cargo_bin("agileplus")
        .unwrap()
        .args(["research", "--help"])
        .assert()
        .success()
        .stdout(predicates::str::contains("feature"));
}

#[test]
fn events_help_prints_subcommand_usage() {
    Command::cargo_bin("agileplus")
        .unwrap()
        .args(["events", "--help"])
        .assert()
        .success()
        .stdout(predicates::str::contains("since"));
}

#[test]
fn events_since_filters_stub_events() {
    Command::cargo_bin("agileplus")
        .unwrap()
        .args(["events", "--since", "2026-03-03", "--format", "json"])
        .assert()
        .success()
        .stdout(predicates::str::contains("[]"));
}

#[test]
fn implement_emits_cockpit_updates_to_configured_endpoint() {
    let repo_dir = init_temp_git_repo();
    let db_path = repo_dir.path().join(".agileplus").join("agileplus.db");
    let spec_path = fixtures_dir().join("sample-spec.md");
    let (cockpit_url, rx) = spawn_cockpit_recorder(2);

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "specify",
            "--feature",
            "dogfood-flow",
            "--from-file",
            spec_path.to_str().unwrap(),
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success();

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "research",
            "--feature",
            "dogfood-flow",
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success();

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "plan",
            "--feature",
            "dogfood-flow",
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success();

    Command::cargo_bin("agileplus")
        .unwrap()
        .env("SUBSTRATE_BIN", "true")
        .env("AGILEPLUS_COCKPIT_URL", &cockpit_url)
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "implement",
            "--feature",
            "dogfood-flow",
            "--wp",
            "WP01",
            "--max-review-cycles",
            "1",
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("WP01 approved!"))
        .stdout(predicates::str::contains(
            "Implement complete: 1/1 WPs done.",
        ));

    let first = rx
        .recv_timeout(Duration::from_secs(5))
        .expect("first cockpit update");
    let second = rx
        .recv_timeout(Duration::from_secs(5))
        .expect("second cockpit update");

    assert_eq!(first["session_id"], "dogfood-flow");
    assert_eq!(first["phase"], "running");
    assert_eq!(first["progress"], 0.0);
    assert!(first["summary"]
        .as_str()
        .expect("running summary")
        .contains("WP01"));

    assert_eq!(second["session_id"], "dogfood-flow");
    assert_eq!(second["phase"], "completed");
    assert_eq!(second["progress"], 1.0);
    assert!(second["summary"]
        .as_str()
        .expect("completed summary")
        .contains("agent completed"));
}

#[test]
fn implement_emits_cockpit_updates_via_substrate_env_alias() {
    let repo_dir = init_temp_git_repo();
    let db_path = repo_dir.path().join(".agileplus").join("agileplus.db");
    let spec_path = fixtures_dir().join("sample-spec.md");
    let (cockpit_url, rx) = spawn_cockpit_recorder(2);

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "specify",
            "--feature",
            "dogfood-flow-alias",
            "--from-file",
            spec_path.to_str().unwrap(),
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success();

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "research",
            "--feature",
            "dogfood-flow-alias",
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success();

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "plan",
            "--feature",
            "dogfood-flow-alias",
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success();

    Command::cargo_bin("agileplus")
        .unwrap()
        .env("SUBSTRATE_BIN", "true")
        .env("SUBSTRATE_COCKPIT_URL", &cockpit_url)
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "implement",
            "--feature",
            "dogfood-flow-alias",
            "--wp",
            "WP01",
            "--max-review-cycles",
            "1",
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success();

    let first = rx
        .recv_timeout(Duration::from_secs(5))
        .expect("first cockpit update");
    let second = rx
        .recv_timeout(Duration::from_secs(5))
        .expect("second cockpit update");

    assert_eq!(first["session_id"], "dogfood-flow-alias");
    assert_eq!(first["phase"], "running");
    assert_eq!(second["session_id"], "dogfood-flow-alias");
    assert_eq!(second["phase"], "completed");
}

#[test]
fn specify_from_file_creates_feature() {
    let repo_dir = init_temp_git_repo();
    let db_path = repo_dir.path().join(".agileplus").join("agileplus.db");
    let spec_path = fixtures_dir().join("sample-spec.md");

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "specify",
            "--feature",
            "test-001",
            "--from-file",
            spec_path.to_str().unwrap(),
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("test-001"));
}

#[test]
fn specify_creates_spec_artifact() {
    let repo_dir = init_temp_git_repo();
    let db_path = repo_dir.path().join(".agileplus").join("agileplus.db");
    let spec_path = fixtures_dir().join("sample-spec.md");

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "specify",
            "--feature",
            "my-feature",
            "--from-file",
            spec_path.to_str().unwrap(),
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success();

    // Verify the spec.md was written
    let spec_file = repo_dir
        .path()
        .join("kitty-specs")
        .join("my-feature")
        .join("spec.md");
    assert!(
        spec_file.exists(),
        "spec.md should have been created at {}",
        spec_file.display()
    );
}

#[test]
fn research_on_nonexistent_feature_runs_pre_specify_mode() {
    let repo_dir = init_temp_git_repo();
    let db_path = repo_dir.path().join(".agileplus").join("agileplus.db");

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "research",
            "--feature",
            "nonexistent-feature",
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("Pre-specify"));
}

#[test]
fn research_after_specify_transitions_to_researched() {
    let repo_dir = init_temp_git_repo();
    let db_path = repo_dir.path().join(".agileplus").join("agileplus.db");
    let spec_path = fixtures_dir().join("sample-spec.md");

    // First specify
    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "specify",
            "--feature",
            "feat-research",
            "--from-file",
            spec_path.to_str().unwrap(),
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success();

    // Then research
    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "research",
            "--feature",
            "feat-research",
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("Researched"));
}

#[test]
fn specify_refinement_detects_no_changes() {
    let repo_dir = init_temp_git_repo();
    let db_path = repo_dir.path().join(".agileplus").join("agileplus.db");
    let spec_path = fixtures_dir().join("sample-spec.md");

    // First specify
    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "specify",
            "--feature",
            "rev-feat",
            "--from-file",
            spec_path.to_str().unwrap(),
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success();

    // Re-run with same file — should detect no changes
    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "specify",
            "--feature",
            "rev-feat",
            "--from-file",
            spec_path.to_str().unwrap(),
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("No changes"));
}

#[test]
fn specify_refinement_writes_diff_artifact() {
    let repo_dir = init_temp_git_repo();
    let db_path = repo_dir.path().join(".agileplus").join("agileplus.db");
    let spec_path = fixtures_dir().join("sample-spec.md");
    let revised_path = fixtures_dir().join("sample-spec-revised.md");

    // Initial specify
    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "specify",
            "--feature",
            "diff-feat",
            "--from-file",
            spec_path.to_str().unwrap(),
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success();

    // Revise with different content
    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "specify",
            "--feature",
            "diff-feat",
            "--from-file",
            revised_path.to_str().unwrap(),
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("updated"));
}

#[test]
fn no_git_repo_shows_helpful_error() {
    let dir = TempDir::new().expect("temp dir");
    let db_path = dir.path().join("test.db");
    let spec_path = fixtures_dir().join("sample-spec.md");

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "specify",
            "--feature",
            "no-git",
            "--from-file",
            spec_path.to_str().unwrap(),
        ])
        .current_dir(dir.path())
        .assert()
        .failure();
}

fn write_traceability_fixture(repo_dir: &TempDir, include_test_marker: bool) {
    let spec_dir = repo_dir.path().join("kitty-specs").join("trace-feature");
    std::fs::create_dir_all(&spec_dir).expect("create spec dir");
    std::fs::write(
        spec_dir.join("spec.md"),
        "# Trace Feature\n\n- FR-001: traceable behavior\n",
    )
    .expect("write spec");

    let src_dir = repo_dir.path().join("src");
    std::fs::create_dir_all(&src_dir).expect("create src dir");
    std::fs::write(
        src_dir.join("lib.rs"),
        "//! AGP-REQ(FR-001)\n\npub fn traceable() -> bool { true }\n",
    )
    .expect("write source marker");

    if include_test_marker {
        let test_dir = repo_dir.path().join("tests");
        std::fs::create_dir_all(&test_dir).expect("create tests dir");
        std::fs::write(
            test_dir.join("trace_test.rs"),
            "//! AGP-REQ(FR-001)\n\n#[test]\nfn traceable_test() { assert!(true); }\n",
        )
        .expect("write test marker");
    }
}

#[test]
fn hooks_verify_fails_when_traceability_is_broken() {
    let repo_dir = init_temp_git_repo();
    let db_path = repo_dir.path().join(".agileplus").join("agileplus.db");
    write_traceability_fixture(&repo_dir, false);

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "hooks",
            "verify",
            "--feature",
            "trace-feature",
        ])
        .current_dir(repo_dir.path())
        .assert()
        .failure()
        .stderr(predicates::str::contains("missing_test_marker"));
}

#[test]
fn hooks_verify_passes_when_traceability_is_complete() {
    let repo_dir = init_temp_git_repo();
    let db_path = repo_dir.path().join(".agileplus").join("agileplus.db");
    write_traceability_fixture(&repo_dir, true);

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "hooks",
            "verify",
            "--feature",
            "trace-feature",
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains(
            "Traceability verification passed",
        ));
}

#[test]
fn hooks_install_and_uninstall_manage_hook_template() {
    let repo_dir = init_temp_git_repo();
    let db_path = repo_dir.path().join(".agileplus").join("agileplus.db");
    let hook_path = repo_dir
        .path()
        .join(".agileplus")
        .join("hooks")
        .join("pre-commit");

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "hooks",
            "install",
            "--output",
            hook_path.to_str().unwrap(),
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("hook template written"));

    let hook_content = std::fs::read_to_string(&hook_path).expect("read hook template");
    assert!(hook_content.contains("AGILEPLUS_FEATURE"));
    assert!(hook_content.contains("agileplus hooks verify --feature"));

    Command::cargo_bin("agileplus")
        .unwrap()
        .args([
            "--db",
            db_path.to_str().unwrap(),
            "hooks",
            "uninstall",
            "--path",
            hook_path.to_str().unwrap(),
        ])
        .current_dir(repo_dir.path())
        .assert()
        .success()
        .stdout(predicates::str::contains("hook removed"));

    assert!(!hook_path.exists(), "hook template should be removed");
}
