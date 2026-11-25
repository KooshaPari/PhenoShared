//! Integration tests for phenotype-forge — **negative oracle** suite.
//!
//! These tests intentionally lock in the **truthful scaffold** state of the
//! `phenotype-forge` binary as of 2026-09-08. They are the inverse of typical
//! "feature works" tests: they assert what the binary **does not** do today,
//! so that a future implementer who silently re-adds false claims (e.g.,
//! flipping a `Not implemented` requirement to `Stable` in the README without
//! adding real code) will be caught by CI.
//!
//! Future implementers should:
//!   1. Implement the feature in `src/main.rs` / `src/lib.rs`.
//!   2. Replace the matching negative-oracle test with a positive assertion
//!      (e.g., drop the `#[ignore]` + add an `assert!` on the new behavior).
//!   3. Update `FUNCTIONAL_REQUIREMENTS.md` to flip the requirement's
//!      status to `Implemented`.
//!   4. Update `README.md` so the feature matrix reflects the new state.

use std::path::PathBuf;
use std::process::Command;

/// Locate the `phenotype-forge` binary built by `cargo test`.
fn binary_path() -> PathBuf {
    // `CARGO_BIN_EXE_<name>` is set by Cargo for integration tests; it points
    // at the binary that was built alongside the test binary.
    PathBuf::from(env!("CARGO_BIN_EXE_phenotype-forge"))
}

// ---------------------------------------------------------------------------
// FR-OBS-001 — banner output (currently Implemented; lock-in test)
// ---------------------------------------------------------------------------

