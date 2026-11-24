//! Integration tests for phenotype-health-cli

use phenotype_health::HealthStatus;
use phenotype_health_cli::{
    HealthMetrics, ProjectHealthResult, ProjectSummary, UnifiedHealthReport, UnifiedHealthScanner,
};
use phenotype_project_registry::ProjectType;
use std::path::PathBuf;

/// Test unified health scanner creation
#[test]
fn test_scanner_creation() {
    let scanner = UnifiedHealthScanner::new();
    // Just verify it creates without panicking
}

/// Test project health result structure
#[test]
fn test_project_health_result() {
    let result = ProjectHealthResult {
        path: "/test/path".to_string(),
        project_type: ProjectType::RustLibrary,
        compliance_score: 85.0,
        security_risk_score: 15.0,
        findings_count: 2,
        has_health_config: true,
        status: HealthStatus::Degraded,
    };

    assert_eq!(result.path, "/test/path");
    assert_eq!(result.compliance_score, 85.0);
    assert_eq!(result.security_risk_score, 15.0);
    assert_eq!(result.status, HealthStatus::Degraded);
}

/// Test project summary structure
#[test]
fn test_project_summary() {
    let summary = ProjectSummary {
        name: "test-project".to_string(),
        project_type: ProjectType::RustLibrary,
        path: "/test".to_string(),
        has_health_config: true,
        compliance_score: 95.0,
        security_risk_score: 10.0,
        status: HealthStatus::Healthy,
    };

    assert_eq!(summary.name, "test-project");
    assert!(summary.has_health_config);
}

/// Test health metrics default
#[test]
fn test_health_metrics_default() {
    let metrics = HealthMetrics::default();
    assert_eq!(metrics.total_projects, 0);
    assert_eq!(metrics.healthy_projects, 0);
    assert_eq!(metrics.critical_findings, 0);
}

/// Test unified health report structure
#[test]
fn test_unified_health_report() {
    let report = UnifiedHealthReport {
        status: HealthStatus::Healthy,
        projects: vec![],
        compliance_findings: vec![],
        security_findings: vec![],
        metrics: HealthMetrics::default(),
    };

    assert_eq!(report.status, HealthStatus::Healthy);
    assert!(report.projects.is_empty());
}

/// Test scanner default implementation
#[test]
fn test_scanner_default() {
    let scanner = UnifiedHealthScanner::default();
    // Verify default() works
}
