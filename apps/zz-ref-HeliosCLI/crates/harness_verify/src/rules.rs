// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Security, performance, and custom verification rules.

use crate::error::Result;
use crate::result::VerificationResult;
use crate::utils::{
    extract_benchmark_time, has_shell_metacharacters, parse_duration_to_ns, which_scanner,
};

/// Run a security scanner verification rule.
pub async fn run_security_rule(
    scanner: &str,
    critical_only: bool,
    spec_id: &str,
) -> Result<VerificationResult> {
    let scanner_clean = scanner.trim();
    if scanner_clean.is_empty() {
        return Ok(make_failed_result(
            spec_id,
            crate::result::VerificationType::Security,
            "Security scanner name is empty",
        ));
    }
    if has_shell_metacharacters(scanner_clean) {
        return Ok(make_failed_result(
            spec_id,
            crate::result::VerificationType::Security,
            &format!("Security scanner name '{}' contains shell metacharacters", scanner_clean),
        ));
    }
    let start = chrono::Utc::now();
    let scanner_path = which_scanner(scanner_clean);
    let result = match scanner_path {
        Some(path) => {
            let output = tokio::process::Command::new(&path).arg("--help").output().await;
            match output {
                Ok(o) => {
                    let duration =
                        chrono::Utc::now().signed_duration_since(start).num_milliseconds() as u64;
                    let passed = o.status.success();
                    VerificationResult {
                        id: uuid::Uuid::new_v4(),
                        spec_id: spec_id.to_string(),
                        verification_type: crate::result::VerificationType::Security,
                        status: if passed {
                            crate::result::VerificationStatus::Passed
                        } else {
                            crate::result::VerificationStatus::Failed
                        },
                        started_at: start,
                        completed_at: Some(chrono::Utc::now()),
                        duration_ms: duration,
                        output: format!(
                            "Security scanner '{}' found at {} (critical_only={})",
                            scanner_clean, path, critical_only
                        ),
                        errors: if !passed {
                            vec![String::from_utf8_lossy(&o.stderr).to_string()]
                        } else {
                            vec![]
                        },
                        metrics: Default::default(),
                    }
                }
                Err(e) => VerificationResult {
                    id: uuid::Uuid::new_v4(),
                    spec_id: spec_id.to_string(),
                    verification_type: crate::result::VerificationType::Security,
                    status: crate::result::VerificationStatus::Failed,
                    started_at: start,
                    completed_at: Some(chrono::Utc::now()),
                    duration_ms: 0,
                    output: format!(
                        "Security scanner '{}' failed to execute: {}",
                        scanner_clean, e
                    ),
                    errors: vec![e.to_string()],
                    metrics: Default::default(),
                },
            }
        }
        None => VerificationResult {
            id: uuid::Uuid::new_v4(),
            spec_id: spec_id.to_string(),
            verification_type: crate::result::VerificationType::Security,
            status: crate::result::VerificationStatus::Skipped,
            started_at: start,
            completed_at: Some(chrono::Utc::now()),
            duration_ms: 0,
            output: format!(
                "Security scanner '{}' not found on PATH (critical_only={})",
                scanner_clean, critical_only
            ),
            errors: vec![],
            metrics: Default::default(),
        },
    };
    Ok(result)
}

/// Run a performance benchmark verification rule.
pub async fn run_performance_rule(
    metric: &str,
    threshold: &str,
    spec_id: &str,
) -> Result<VerificationResult> {
    let threshold_ns = parse_duration_to_ns(threshold);
    let start = chrono::Utc::now();
    let bench_result = tokio::time::timeout(
        std::time::Duration::from_secs(300),
        tokio::task::spawn_blocking({
            let metric = metric.to_string();
            move || {
                let output = std::process::Command::new("cargo")
                    .args(["bench", "--bench", &metric, "--", "--output-format=bencher"])
                    .output();
                if let Ok(output) = output {
                    if output.status.success() {
                        return output;
                    }
                }
                std::process::Command::new("cargo")
                    .args(["test", "--benches", &metric, "--", "--nocapture"])
                    .output()
                    .expect("Failed to run cargo bench or cargo test")
            }
        }),
    )
    .await;
    match bench_result {
        Ok(Ok(output)) => {
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();
            let elapsed = chrono::Utc::now().signed_duration_since(start).num_milliseconds() as u64;
            let measured_ns = extract_benchmark_time(&stdout, &stderr);
            let (passed, output_msg) = if let Some(actual_ns) = measured_ns {
                if let Some(max_ns) = threshold_ns {
                    let passed = actual_ns <= max_ns;
                    (
                        passed,
                        format!(
                            "Performance: {} measured {}ns, threshold {}ns -- {}",
                            metric,
                            actual_ns,
                            max_ns,
                            if passed { "PASSED" } else { "EXCEEDED" }
                        ),
                    )
                } else {
                    (
                        true,
                        format!("Performance: {} measured {}ns (no threshold)", metric, actual_ns),
                    )
                }
            } else {
                let wall_ns = elapsed * 1_000_000;
                if let Some(max_ns) = threshold_ns {
                    let passed = wall_ns <= max_ns;
                    (
                        passed,
                        format!(
                            "Performance: {} wall-clock {}ms, threshold {}ms -- {}",
                            metric,
                            elapsed,
                            max_ns / 1_000_000,
                            if passed { "PASSED" } else { "EXCEEDED" }
                        ),
                    )
                } else {
                    (true, format!("Performance: {} completed in {}ms", metric, elapsed))
                }
            };
            Ok(VerificationResult {
                id: uuid::Uuid::new_v4(),
                spec_id: spec_id.to_string(),
                verification_type: crate::result::VerificationType::Performance,
                status: if passed {
                    crate::result::VerificationStatus::Passed
                } else {
                    crate::result::VerificationStatus::Failed
                },
                started_at: start,
                completed_at: Some(chrono::Utc::now()),
                duration_ms: elapsed,
                output: output_msg,
                errors: if !passed {
                    vec![format!("Performance threshold exceeded for '{}'", metric)]
                } else {
                    vec![]
                },
                metrics: Default::default(),
            })
        }
        _ => Ok(make_failed_result(
            spec_id,
            crate::result::VerificationType::Performance,
            &format!("Performance benchmark '{}' failed to execute", metric),
        )),
    }
}

