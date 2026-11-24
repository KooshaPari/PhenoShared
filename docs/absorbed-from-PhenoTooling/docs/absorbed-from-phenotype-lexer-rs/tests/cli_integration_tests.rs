use assert_cmd::Command;
use predicates::str::contains;

#[test]
fn test_cli_adapter_stdin_stdout() {
    let mut cmd = Command::cargo_bin("netscript").unwrap();
    cmd.write_stdin("42\n");
    cmd.assert().success().stdout(contains("Integer(42)"));
}

#[test]
fn test_cli_adapter_multiple_lines() {
    let mut cmd = Command::cargo_bin("netscript").unwrap();
    cmd.write_stdin("let x = 1;\nprint(\"hello\");\n");
    cmd.assert()
        .success()
        .stdout(contains("Let"))
        .stdout(contains("Print"))
        .stdout(contains("String(\"hello\")"));
}

#[test]
fn test_cli_adapter_empty_input() {
    let mut cmd = Command::cargo_bin("netscript").unwrap();
    cmd.write_stdin("");
    cmd.assert().success();
}

#[test]
fn test_cli_adapter_stderr_banner() {
    let mut cmd = Command::cargo_bin("netscript").unwrap();
    cmd.write_stdin("");
    cmd.assert().success().stderr(contains("NetScript Lexer"));
}