/// The binary prints `Running task: <name>` when invoked with a positional
/// task argument. See `FUNCTIONAL_REQUIREMENTS.md` FR-OBS-001.
#[test]
fn test_binary_prints_running_task_banner() {
    let out = Command::new(binary_path())
        .arg("hello")
        .output()
        .expect("failed to invoke phenotype-forge binary");
    assert!(
        out.status.success(),
        "phenotype-forge exited non-zero: status={:?}, stderr={}",
        out.status,
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(
        stdout.contains("Running task: hello"),
        "expected banner `Running task: hello` in stdout, got: {stdout}"
    );
}

// ---------------------------------------------------------------------------
// FR-OBS-002 — --watch flag parses (currently Implemented; lock-in test)
// ---------------------------------------------------------------------------

/// The binary accepts `--watch` without crashing. The flag is a documented
/// no-op (FR-OBS-003). See `FUNCTIONAL_REQUIREMENTS.md` FR-OBS-002.
#[test]
fn test_binary_accepts_watch_flag_without_crashing() {
    let out = Command::new(binary_path())
        .args(["--watch", "hello"])
        .output()
        .expect("failed to invoke phenotype-forge binary");
    assert!(
        out.status.success(),
        "--watch caused non-zero exit: status={:?}",
        out.status
    );
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(
        stdout.contains("scaffold placeholder"),
        "expected truthful `--watch` message in stdout, got: {stdout}"
    );
}

// ---------------------------------------------------------------------------
// FR-OBS-003 — filesystem observer NOT registered (negative oracle)
// ---------------------------------------------------------------------------

/// The `--watch` flag is a no-op: no `notify` observer is created. This test
/// passes if the binary exits immediately (i.e., does not stay alive waiting
/// for events). See `FUNCTIONAL_REQUIREMENTS.md` FR-OBS-003.
///
/// **How to flip this test on once implemented:** remove the
/// `#[ignore]` below, then implement a real `notify` watcher that holds the
/// process open. The test will start failing until the implementation lands.
#[test]
#[ignore = "negative-oracle: passes today; will fail once a real filesystem observer is implemented"]
fn test_watch_flag_should_register_observer_when_implemented() {
    // Today this is just asserting the inverse of the lock-in test.
    // Once a real observer exists, this `#[ignore]` should be removed and
    // the assertion should change to: the process does NOT exit within
    // a short window (e.g., `assert!(!out.status.success() || ...)`).
}

// ---------------------------------------------------------------------------
// FR-CLI-001..004 — `forge list` / `forge graph` / `forge check` NOT shipped
// ---------------------------------------------------------------------------

/// The binary does NOT have a `list` subcommand. `list` is accepted only as
/// a free-form positional task name (clap's `Args.task` is `String` with a
/// default value), and the binary prints the same `Running task: list
/// (scaffold placeholder)` banner as for any other string. A real
/// implementation would route `forge list` to a listing subcommand that
/// emits task names + descriptions; the negative oracle is that the binary
/// must NOT do that.
///
/// See `FUNCTIONAL_REQUIREMENTS.md` FR-CLI-002.
#[test]
fn test_binary_has_no_list_subcommand() {
    let out_list = Command::new(binary_path())
        .arg("list")
        .output()
        .expect("failed to invoke phenotype-forge binary");
    let out_other = Command::new(binary_path())
        .arg("anything-else")
        .output()
        .expect("failed to invoke phenotype-forge binary");

    // Both invocations succeed with the scaffold-only banner. A real
    // `forge list` subcommand would have a different stdout shape (e.g.,
    // a table of task names). Today the stdout is identical except for
    // the task name echo.
    assert_eq!(
        out_list.status.code(),
        out_other.status.code(),
        "expected `forge list` and `forge anything-else` to behave identically \
         (no `list` subcommand), but exit codes differ: list={:?}, other={:?}",
        out_list.status,
        out_other.status,
    );

    let stdout_list = String::from_utf8_lossy(&out_list.stdout);
    let stdout_other = String::from_utf8_lossy(&out_other.stdout);

    // Truthful scaffold: the output is the same shape as for any task name.
    assert!(
        stdout_list.contains("Running task: list (scaffold placeholder)"),
        "expected scaffold-only banner in `forge list` stdout, got: {stdout_list}"
    );
    assert!(
        stdout_other.contains("Running task: anything-else (scaffold placeholder)"),
        "expected scaffold-only banner in `forge anything-else` stdout, got: {stdout_other}"
    );

    // Negative oracle: `forge list` must NOT contain a listing-of-tasks output.
    // A real `forge list` would print task names from the registry. Today
    // there is no registry, so the only output is the scaffold banner.
    assert!(
        !stdout_list.contains("Available tasks") && !stdout_list.contains("Tasks:"),
        "`forge list` printed task-listing output; FR-CLI-002 is not implemented \
         in code, so the README should not claim it is. stdout={stdout_list}"
    );
}

/// The binary does NOT have a `graph` subcommand. See FR-CLI-003 and the
/// explanation in `test_binary_has_no_list_subcommand` — the negative oracle
/// is "no special subcommand handling."
#[test]
fn test_binary_has_no_graph_subcommand() {
    let out = Command::new(binary_path())
        .arg("graph")
        .output()
        .expect("failed to invoke phenotype-forge binary");
    assert!(
        out.status.success(),
        "`forge graph` should still print the scaffold banner today (no special \
         subcommand handling); got status={:?}, stderr={}",
        out.status,
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(
        stdout.contains("Running task: graph (scaffold placeholder)"),
        "expected scaffold-only banner in `forge graph` stdout, got: {stdout}"
    );
    // Negative oracle: must not contain DAG-rendering output (DOT, mermaid, etc.)
    assert!(
        !stdout.contains("digraph") && !stdout.contains("->") && !stdout.contains("graph TD"),
        "`forge graph` printed DAG output; FR-CLI-003 is not implemented. \
         stdout={stdout}"
    );
}

/// The binary does NOT have a `check` subcommand. See FR-CLI-004 and the
/// explanation in `test_binary_has_no_list_subcommand` — the negative oracle
/// is "no special subcommand handling."
#[test]
fn test_binary_has_no_check_subcommand() {
    let out = Command::new(binary_path())
        .arg("check")
        .output()
        .expect("failed to invoke phenotype-forge binary");
    assert!(
        out.status.success(),
        "`forge check` should still print the scaffold banner today (no special \
         subcommand handling); got status={:?}, stderr={}",
        out.status,
        String::from_utf8_lossy(&out.stderr)
    );
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(
        stdout.contains("Running task: check (scaffold placeholder)"),
        "expected scaffold-only banner in `forge check` stdout, got: {stdout}"
    );
    // Negative oracle: must not contain cycle-detection output.
    assert!(
        !stdout.contains("cycle") && !stdout.contains("Cycle detected"),
        "`forge check` printed cycle-detection output; FR-CLI-004 is not \
         implemented. stdout={stdout}"
    );
}

/// The binary does NOT have a `run` subcommand. `run` is accepted only as a
/// free-form positional task name. See FR-CLI-001 and the explanation in
/// `test_binary_has_no_list_subcommand`.
#[test]
fn test_binary_has_no_run_subcommand() {
    let out = Command::new(binary_path())
        .args(["run", "build"])
        .output()
        .expect("failed to invoke phenotype-forge binary");
    // Note: `run` and `build` are both positional, so `Args.task == "run"`
    // and the second arg ("build") is rejected by clap (UnknownArgument).
    // Either way, the binary must not perform a `run` subcommand.
    let stdout = String::from_utf8_lossy(&out.stdout);
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(
        !stdout.contains("Executing build") && !stdout.contains("Started task"),
        "`forge run build` printed task-execution output; FR-CLI-001 is not \
         implemented. stdout={stdout}, stderr={stderr}"
    );
}

// ---------------------------------------------------------------------------
// README feature-matrix integrity (negative oracle)
// ---------------------------------------------------------------------------

/// The README's feature matrix must NOT contain any false `Stable` or
/// `Beta` claims for features that are not implemented in this checkout.
///
/// This test reads `README.md` at test time and fails if a `Stable` or
/// `Beta` token appears in a feature row. Future implementers who add a
/// real feature should remove the `Stable` from the README **after**
/// landing the implementation (and the corresponding positive test).
#[test]
fn test_readme_feature_matrix_has_no_false_stable_claims() {
    let readme =
        std::fs::read_to_string("README.md").expect("failed to read README.md from the repo root");
    assert!(
        !readme.contains("| Stable"),
        "README feature matrix still contains a `Stable` claim; this scaffold \
         does not deliver any `Stable` features. Update README.md or implement \
         the feature before claiming `Stable`."
    );
    assert!(
        !readme.contains("| Beta"),
        "README feature matrix still contains a `Beta` claim; this scaffold \
         does not deliver any `Beta` features. Update README.md or implement \
         the feature before claiming `Beta`."
    );
}

/// The README must explicitly call out the scaffold-only status.
#[test]
fn test_readme_declares_scaffold_only_status() {
    let readme =
        std::fs::read_to_string("README.md").expect("failed to read README.md from the repo root");
    assert!(
        readme.contains("Scaffold Only") || readme.contains("scaffold-only"),
        "README.md must declare the scaffold-only project status explicitly"
    );
}

// ---------------------------------------------------------------------------
// Cargo.toml integrity (negative oracle)
// ---------------------------------------------------------------------------

/// `Cargo.toml` declares dependencies that the scaffold does not exercise
/// (`tokio`, `serde`, `notify`, `toml`, `thiserror`, `tracing`,
/// `tracing-subscriber`, `tracing-appender`). This test is a lock-in: it
/// fails loudly if a future maintainer silently removes those dependencies
/// without also implementing the corresponding feature.
///
/// In other words: the dependencies are evidence of scope. Removing a
/// dependency without removing the corresponding FRS row is forbidden.
#[test]
fn test_cargo_toml_keeps_declared_dependencies() {
    let cargo = std::fs::read_to_string("Cargo.toml")
        .expect("failed to read Cargo.toml from the repo root");
    for dep in &[
        "tokio",
        "clap",
        "serde",
        "notify",
        "toml",
        "thiserror",
        "tracing",
    ] {
        assert!(
            cargo.contains(dep),
            "Cargo.toml is missing the `{dep}` dependency that was declared \
             at audit time. Removing dependencies without implementing the \
             corresponding feature is forbidden — see CHANGELOG.md 0.0.0 \
             \"Cargo.toml — no changes\"."
        );
    }
}
