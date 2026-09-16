// Static analysis and security check runners.

use std::path::Path;

use crate::checks::{CheckCategory, CheckResult, CheckStatus, Thresholds};
use crate::config::QGateConfig;

use super::checks::{na, run_cmd};
use super::StackDetector;

pub(crate) async fn run_static_analysis(
    stack: &StackDetector<'_>, root: &Path, cfg: &QGateConfig,
) -> CheckResult {
    if cfg.is_na("static_analysis") {
        return na("static_analysis", CheckCategory::StaticAnalysis);
    }
    let mut sa_details: Vec<String> = Vec::new();
    let mut sa_failed = false;

    if stack.has_rust() {
        let (ok, detail) = run_cmd("cargo", &["clippy", "--workspace", "--", "-D", "warnings"], root)
            .await
            .unwrap_or((false, "clippy not found".into()));
        if !ok {
            sa_failed = true;
            sa_details.push(format!("clippy: {}", detail.lines().next().unwrap_or("")));
        } else {
            sa_details.push("clippy: ok".into());
        }
        let (fmt_ok, fmt_detail) = run_cmd("cargo", &["fmt", "--all", "--", "--check"], root)
            .await
            .unwrap_or((false, "rustfmt not found".into()));
        if !fmt_ok {
            sa_failed = true;
            sa_details.push(format!("rustfmt: {}", fmt_detail.lines().next().unwrap_or("")));
        } else {
            sa_details.push("rustfmt: ok".into());
        }
    }

    if stack.has_typescript() {
        let (ok, detail) = run_cmd("bun", &["x", "tsgo", "--noEmit"], root)
            .await
            .unwrap_or_else(|_| (false, "tsgo not found, falling back".into()));
        if !ok {
            let (tsc_ok, tsc_detail) = tokio::process::Command::new("bun")
                .args(["x", "tsc", "--noEmit"])
                .current_dir(root)
                .output()
                .await
                .map(|o| (o.status.success(), String::from_utf8_lossy(&o.stderr).to_string()))
                .unwrap_or((false, "tsc not found".into()));
            if !tsc_ok {
                sa_failed = true;
                sa_details.push(format!("tsc: {}", tsc_detail.lines().next().unwrap_or("")));
            } else {
                sa_details.push("tsc: ok".into());
            }
        } else {
            sa_details.push(format!("tsgo: {}", if ok { "ok" } else { &detail }));
        }
        let (lint_ok, lint_detail) = run_cmd("bun", &["run", "lint"], root)
            .await
            .unwrap_or((false, "eslint not found".into()));
        if !lint_ok {
            sa_failed = true;
            sa_details.push(format!("eslint: {}", lint_detail.lines().next().unwrap_or("")));
        } else {
            sa_details.push("eslint: ok".into());
        }
    }

    if stack.has_python() {
        let (ok, detail) = run_cmd("uv", &["run", "mypy", "."], root)
            .await
            .unwrap_or((false, "mypy not found".into()));
        if !ok {
            sa_failed = true;
            sa_details.push(format!("mypy: {}", detail.lines().next().unwrap_or("")));
        } else {
            sa_details.push("mypy: ok".into());
        }
        let (ruff_ok, ruff_detail) = run_cmd("uv", &["run", "ruff", "check", "."], root)
            .await
            .unwrap_or((false, "ruff not found".into()));
        if !ruff_ok {
            sa_failed = true;
            sa_details.push(format!("ruff: {}", ruff_detail.lines().next().unwrap_or("")));
        } else {
            sa_details.push("ruff: ok".into());
        }
    }

    CheckResult {
        category: CheckCategory::StaticAnalysis,
        status: if sa_failed { CheckStatus::Failed } else { CheckStatus::Passed },
        score: if sa_failed { Some(1.0) } else { Some(0.0) },
        threshold: Some(Thresholds::STATIC_ANALYSIS_ERRORS),
        details: sa_details.join("; "),
    }
}

pub(crate) async fn run_security(
    stack: &StackDetector<'_>, root: &Path, cfg: &QGateConfig,
) -> CheckResult {
    if cfg.is_na("security") {
        return na("security", CheckCategory::Security);
    }
    let mut sec_failed = false;
    let mut sec_details: Vec<String> = Vec::new();

    let (gl_ok, gl_detail) = run_cmd("gitleaks", &["detect", "--no-git", "--exit-code", "1"], root)
        .await
        .unwrap_or((true, "gitleaks not installed — skipping".into()));
    if !gl_ok {
        sec_failed = true;
        sec_details.push(format!("gitleaks: {}", gl_detail.lines().next().unwrap_or("")));
    } else {
        sec_details.push("gitleaks: ok".into());
    }

    let (sg_ok, sg_detail) = run_cmd("semgrep", &["--config=auto", "--error", "--quiet", "."], root)
        .await
        .unwrap_or((true, "semgrep not installed — skipping".into()));
    if !sg_ok {
        sec_failed = true;
        sec_details.push(format!("semgrep: {}", sg_detail.lines().next().unwrap_or("")));
    } else {
        sec_details.push("semgrep: ok".into());
    }

    if stack.has_rust() {
        let (ca_ok, ca_detail) = run_cmd("cargo", &["audit"], root)
            .await
            .unwrap_or((true, "cargo-audit not installed — skipping".into()));
        if !ca_ok {
            sec_failed = true;
            sec_details.push(format!("cargo-audit: {}", ca_detail.lines().next().unwrap_or("")));
        } else {
            sec_details.push("cargo-audit: ok".into());
        }
    }

    if stack.has_python() {
        let (bandit_ok, bandit_detail) = run_cmd("uv", &["run", "bandit", "-r", ".", "-ll"], root)
            .await
            .unwrap_or((true, "bandit not installed — skipping".into()));
        if !bandit_ok {
            sec_failed = true;
            sec_details.push(format!("bandit: {}", bandit_detail.lines().next().unwrap_or("")));
        } else {
            sec_details.push("bandit: ok".into());
        }
    }

    CheckResult {
        category: CheckCategory::Security,
        status: if sec_failed { CheckStatus::Failed } else { CheckStatus::Passed },
        score: if sec_failed { Some(1.0) } else { Some(0.0) },
        threshold: Some(Thresholds::SECURITY_HIGH_FINDINGS),
        details: sec_details.join("; "),
    }
}
