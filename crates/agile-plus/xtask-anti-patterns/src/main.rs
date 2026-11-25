//! Anti-pattern detector binary.
//!
//! Implements Â§3 of `docs/ai-dd-governance.md`. Walks Rust source files in a
//! target repo and emits a JSON report of detected anti-patterns. Exits
//! non-zero if any HIGH severity findings.
//!
//! Run: `cargo run -p xtask-anti-patterns -- --path <repo>`.

use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use serde::Serialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "UPPERCASE")]
enum Severity {
    High,
    Medium,
    Low,
}

#[derive(Debug, Serialize)]
struct Finding {
    file: String,
    line: u64,
    rule_id: &'static str,
    severity: Severity,
    message: String,
}

#[derive(Debug, Serialize)]
struct Report {
    path: String,
    findings: Vec<Finding>,
    high_count: usize,
}

const SKIP_DIRS: &[&str] = &["target", "node_modules", "vendor", ".worktrees"];

fn main() -> ExitCode {
    let args: Vec<String> = env::args().collect();
    let path = match parse_args(&args) {
        Some(p) => p,
        None => {
            eprintln!("usage: xtask-anti-patterns --path <repo>");
            return ExitCode::from(2);
        }
    };

    let mut findings: Vec<Finding> = Vec::new();
    if let Err(e) = walk(&path, &mut findings) {
        eprintln!("walk error: {e}");
        return ExitCode::from(2);
    }

    let high = findings
        .iter()
        .filter(|f| f.severity == Severity::High)
        .count();
    let report = Report {
        path: path.display().to_string(),
        high_count: high,
        findings,
    };

    match serde_json::to_string_pretty(&report) {
        Ok(s) => println!("{s}"),
        Err(e) => {
            eprintln!("serialize error: {e}");
            return ExitCode::from(2);
        }
    }

    if high > 0 {
        ExitCode::from(1)
    } else {
        ExitCode::SUCCESS
    }
}

fn parse_args(args: &[String]) -> Option<PathBuf> {
    let mut iter = args.iter().skip(1);
    while let Some(a) = iter.next() {
        if a == "--path" {
            return iter.next().map(PathBuf::from);
        }
    }
    None
}

fn walk(root: &Path, out: &mut Vec<Finding>) -> std::io::Result<()> {
    if !root.exists() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::NotFound,
            format!("path not found: {}", root.display()),
        ));
    }
    visit(root, out)
}

fn visit(dir: &Path, out: &mut Vec<Finding>) -> std::io::Result<()> {
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        let name = entry.file_name();
        let name = name.to_string_lossy();
        if path.is_dir() {
            if SKIP_DIRS.iter().any(|s| s == &name.as_ref()) {
                continue;
            }
            visit(&path, out)?;
        } else if path.extension().map(|e| e == "rs").unwrap_or(false) {
            scan_file(&path, out);
        }
    }
    Ok(())
}

fn scan_file(path: &Path, out: &mut Vec<Finding>) {
    let content = match fs::read_to_string(path) {
        Ok(s) => s,
        Err(_) => return,
    };
    let in_lib = is_lib_path(path);
    for (idx, line) in content.lines().enumerate() {
        let lineno = (idx as u64) + 1;

        if in_lib {
            if line.contains(".unwrap()") && !line.trim_start().starts_with("//") {
                out.push(Finding {
                    file: path.display().to_string(),
                    line: lineno,
                    rule_id: "unwrap_in_lib",
                    severity: Severity::High,
                    message: "`.unwrap()` in lib code; use `?` or `expect(msg)`".into(),
                });
            }
            if line.contains("panic!") && !line.trim_start().starts_with("//") {
                out.push(Finding {
                    file: path.display().to_string(),
                    line: lineno,
                    rule_id: "panic_in_lib",
                    severity: Severity::High,
                    message: "`panic!` in lib code; return `Result` instead".into(),
                });
            }
        }

        if let Some(after) = strip_call(line, "expect") {
            if after.trim().is_empty() || after.trim() == "()" || after.trim() == "\"\"" {
                out.push(Finding {
                    file: path.display().to_string(),
                    line: lineno,
                    rule_id: "expect_without_message",
                    severity: Severity::Medium,
                    message: "`expect()` requires a non-empty message".into(),
                });
            }
        }

        if line.contains("unsafe ") || line.contains("unsafe{") || line.contains("unsafe {") {
            // SAFETY: within 2 preceding lines
            let lines: Vec<&str> = content.lines().collect();
            let start = idx.saturating_sub(2);
            let window = lines.get(start..idx).unwrap_or(&[]).join("\n");
            if !window.contains("SAFETY:") {
                out.push(Finding {
                    file: path.display().to_string(),
                    line: lineno,
                    rule_id: "unsafe_without_comment",
                    severity: Severity::High,
                    message: "`unsafe` block missing preceding `// SAFETY:` comment".into(),
                });
            }
        }

        if line.contains("TODO") {
            // window: same line + next 30 chars
            let window: String = content
                .lines()
                .skip(idx)
                .take(2)
                .collect::<Vec<_>>()
                .join("\n")
                .chars()
                .take(80)
                .collect();
            if !window.contains("(#") && !window.contains("issue-") {
                out.push(Finding {
                    file: path.display().to_string(),
                    line: lineno,
                    rule_id: "todo_without_issue",
                    severity: Severity::Low,
                    message: "`TODO` missing issue reference (`(#NNN)` or `issue-NNN`)".into(),
                });
            }
        }

        if line.contains("as_str() ==") {
            out.push(Finding {
                file: path.display().to_string(),
                line: lineno,
                rule_id: "stringly_typed_enum",
                severity: Severity::Medium,
                message: "stringly-typed enum: `as_str() ==` matches; consider a newtype".into(),
            });
        }
    }
}

fn is_lib_path(p: &Path) -> bool {
    let s = p.to_string_lossy();
    s.contains("/src/") || s.ends_with("/lib.rs") || s.contains("crates/") && s.contains("/src/")
}

fn strip_call<'a>(line: &'a str, fn_name: &str) -> Option<&'a str> {
    let needle = format!(".{fn_name}");
    let pos = line.find(&needle)?;
    let rest = &line[pos + needle.len()..];
    // require opening paren
    let rest = rest.strip_prefix('(')?;
    // find matching close paren â€” simplified: scan to next `)`
    let end = rest.find(')')?;
    Some(&rest[..end])
}
