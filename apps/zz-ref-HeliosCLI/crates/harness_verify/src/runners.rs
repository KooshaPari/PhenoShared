// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Test runners

use crate::error::{Result, VerifyError};
use crate::result::{
    VerificationMetrics, VerificationResult, VerificationStatus, VerificationType,
};
use chrono::Utc;
use std::process::{Command, Output};
use std::time::Instant;
use tracing::{debug, instrument};
use uuid::Uuid;

/// Run tests using cargo test
#[instrument(skip(spec_id), fields(spec_id = %spec_id, timeout_secs))]
pub async fn run_cargo_test(spec_id: &str, timeout_secs: u64) -> Result<VerificationResult> {
    let start = Instant::now();
    let package = spec_id.to_string();

    let output = tokio::time::timeout(
        std::time::Duration::from_secs(timeout_secs),
        tokio::task::spawn_blocking(move || {
            Command::new("cargo").args(["test", "-p", &package, "--", "--nocapture"]).output()
        }),
    )
    .await
    .map_err(|_| VerifyError::Timeout("Test execution timed out".to_string()))?
    .map_err(|e| VerifyError::TestRunnerError(e.to_string()))??;

    Ok(build_cargo_test_result(spec_id, &output, start.elapsed().as_millis() as u64))
}

fn build_cargo_test_result(spec_id: &str, output: &Output, duration_ms: u64) -> VerificationResult {
    let output_str = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr_str = String::from_utf8_lossy(&output.stderr).to_string();

    let passed = output.status.success();
    let status = if passed { VerificationStatus::Passed } else { VerificationStatus::Failed };

    let (test_count, passed_count, failed_count) =
        parse_cargo_test_counts(&output_str, &stderr_str);

    let errors = if !passed { vec![stderr_str] } else { vec![] };

    debug!(passed, test_count, passed_count, failed_count, "cargo test completed");

    VerificationResult {
        id: Uuid::new_v4(),
        spec_id: spec_id.to_string(),
        verification_type: VerificationType::Test,
        status,
        started_at: Utc::now(),
        completed_at: Some(Utc::now()),
        duration_ms,
        output: output_str,
        errors,
        metrics: VerificationMetrics {
            test_count: Some(test_count),
            passed_count: Some(passed_count),
            failed_count: Some(failed_count),
            ..Default::default()
        },
    }
}

/// Parse aggregate test counts from `cargo test` stdout/stderr.
pub(crate) fn parse_cargo_test_counts(stdout: &str, stderr: &str) -> (u32, u32, u32) {
    let mut test_count = 0u32;
    let mut passed_count = 0u32;
    let mut failed_count = 0u32;

    for line in stdout.lines().chain(stderr.lines()) {
        if !line.contains("test result:") {
            continue;
        }
        // Parse: "test result: ok. 10 passed; 0 failed"
        let parts: Vec<&str> = line.split_whitespace().collect();
        for (i, part) in parts.iter().enumerate() {
            if *part == "passed;" {
                if let Some(n) = parts.get(i - 1).and_then(|s| s.parse::<u32>().ok()) {
                    passed_count += n;
                    test_count += n;
                }
            }
            if *part == "failed" || *part == "failed;" {
                if let Some(n) = parts.get(i - 1).and_then(|s| s.parse::<u32>().ok()) {
                    failed_count += n;
                    test_count += n;
                }
            }
        }
    }

    (test_count, passed_count, failed_count)
}

/// Run pytest
#[instrument(skip(spec_id), fields(spec_id = %spec_id, timeout_secs))]
pub async fn run_pytest(spec_id: &str, timeout_secs: u64) -> Result<VerificationResult> {
    let start = Instant::now();

    let output = tokio::time::timeout(
        std::time::Duration::from_secs(timeout_secs),
        tokio::task::spawn_blocking(move || {
            Command::new("pytest").args(["-v", "--tb=short"]).output()
        }),
    )
    .await
    .map_err(|_| VerifyError::Timeout("Test execution timed out".to_string()))?
    .map_err(|e| VerifyError::TestRunnerError(e.to_string()))??;

    Ok(build_pytest_result(spec_id, &output, start.elapsed().as_millis() as u64))
}

fn build_pytest_result(spec_id: &str, output: &Output, duration_ms: u64) -> VerificationResult {
    let output_str = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr_str = String::from_utf8_lossy(&output.stderr).to_string();

    let passed = output.status.success();
    let status = if passed { VerificationStatus::Passed } else { VerificationStatus::Failed };

    let errors = if !passed { vec![stderr_str] } else { vec![] };

    VerificationResult {
        id: Uuid::new_v4(),
        spec_id: spec_id.to_string(),
        verification_type: VerificationType::Test,
        status,
        started_at: Utc::now(),
        completed_at: Some(Utc::now()),
        duration_ms,
        output: output_str,
        errors,
        metrics: Default::default(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_cargo_test_counts_sums_multiple_crates() {
        let stdout = "\
test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out\n";
        let (total, passed, failed) = parse_cargo_test_counts(stdout, "");
        assert_eq!(total, 10);
        assert_eq!(passed, 10);
        assert_eq!(failed, 0);
    }

    #[test]
    fn parse_cargo_test_counts_reads_stderr_lines() {
        let stderr = "test result: ok. 2 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out\n";
        let (total, passed, failed) = parse_cargo_test_counts("", stderr);
        assert_eq!(total, 3);
        assert_eq!(passed, 2);
        assert_eq!(failed, 1);
    }

    #[test]
    fn build_cargo_test_result_populates_metrics() {
        #[cfg(windows)]
        let status = Command::new("cmd").args(["/C", "exit 0"]).output().unwrap().status;
        #[cfg(not(windows))]
        let status = Command::new("true").output().unwrap().status;

        let output = Output {
            status,
            stdout: b"test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out\n"
                .to_vec(),
            stderr: Vec::new(),
        };
        let result = build_cargo_test_result("demo", &output, 12);
        assert!(matches!(result.status, VerificationStatus::Passed));
        assert_eq!(result.metrics.test_count, Some(4));
        assert_eq!(result.metrics.passed_count, Some(4));
    }

    #[test]
    fn build_pytest_result_surfaces_stderr_on_failure() {
        #[cfg(windows)]
        let status = Command::new("cmd").args(["/C", "exit 1"]).output().unwrap().status;
        #[cfg(not(windows))]
        let status = Command::new("false").output().unwrap().status;

        let output = Output { status, stdout: Vec::new(), stderr: b"1 failed".to_vec() };
        let result = build_pytest_result("demo", &output, 5);
        assert!(matches!(result.status, VerificationStatus::Failed));
        assert_eq!(result.errors.len(), 1);
    }

    #[tokio::test]
    async fn run_cargo_test_executes_package_scoped_command() {
        let result = run_cargo_test("harness_interfaces", 180).await.expect("cargo test");
        assert!(matches!(result.status, VerificationStatus::Passed));
        assert!(result.metrics.test_count.unwrap_or(0) > 0);
    }
}
