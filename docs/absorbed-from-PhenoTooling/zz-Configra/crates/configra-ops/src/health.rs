//! Liveness and readiness health probes.

use std::time::{Duration, Instant};

use chrono::Utc;
use serde::Serialize;

use crate::metrics::{self, names, MetricsHook, NoopMetricsHook};

/// Aggregate health status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum HealthStatus {
    /// All checks passed.
    Healthy,
    /// One or more checks failed.
    Unhealthy,
}

/// Result of a single named check.
#[derive(Debug, Clone, Serialize)]
pub struct CheckResult {
    pub name: String,
    pub status: HealthStatus,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
    pub duration_ms: u64,
}

impl CheckResult {
    pub fn ok(name: impl Into<String>, started: Instant) -> Self {
        Self {
            name: name.into(),
            status: HealthStatus::Healthy,
            message: None,
            duration_ms: started.elapsed().as_millis() as u64,
        }
    }

    pub fn fail(name: impl Into<String>, message: impl Into<String>, started: Instant) -> Self {
        Self {
            name: name.into(),
            status: HealthStatus::Unhealthy,
            message: Some(message.into()),
            duration_ms: started.elapsed().as_millis() as u64,
        }
    }
}

/// Full health report (JSON-serializable for probes and CLI).
#[derive(Debug, Clone, Serialize)]
pub struct HealthReport {
    pub status: HealthStatus,
    pub version: String,
    pub timestamp: String,
    pub checks: Vec<CheckResult>,
}

impl HealthReport {
    /// Exit code for shell / container probes (`0` healthy, `1` unhealthy).
    pub fn exit_code(&self) -> i32 {
        if self.status == HealthStatus::Healthy {
            0
        } else {
            1
        }
    }

    /// Serialize to compact JSON.
    pub fn to_json(&self) -> serde_json::Result<String> {
        serde_json::to_string(self)
    }
}

/// Pluggable readiness dependency check.
pub trait HealthCheck: Send + Sync {
    /// Stable check name (e.g. `sqlite`, `redis`).
    fn name(&self) -> &str;
    /// Perform the check; return `Ok(())` when healthy.
    fn check(&self) -> Result<(), String>;
}

/// Process liveness — always healthy if the binary is running.
pub fn liveness(version: &str) -> HealthReport {
    let started = Instant::now();
    HealthReport {
        status: HealthStatus::Healthy,
        version: version.to_owned(),
        timestamp: Utc::now().to_rfc3339(),
        checks: vec![CheckResult::ok("process", started)],
    }
}

/// Readiness over injected dependency checks.
pub fn readiness(version: &str, checks: &[&dyn HealthCheck]) -> HealthReport {
    readiness_with_metrics(version, checks, &NoopMetricsHook)
}

/// Readiness with metrics recording.
pub fn readiness_with_metrics(
    version: &str,
    checks: &[&dyn HealthCheck],
    metrics: &dyn MetricsHook,
) -> HealthReport {
    if metrics::metrics_enabled() {
        metrics.increment_counter(names::HEALTH_CHECK_TOTAL, 1);
    }

    let timeout = health_timeout();
    let mut results = Vec::with_capacity(checks.len());
    let mut overall = HealthStatus::Healthy;

    for check in checks {
        let started = Instant::now();
        let result = match run_with_timeout(*check, timeout) {
            Ok(()) => CheckResult::ok(check.name().to_owned(), started),
            Err(msg) => {
                overall = HealthStatus::Unhealthy;
                CheckResult::fail(check.name().to_owned(), msg, started)
            }
        };
        results.push(result);
    }

    HealthReport {
        status: overall,
        version: version.to_owned(),
        timestamp: Utc::now().to_rfc3339(),
        checks: results,
    }
}

fn run_with_timeout(check: &dyn HealthCheck, timeout: Duration) -> Result<(), String> {
    // Synchronous checks with a soft deadline — integrators should keep checks fast.
    let started = Instant::now();
    let outcome = check.check();
    if started.elapsed() > timeout {
        return Err(format!("check exceeded {}ms budget", timeout.as_millis()));
    }
    outcome
}

fn health_timeout() -> Duration {
    let secs = std::env::var("CONFIGRA_HEALTHCHECK_TIMEOUT_SECS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(5);
    Duration::from_secs(secs)
}

/// Built-in check: workspace crates are linkable (compile-time guarantee).
#[derive(Debug, Default, Clone, Copy)]
pub struct WorkspaceCheck;

impl HealthCheck for WorkspaceCheck {
    fn name(&self) -> &str {
        "workspace"
    }

    fn check(&self) -> Result<(), String> {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct Failing;

    impl HealthCheck for Failing {
        fn name(&self) -> &str {
            "failing"
        }
        fn check(&self) -> Result<(), String> {
            Err("down".into())
        }
    }

    #[test]
    fn readiness_marks_unhealthy_on_failure() {
        let failing = Failing;
        let checks: Vec<&dyn HealthCheck> = vec![&failing];
        let report = readiness("0.0.0", &checks);
        assert_eq!(report.status, HealthStatus::Unhealthy);
        assert_eq!(report.exit_code(), 1);
    }

    #[test]
    fn liveness_always_healthy() {
        let report = liveness("1.2.3");
        assert_eq!(report.status, HealthStatus::Healthy);
        assert_eq!(report.exit_code(), 0);
        assert_eq!(report.version, "1.2.3");
        assert_eq!(report.checks.len(), 1);
        assert_eq!(report.checks[0].name, "process");
    }

    #[test]
    fn readiness_healthy_when_all_pass() {
        let ws = WorkspaceCheck;
        let checks: Vec<&dyn HealthCheck> = vec![&ws];
        let report = readiness("0.1.0", &checks);
        assert_eq!(report.status, HealthStatus::Healthy);
        assert_eq!(report.exit_code(), 0);
        assert_eq!(report.checks.len(), 1);
        assert_eq!(report.checks[0].status, HealthStatus::Healthy);
    }

    #[test]
    fn readiness_mixed_checks() {
        struct Passing;
        impl HealthCheck for Passing {
            fn name(&self) -> &str { "passing" }
            fn check(&self) -> Result<(), String> { Ok(()) }
        }

        let passing = Passing;
        let failing = Failing;
        let checks: Vec<&dyn HealthCheck> = vec![&passing, &failing];
        let report = readiness("0.1.0", &checks);
        assert_eq!(report.status, HealthStatus::Unhealthy);
        assert_eq!(report.checks.len(), 2);
        assert_eq!(report.checks[0].status, HealthStatus::Healthy);
        assert_eq!(report.checks[1].status, HealthStatus::Unhealthy);
    }

    #[test]
    fn health_report_json_roundtrip() {
        let report = liveness("1.0.0");
        let json = report.to_json().unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed["status"], "healthy");
        assert_eq!(parsed["version"], "1.0.0");
        assert!(parsed["timestamp"].is_string());
    }

    #[test]
    fn check_result_ok_has_healthy_status() {
        let start = std::time::Instant::now();
        let result = CheckResult::ok("test-check", start);
        assert_eq!(result.status, HealthStatus::Healthy);
        assert_eq!(result.name, "test-check");
        assert!(result.message.is_none());
    }

    #[test]
    fn check_result_fail_has_unhealthy_status() {
        let start = std::time::Instant::now();
        let result = CheckResult::fail("test-check", "something broke", start);
        assert_eq!(result.status, HealthStatus::Unhealthy);
        assert_eq!(result.name, "test-check");
        assert_eq!(result.message.as_deref(), Some("something broke"));
    }
}
