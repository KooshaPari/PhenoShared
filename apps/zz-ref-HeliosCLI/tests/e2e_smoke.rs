#[test]
fn smoke_readme_exists() {
    let readme = std::fs::read_to_string("README.md").expect("README.md should exist");
    assert!(!readme.is_empty());
}

#[test]
fn smoke_binary_help_exits_ok() {
    let output = std::process::Command::new("cargo")
        .args([
            "run",
            "--quiet",
            "--manifest-path",
            "codex-rs/Cargo.toml",
            "-p",
            "codex-cli",
            "--",
            "--help",
        ])
        .output()
        .expect("cargo run -- --help should succeed");
    assert!(
        output.status.success(),
        "binary --help should exit 0: stderr={}",
        String::from_utf8_lossy(&output.stderr),
    );
}
