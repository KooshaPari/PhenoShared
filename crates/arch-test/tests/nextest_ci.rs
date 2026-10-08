use std::path::PathBuf;

fn repository_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|path| path.parent())
        .expect("arch-test lives under <repo>/crates/arch-test")
        .to_path_buf()
}

#[test]
fn ci_runs_nextest_with_the_ci_profile() {
    // E1.8 (commit c92a24fe, 2026-10-01) moved the rust gate out of
    // `.github/workflows/ci.yml` into a dedicated `quality-gate.yml`
    // workflow. ci.yml is now a thin changes-router only; the actual
    // build, make check, cross-target, and nextest legs all live in
    // quality-gate.yml. This test was originally written against the
    // pre-E1.8 layout and was reading the now-stale ci.yml, so it
    // crashed at the assertion that didn't match the new gate. The
    // rewrite points the same contract — the workspace test suite must
    // run through cargo-nextest's `ci` profile, with a known junit
    // upload path — at the workflow that actually owns that contract.
    let repository_root = repository_root();
    let workflow_path = repository_root.join(".github/workflows/quality-gate.yml");
    let workflow = std::fs::read_to_string(&workflow_path)
        .unwrap_or_else(|e| panic!("read {}: {e}", workflow_path.display()));
    let nextest = std::fs::read_to_string(repository_root.join(".config/nextest.toml"))
        .expect("read nextest configuration");

    assert!(
        workflow.contains("cargo nextest run --workspace --profile ci"),
        "quality-gate must run the workspace test suite through cargo-nextest's ci profile"
    );
    assert!(
        workflow.contains("tool: cargo-nextest"),
        "quality-gate must install cargo-nextest before running the test suite (taiki-e install-action with tool: cargo-nextest)"
    );
    assert!(
        workflow.contains("cargo build --workspace --locked"),
        "quality-gate must prebuild the entire workspace (which includes the cloud-codex conformance fixture) before parallel tests start"
    );
    assert!(
        nextest.contains("[profile.ci]"),
        "the repository must define a dedicated ci nextest profile"
    );
    assert!(
        nextest.contains("test-threads = 12"),
        "the ci profile must opt into parallel test execution"
    );
    assert!(
        nextest.contains("[profile.ci.junit]") && nextest.contains("path = \"junit.xml\""),
        "the ci profile must write its JUnit report into nextest's ci store directory"
    );
    assert!(
        workflow.contains("target/nextest/ci/junit.xml"),
        "quality-gate must upload the JUnit report from nextest's profile-specific store directory"
    );
}