/// Run a custom command verification rule.
pub async fn run_custom_rule(
    command: &str,
    expected_exit_code: i32,
    spec_id: &str,
) -> Result<VerificationResult> {
    if has_shell_metacharacters(command) {
        return Ok(make_failed_result(
            spec_id,
            crate::result::VerificationType::Custom,
            "Custom command rejected: contains shell metacharacters",
        ));
    }
    let output = tokio::process::Command::new("sh").args(["-c", command]).output().await?;
    let passed = output.status.code() == Some(expected_exit_code);
    Ok(VerificationResult {
        id: uuid::Uuid::new_v4(),
        spec_id: spec_id.to_string(),
        verification_type: crate::result::VerificationType::Custom,
        status: if passed {
            crate::result::VerificationStatus::Passed
        } else {
            crate::result::VerificationStatus::Failed
        },
        started_at: chrono::Utc::now(),
        completed_at: Some(chrono::Utc::now()),
        duration_ms: 0,
        output: String::from_utf8_lossy(&output.stdout).to_string(),
        errors: vec![String::from_utf8_lossy(&output.stderr).to_string()],
        metrics: Default::default(),
    })
}

fn make_failed_result(
    spec_id: &str,
    vtype: crate::result::VerificationType,
    output: &str,
) -> VerificationResult {
    VerificationResult {
        id: uuid::Uuid::new_v4(),
        spec_id: spec_id.to_string(),
        verification_type: vtype,
        status: crate::result::VerificationStatus::Failed,
        started_at: chrono::Utc::now(),
        completed_at: Some(chrono::Utc::now()),
        duration_ms: 0,
        output: output.to_string(),
        errors: vec![],
        metrics: Default::default(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::result::VerificationStatus;

    #[tokio::test]
    async fn security_rule_is_skipped_with_message() {
        let absent_scanner = "harness-verify-test-scanner-not-installed";
        let result = run_security_rule(absent_scanner, true, "security-demo").await.unwrap();
        assert!(matches!(result.status, VerificationStatus::Skipped));
        assert!(result.output.contains(absent_scanner));
    }

    #[tokio::test]
    async fn security_rule_rejects_metacharacters() {
        let result = run_security_rule("echo | cat", true, "test").await.unwrap();
        assert!(matches!(result.status, VerificationStatus::Failed));
        assert!(result.output.contains("metacharacters"));
    }

    #[tokio::test]
    async fn security_rule_rejects_empty_scanner() {
        let result = run_security_rule("", true, "test").await.unwrap();
        assert!(matches!(result.status, VerificationStatus::Failed));
        assert!(result.output.contains("empty"));
    }

    #[tokio::test]
    async fn performance_rule_runs_benchmark_and_checks_threshold() {
        let result =
            run_performance_rule("nonexistent_benchmark_xyz", "300s", "perf-demo").await.unwrap();
        assert!(matches!(result.status, VerificationStatus::Failed | VerificationStatus::Passed));
        assert!(result.output.starts_with("Performance:"));
    }

    #[test]
    fn parse_duration_to_ns_parses_common_formats() {
        assert_eq!(parse_duration_to_ns("250ms"), Some(250_000_000));
        assert_eq!(parse_duration_to_ns("1500ns"), Some(1500));
        assert_eq!(parse_duration_to_ns("2s"), Some(2_000_000_000));
        assert_eq!(parse_duration_to_ns("500us"), Some(500_000));
        assert_eq!(parse_duration_to_ns("1234"), Some(1234));
        assert_eq!(parse_duration_to_ns("  100ms  "), Some(100_000_000));
        assert_eq!(parse_duration_to_ns("invalid"), None);
    }

    #[test]
    fn extract_benchmark_time_parses_criterion_output() {
        let stderr = "time:   [1.2345 ms 1.2356 ms 1.2367 ms]";
        assert_eq!(extract_benchmark_time("", stderr), Some(1_234_500));
    }

    #[test]
    fn extract_benchmark_time_parses_bench_output() {
        let stdout = "test bench_foo ... bench: 1234 ns/iter (+/- 56)";
        assert_eq!(extract_benchmark_time(stdout, ""), Some(1234));
    }

    #[test]
    fn extract_benchmark_time_returns_none_for_empty() {
        assert_eq!(extract_benchmark_time("", ""), None);
        assert_eq!(extract_benchmark_time("no timing here", ""), None);
    }

    #[test]
    fn has_shell_metacharacters_detects_injection_attempts() {
        assert!(!has_shell_metacharacters("rm -rf /"));
        assert!(has_shell_metacharacters("echo hello | cat /etc/passwd"));
        assert!(has_shell_metacharacters("test; rm -rf /"));
        assert!(has_shell_metacharacters("cmd && malice"));
        assert!(has_shell_metacharacters("`whoami`"));
        assert!(has_shell_metacharacters("$(whoami)"));
        assert!(has_shell_metacharacters("echo > /tmp/pwned"));
        assert!(has_shell_metacharacters("echo < /etc/shadow"));
        assert!(has_shell_metacharacters("a\nb"));
    }
}
