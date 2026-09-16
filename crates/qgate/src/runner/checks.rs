// Shared helpers for check orchestration.

use std::path::Path;

use anyhow::Result;
use tokio::process::Command;

use crate::checks::{CheckCategory, CheckResult, CheckStatus};

/// Run a shell command and return (success, combined output tail).
pub(crate) async fn run_cmd(program: &str, args: &[&str], cwd: &Path) -> Result<(bool, String)> {
    let output = Command::new(program)
        .args(args)
        .current_dir(cwd)
        .output()
        .await?;
    let combined = [
        String::from_utf8_lossy(&output.stdout).to_string(),
        String::from_utf8_lossy(&output.stderr).to_string(),
    ]
    .join("\n");
    let tail: String = combined
        .lines()
        .rev()
        .take(30)
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .collect::<Vec<_>>()
        .join("\n");
    Ok((output.status.success(), tail))
}

/// Build a `CheckResult` from a command run outcome.
pub(crate) fn make_result(
    category: CheckCategory,
    ok: bool,
    detail: String,
    success_msg: &str,
    score_if_pass: Option<f64>,
    score_if_fail: Option<f64>,
    threshold: Option<f64>,
) -> CheckResult {
    CheckResult {
        category,
        status: if ok {
            CheckStatus::Passed
        } else {
            CheckStatus::Failed
        },
        score: if ok { score_if_pass } else { score_if_fail },
        threshold,
        details: if ok {
            success_msg.into()
        } else {
            detail
        },
    }
}

/// Build a "not applicable" result.
pub(crate) fn na(name: &str, cat: CheckCategory) -> CheckResult {
    CheckResult {
        category: cat,
        status: CheckStatus::NotApplicable,
        score: None,
        threshold: None,
        details: format!("{name} explicitly declared N/A"),
    }
}

/// Build a "skipped" result.
pub(crate) fn skipped(name: &str, cat: CheckCategory, reason: &str) -> CheckResult {
    CheckResult {
        category: cat,
        status: CheckStatus::Skipped,
        score: None,
        threshold: None,
        details: format!("{name} skipped: {reason}"),
    }
}
