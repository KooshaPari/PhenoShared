use serde::Serialize;
use std::path::Path;

use phenotype_compliance_scanner::{ComplianceScanner, Finding, Severity};
use phenotype_health::{HealthRegistry, HealthStatus};
use phenotype_project_registry::{discover_projects, ProjectMetadata, ProjectType};
use phenotype_security_aggregator::{
    Finding as SecurityFinding, SecurityAggregator,
};

/// Unified health report combining all sources
#[derive(Debug, Clone, Serialize)]
pub struct UnifiedHealthReport {
    /// Overall health status
    pub status: HealthStatus,
    /// Projects discovered
    pub projects: Vec<ProjectSummary>,
    /// Compliance findings by project
    pub compliance_findings: Vec<Finding>,
    /// Security findings
    pub security_findings: Vec<SecurityFinding>,
    /// Aggregated metrics
    pub metrics: HealthMetrics,
}

/// Project summary in unified report
#[derive(Debug, Clone, Serialize)]
pub struct ProjectSummary {
    pub name: String,
    pub project_type: ProjectType,
    pub path: String,
    pub has_health_config: bool,
    pub compliance_score: f32,
    pub security_risk_score: f32,
    pub status: HealthStatus,
}

/// Aggregated health metrics
#[derive(Debug, Clone, Default, Serialize)]
pub struct HealthMetrics {
    pub total_projects: usize,
    pub healthy_projects: usize,
    pub degraded_projects: usize,
    pub unhealthy_projects: usize,
    pub critical_findings: usize,
    pub high_findings: usize,
    pub medium_findings: usize,
    pub low_findings: usize,
}

/// Unified health scanner integrating all 4 crates
pub struct UnifiedHealthScanner {
    compliance_scanner: ComplianceScanner,
    security_aggregator: SecurityAggregator,
    #[cfg(feature = "health-registry")]
    health_registry: HealthRegistry,
}

impl UnifiedHealthScanner {
    /// Create new unified scanner
    pub fn new() -> Self {
        Self {
            compliance_scanner: ComplianceScanner::default(),
            security_aggregator: SecurityAggregator::new(),
            #[cfg(feature = "health-registry")]
            health_registry: HealthRegistry::new(),
        }
    }

    /// Scan entire workspace and generate unified report
    pub async fn scan_workspace(&mut self, root_path: impl AsRef<Path>) -> UnifiedHealthReport {
        let root = root_path.as_ref();

        // Step 1: Discover all projects (sync function, run in blocking thread)
        let path_buf = root.to_path_buf();
        let projects: Vec<ProjectMetadata> =
            tokio::task::spawn_blocking(move || discover_projects(path_buf).unwrap_or_default())
                .await
                .unwrap_or_default();

        // Step 2: Scan compliance for each project
        let mut compliance_findings = Vec::new();
        for project in &projects {
            if let Ok(result) = self.compliance_scanner.scan(&project.path) {
                compliance_findings.extend(result.findings);
            }
        }

        // Step 3: Aggregate security findings
        let security_findings: Vec<SecurityFinding> =
            match self.security_aggregator.aggregate().await {
                Ok(report) => report.findings,
                Err(_) => Vec::new(),
            };

        // Step 4: Calculate project summaries
        let project_summaries: Vec<ProjectSummary> = projects
            .into_iter()
            .map(|p| {
                let compliance_score = self.calculate_compliance_score(&p.path);
                let security_risk = self.calculate_security_risk(&p.name);
                let status = if compliance_score >= 90.0 && security_risk < 30.0 {
                    HealthStatus::Healthy
                } else if compliance_score >= 70.0 && security_risk < 60.0 {
                    HealthStatus::Degraded
                } else {
                    HealthStatus::Unhealthy
                };

                ProjectSummary {
                    name: p.name.clone(),
                    project_type: p.project_type.clone(),
                    path: p.path.to_string_lossy().to_string(),
                    has_health_config: p.health_config.enabled,
                    compliance_score,
                    security_risk_score: security_risk,
                    status,
                }
            })
            .collect();

        // Step 5: Calculate overall status
        let status = self.calculate_overall_status(
            &project_summaries,
            &compliance_findings,
            &security_findings,
        );

        // Step 6: Build metrics
        let metrics =
            self.calculate_metrics(&project_summaries, &compliance_findings, &security_findings);

        UnifiedHealthReport {
            status,
            projects: project_summaries,
            compliance_findings,
            security_findings,
            metrics,
        }
    }

    /// Run quick health check on a single project
    pub async fn quick_check(&mut self, project_path: impl AsRef<Path>) -> ProjectHealthResult {
        let path = project_path.as_ref();

        // Detect project type
        let project_type = if path.join("Cargo.toml").exists() {
            ProjectType::RustLibrary
        } else if path.join("package.json").exists() {
            ProjectType::TypeScriptLibrary
        } else if path.join("go.mod").exists() {
            ProjectType::GoModule
        } else if path.join("pyproject.toml").exists() || path.join("setup.py").exists() {
            ProjectType::PythonPackage
        } else {
            ProjectType::Unknown
        };

        // Scan compliance
        let findings: Vec<Finding> = match self.compliance_scanner.scan(path) {
            Ok(result) => result.findings,
            Err(_) => Vec::new(),
        };

        let compliance_score = if findings.is_empty() {
            100.0
        } else {
            let critical = findings
                .iter()
                .filter(|f| matches!(f.severity, Severity::Critical))
                .count();
            let high = findings
                .iter()
                .filter(|f| matches!(f.severity, Severity::High))
                .count();
            let medium = findings
                .iter()
                .filter(|f| matches!(f.severity, Severity::Medium))
                .count();
            let base =
                100.0 - (critical as f32 * 20.0) - (high as f32 * 10.0) - (medium as f32 * 5.0);
            if base < 0.0 {
                0.0
            } else {
                base
            }
        };

        // Check for health config
        let has_health_config =
            path.join("health.toml").exists() || path.join(".github/health.yaml").exists();

        // Get security findings and calculate actual risk score
        let security_findings: Vec<SecurityFinding> =
            match self.security_aggregator.aggregate().await {
                Ok(report) => report.findings,
                Err(_) => Vec::new(),
            };

        // Calculate security risk score based on findings severity
        let security_risk_score = if security_findings.is_empty() {
            0.0
        } else {
            let critical = security_findings
                .iter()
                .filter(|f| {
                    matches!(
                        f.severity,
                        phenotype_security_aggregator::Severity::Critical
                    )
                })
                .count();
            let high = security_findings
                .iter()
                .filter(|f| matches!(f.severity, phenotype_security_aggregator::Severity::High))
                .count();
            let medium = security_findings
                .iter()
                .filter(|f| matches!(f.severity, phenotype_security_aggregator::Severity::Medium))
                .count();
            let low = security_findings
                .iter()
                .filter(|f| matches!(f.severity, phenotype_security_aggregator::Severity::Low))
                .count();

            // Weighted risk calculation (0-100 scale)
            let risk = (critical as f32 * 25.0)
                + (high as f32 * 10.0)
                + (medium as f32 * 3.0)
                + (low as f32 * 1.0);
            risk.min(100.0)
        };

        ProjectHealthResult {
            path: path.to_string_lossy().to_string(),
            project_type,
            compliance_score,
            security_risk_score,
            findings_count: findings.len() + security_findings.len(),
            has_health_config,
            status: if compliance_score >= 90.0 && security_risk_score < 30.0 {
                HealthStatus::Healthy
            } else if compliance_score >= 70.0 && security_risk_score < 60.0 {
                HealthStatus::Degraded
            } else {
                HealthStatus::Unhealthy
            },
        }
    }

    fn calculate_compliance_score(&self, path: &std::path::Path) -> f32 {
        // Check for basic documentation
        let has_readme = path.join("README.md").exists() || path.join("README.rst").exists();
        let has_license = path.join("LICENSE").exists() || path.join("LICENSE.md").exists();
        let has_agents = path.join("AGENTS.md").exists();

        let mut score = 100.0;
        if !has_readme {
            score -= 30.0;
        }
        if !has_license {
            score -= 20.0;
        }
        if !has_agents {
            score -= 10.0;
        }

        if score < 0.0 {
            0.0
        } else {
            score
        }
    }

    fn calculate_security_risk(&self, project_name: &str) -> f32 {
        // Mock security risk calculation based on project name patterns
        let lower = project_name.to_lowercase();
        if lower.contains("auth") || lower.contains("security") {
            25.0 // Higher inherent risk for auth/security projects
        } else if lower.contains("legacy") || lower.contains("old") {
            50.0 // Legacy code risk
        } else {
            15.0 // Default low risk
        }
    }

    fn calculate_overall_status(
        &self,
        projects: &[ProjectSummary],
        compliance: &[Finding],
        security: &[SecurityFinding],
    ) -> HealthStatus {
        let critical_count = compliance
            .iter()
            .filter(|f| matches!(f.severity, Severity::Critical))
            .count()
            + security
                .iter()
                .filter(|f| {
                    matches!(
                        f.severity,
                        phenotype_security_aggregator::Severity::Critical
                    )
                })
                .count();

        let high_count = compliance
            .iter()
            .filter(|f| matches!(f.severity, Severity::High))
            .count()
            + security
                .iter()
                .filter(|f| matches!(f.severity, phenotype_security_aggregator::Severity::High))
                .count();

        let unhealthy_projects = projects
            .iter()
            .filter(|p| p.compliance_score < 50.0)
            .count();

        if critical_count > 0 || unhealthy_projects > projects.len() / 2 {
            HealthStatus::Unhealthy
        } else if high_count > 0 || unhealthy_projects > 0 {
            HealthStatus::Degraded
        } else {
            HealthStatus::Healthy
        }
    }

    fn calculate_metrics(
        &self,
        projects: &[ProjectSummary],
        compliance: &[Finding],
        security: &[SecurityFinding],
    ) -> HealthMetrics {
        HealthMetrics {
            total_projects: projects.len(),
            healthy_projects: projects
                .iter()
                .filter(|p| p.compliance_score >= 90.0)
                .count(),
            degraded_projects: projects
                .iter()
                .filter(|p| p.compliance_score >= 70.0 && p.compliance_score < 90.0)
                .count(),
            unhealthy_projects: projects
                .iter()
                .filter(|p| p.compliance_score < 70.0)
                .count(),
            critical_findings: compliance
                .iter()
                .filter(|f| matches!(f.severity, Severity::Critical))
                .count()
                + security
                    .iter()
                    .filter(|f| {
                        matches!(
                            f.severity,
                            phenotype_security_aggregator::Severity::Critical
                        )
                    })
                    .count(),
            high_findings: compliance
                .iter()
                .filter(|f| matches!(f.severity, Severity::High))
                .count()
                + security
                    .iter()
                    .filter(|f| matches!(f.severity, phenotype_security_aggregator::Severity::High))
                    .count(),
            medium_findings: compliance
                .iter()
                .filter(|f| matches!(f.severity, Severity::Medium))
                .count()
                + security
                    .iter()
                    .filter(|f| {
                        matches!(f.severity, phenotype_security_aggregator::Severity::Medium)
                    })
                    .count(),
            low_findings: compliance
                .iter()
                .filter(|f| matches!(f.severity, Severity::Low))
                .count()
                + security
                    .iter()
                    .filter(|f| matches!(f.severity, phenotype_security_aggregator::Severity::Low))
                    .count(),
        }
    }
}

impl Default for UnifiedHealthScanner {
    fn default() -> Self {
        Self::new()
    }
}

/// Health result for a single project
#[derive(Debug, Clone, Serialize)]
pub struct ProjectHealthResult {
    pub path: String,
    pub project_type: ProjectType,
    pub compliance_score: f32,
    pub security_risk_score: f32,
    pub findings_count: usize,
    pub has_health_config: bool,
    pub status: HealthStatus,
}

/// Generate JSON report from unified health report
pub fn generate_json_report(report: &UnifiedHealthReport) -> String {
    let projects_json: Vec<serde_json::Value> = report
        .projects
        .iter()
        .map(|p| {
            serde_json::json!({
                "name": p.name,
                "type": format!("{:?}", p.project_type),
                "path": p.path,
                "compliance_score": p.compliance_score,
                "security_risk": p.security_risk_score,
                "has_health_config": p.has_health_config,
            })
        })
        .collect();

    let json = serde_json::json!({
        "status": format!("{:?}", report.status),
        "summary": {
            "total_projects": report.metrics.total_projects,
            "healthy": report.metrics.healthy_projects,
            "degraded": report.metrics.degraded_projects,
            "unhealthy": report.metrics.unhealthy_projects,
        },
        "findings": {
            "critical": report.metrics.critical_findings,
            "high": report.metrics.high_findings,
            "medium": report.metrics.medium_findings,
            "low": report.metrics.low_findings,
        },
        "projects": projects_json,
    });

    serde_json::to_string_pretty(&json).unwrap_or_default()
}

/// Generate text table report
pub fn generate_table_report(report: &UnifiedHealthReport) -> String {
    let mut output = String::new();

    // Header
    output.push_str(&format!("\n{:=^60}\n", " UNIFIED HEALTH REPORT "));
    output.push_str(&format!("Overall Status: {:?}\n\n", report.status));

    // Summary
    output.push_str("SUMMARY:\n");
    output.push_str(&format!(
        "  Projects: {} ({} healthy, {} degraded, {} unhealthy)\n",
        report.metrics.total_projects,
        report.metrics.healthy_projects,
        report.metrics.degraded_projects,
        report.metrics.unhealthy_projects
    ));
    output.push_str(&format!(
        "  Findings: {} critical, {} high, {} medium, {} low\n\n",
        report.metrics.critical_findings,
        report.metrics.high_findings,
        report.metrics.medium_findings,
        report.metrics.low_findings
    ));

    // Projects table
    output.push_str("PROJECTS:\n");
    output.push_str(&format!(
        "{:<20} {:<12} {:<10} {:<12}\n",
        "Name", "Type", "Score", "Status"
    ));
    output.push_str(&"-".repeat(60));
    output.push('\n');

    for project in &report.projects {
        let status_str = match project.compliance_score {
            s if s >= 90.0 => "✅ Healthy",
            s if s >= 70.0 => "⚠️  Degraded",
            _ => "❌ Unhealthy",
        };
        let name = if project.name.len() > 20 {
            &project.name[..20]
        } else {
            &project.name
        };
        output.push_str(&format!(
            "{:<20} {:<12} {:>6.1}% {:<12}\n",
            name,
            format!("{:?}", project.project_type),
            project.compliance_score,
            status_str
        ));
    }

    output.push('\n');
    output
}

/// Generate YAML report from unified health report
pub fn generate_yaml_report(report: &UnifiedHealthReport) -> String {
    let projects_yaml: Vec<serde_yaml::Value> = report
        .projects
        .iter()
        .map(|p| {
            serde_yaml::Value::Mapping(
                [
                    ("name".into(), p.name.clone().into()),
                    ("type".into(), format!("{:?}", p.project_type).into()),
                    ("path".into(), p.path.clone().into()),
                    ("compliance_score".into(), p.compliance_score.into()),
                    ("security_risk".into(), p.security_risk_score.into()),
                ]
                .into_iter()
                .collect(),
            )
        })
        .collect();

    let yaml = serde_yaml::Value::Mapping(
        [
            ("status".into(), format!("{:?}", report.status).into()),
            (
                "summary".into(),
                serde_yaml::Value::Mapping(
                    [
                        (
                            "total_projects".into(),
                            report.metrics.total_projects.into(),
                        ),
                        ("healthy".into(), report.metrics.healthy_projects.into()),
                        ("degraded".into(), report.metrics.degraded_projects.into()),
                        ("unhealthy".into(), report.metrics.unhealthy_projects.into()),
                    ]
                    .into_iter()
                    .collect(),
                ),
            ),
            (
                "findings".into(),
                serde_yaml::Value::Mapping(
                    [
                        ("critical".into(), report.metrics.critical_findings.into()),
                        ("high".into(), report.metrics.high_findings.into()),
                        ("medium".into(), report.metrics.medium_findings.into()),
                        ("low".into(), report.metrics.low_findings.into()),
                    ]
                    .into_iter()
                    .collect(),
                ),
            ),
            (
                "projects".into(),
                serde_yaml::Value::Sequence(projects_yaml),
            ),
        ]
        .into_iter()
        .collect(),
    );

    serde_yaml::to_string(&yaml).unwrap_or_default()
}

/// Generate HTML report from unified health report
pub fn generate_html_report(report: &UnifiedHealthReport) -> String {
    let status_class = match report.status {
        HealthStatus::Healthy => "status-healthy",
        HealthStatus::Degraded => "status-degraded",
        HealthStatus::Unhealthy => "status-unhealthy",
    };

    let status_color = match report.status {
        HealthStatus::Healthy => "#238636",
        HealthStatus::Degraded => "#d29922",
        HealthStatus::Unhealthy => "#da3633",
    };

    let projects_rows: String = report
        .projects
        .iter()
        .map(|p| {
            let status = if p.compliance_score >= 90.0 {
                ("✅ Healthy", "#238636")
            } else if p.compliance_score >= 70.0 {
                ("⚠️ Degraded", "#d29922")
            } else {
                ("❌ Unhealthy", "#da3633")
            };
            format!(
                r#"<tr>
                    <td>{}</td>
                    <td>{:?}</td>
                    <td>{:.1}%</td>
                    <td style="color: {}">{}</td>
                </tr>"#,
                p.name, p.project_type, p.compliance_score, status.1, status.0
            )
        })
        .collect();

    format!(
        r#"<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Health Report - {}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #0d1117;
            color: #c9d1d9;
        }}
        h1 {{ color: #58a6ff; }}
        .status {{ color: {}; font-size: 1.5em; font-weight: bold; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .metric {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #58a6ff; }}
        .metric-label {{ color: #8b949e; font-size: 0.9em; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #30363d;
        }}
        th {{ background: #161b22; color: #58a6ff; }}
        tr:hover {{ background: #161b22; }}
        .status-healthy {{ border-left: 4px solid #238636; }}
        .status-degraded {{ border-left: 4px solid #d29922; }}
        .status-unhealthy {{ border-left: 4px solid #da3633; }}
    </style>
</head>
<body>
    <h1>🩺 Unified Health Report</h1>
    <p class="status {}">Overall Status: {:?}</p>
    
    <div class="summary">
        <div class="metric">
            <div class="metric-value">{}</div>
            <div class="metric-label">Total Projects</div>
        </div>
        <div class="metric">
            <div class="metric-value">{}</div>
            <div class="metric-label">Healthy</div>
        </div>
        <div class="metric">
            <div class="metric-value">{}</div>
            <div class="metric-label">Degraded</div>
        </div>
        <div class="metric">
            <div class="metric-value">{}</div>
            <div class="metric-label">Unhealthy</div>
        </div>
    </div>

    <h2>Findings</h2>
    <div class="summary">
        <div class="metric">
            <div class="metric-value" style="color: #da3633">{}</div>
            <div class="metric-label">Critical</div>
        </div>
        <div class="metric">
            <div class="metric-value" style="color: #d29922">{}</div>
            <div class="metric-label">High</div>
        </div>
        <div class="metric">
            <div class="metric-value">{}</div>
            <div class="metric-label">Medium</div>
        </div>
        <div class="metric">
            <div class="metric-value">{}</div>
            <div class="metric-label">Low</div>
        </div>
    </div>

    <h2>Projects</h2>
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Compliance Score</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {}
        </tbody>
    </table>
</body>
</html>"#,
        chrono::Local::now().format("%Y-%m-%d %H:%M"),
        status_class,
        status_color,
        report.status,
        report.metrics.total_projects,
        report.metrics.healthy_projects,
        report.metrics.degraded_projects,
        report.metrics.unhealthy_projects,
        report.metrics.critical_findings,
        report.metrics.high_findings,
        report.metrics.medium_findings,
        report.metrics.low_findings,
        projects_rows
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_unified_scanner_creation() {
        let scanner = UnifiedHealthScanner::new();
        // Just verify it creates without panic
        #[cfg(feature = "health-registry")]
        assert!(scanner.health_registry.is_empty());
    }

    #[tokio::test]
    async fn test_quick_check_nonexistent() {
        let mut scanner = UnifiedHealthScanner::new();
        let result = scanner.quick_check("/nonexistent/path").await;

        assert_eq!(format!("{:?}", result.project_type), "Unknown");
        assert!(result.compliance_score < 100.0); // Should have findings for missing docs
    }

    #[test]
    fn test_json_report_generation() {
        let report = UnifiedHealthReport {
            status: HealthStatus::Healthy,
            projects: vec![ProjectSummary {
                name: "test-project".to_string(),
                project_type: ProjectType::RustLibrary,
                path: "/test".to_string(),
                has_health_config: true,
                compliance_score: 95.0,
                security_risk_score: 10.0,
                status: HealthStatus::Healthy,
            }],
            compliance_findings: vec![],
            security_findings: vec![],
            metrics: HealthMetrics {
                total_projects: 1,
                healthy_projects: 1,
                degraded_projects: 0,
                unhealthy_projects: 0,
                critical_findings: 0,
                high_findings: 0,
                medium_findings: 0,
                low_findings: 0,
            },
        };

        let json = generate_json_report(&report);
        assert!(json.contains("test-project"));
        assert!(json.contains("95.0"));
    }

    #[test]
    fn test_table_report_generation() {
        let report = UnifiedHealthReport {
            status: HealthStatus::Degraded,
            projects: vec![
                ProjectSummary {
                    name: "proj1".to_string(),
                    project_type: ProjectType::RustLibrary,
                    path: "/p1".to_string(),
                    has_health_config: false,
                    compliance_score: 85.0,
                    security_risk_score: 15.0,
                    status: HealthStatus::Degraded,
                },
                ProjectSummary {
                    name: "proj2".to_string(),
                    project_type: ProjectType::GoModule,
                    path: "/p2".to_string(),
                    has_health_config: true,
                    compliance_score: 60.0,
                    security_risk_score: 20.0,
                    status: HealthStatus::Unhealthy,
                },
            ],
            compliance_findings: vec![],
            security_findings: vec![],
            metrics: HealthMetrics {
                total_projects: 2,
                healthy_projects: 0,
                degraded_projects: 1,
                unhealthy_projects: 1,
                critical_findings: 0,
                high_findings: 1,
                medium_findings: 0,
                low_findings: 2,
            },
        };

        let table = generate_table_report(&report);
        assert!(table.contains("UNIFIED HEALTH REPORT"));
        assert!(table.contains("proj1"));
        assert!(table.contains("proj2"));
        assert!(table.contains("Degraded"));
    }
}

/// Configuration file support
pub mod config {
    use serde::{Deserialize, Serialize};
    use std::collections::HashMap;
    use std::path::Path;

    /// Main configuration structure
    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct HealthConfig {
        /// Scan settings
        pub scan: ScanConfig,
        /// Server settings (for `serve` command)
        pub server: ServerConfig,
        /// Webhook notifications
        #[serde(default)]
        pub webhooks: Vec<WebhookConfig>,
        /// Output preferences
        pub output: OutputConfig,
        /// Ignore patterns
        #[serde(default)]
        pub ignore: Vec<String>,
    }

    impl Default for HealthConfig {
        fn default() -> Self {
            Self {
                scan: ScanConfig::default(),
                server: ServerConfig::default(),
                webhooks: Vec::new(),
                output: OutputConfig::default(),
                ignore: vec![
                    "target".to_string(),
                    "node_modules".to_string(),
                    ".git".to_string(),
                    "__pycache__".to_string(),
                ],
            }
        }
    }

    impl HealthConfig {
        /// Load configuration from file
        pub fn load(path: impl AsRef<Path>) -> anyhow::Result<Self> {
            let content = std::fs::read_to_string(path)?;
            let config: HealthConfig = toml::from_str(&content)?;
            Ok(config)
        }

        /// Load from default locations
        pub fn load_default() -> Self {
            let candidates = [
                ".phenotype-health.toml",
                "phenotype-health.toml",
                ".config/phenotype-health.toml",
            ];

            for candidate in &candidates {
                if let Ok(config) = Self::load(candidate) {
                    return config;
                }
            }

            Self::default()
        }

        /// Save configuration to file
        pub fn save(&self, path: impl AsRef<Path>) -> anyhow::Result<()> {
            let content = toml::to_string_pretty(self)?;
            std::fs::write(path, content)?;
            Ok(())
        }
    }

    /// Scan configuration
    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct ScanConfig {
        /// Maximum concurrent scans
        #[serde(default = "default_concurrency")]
        pub concurrency: usize,
        /// Timeout per project scan (seconds)
        #[serde(default = "default_timeout")]
        pub timeout_seconds: u64,
        /// Enable security scanning
        #[serde(default = "default_true")]
        pub security_scan: bool,
        /// Enable compliance scanning
        #[serde(default = "default_true")]
        pub compliance_scan: bool,
        /// Custom rules path
        pub rules_path: Option<String>,
    }

    impl Default for ScanConfig {
        fn default() -> Self {
            Self {
                concurrency: default_concurrency(),
                timeout_seconds: default_timeout(),
                security_scan: true,
                compliance_scan: true,
                rules_path: None,
            }
        }
    }

    /// Server configuration
    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct ServerConfig {
        /// Bind address
        #[serde(default = "default_bind")]
        pub bind: String,
        /// Port
        #[serde(default = "default_port")]
        pub port: u16,
        /// Enable auto-reload
        #[serde(default)]
        pub auto_reload: bool,
        /// Static files path
        pub static_path: Option<String>,
    }

    impl Default for ServerConfig {
        fn default() -> Self {
            Self {
                bind: default_bind(),
                port: default_port(),
                auto_reload: false,
                static_path: None,
            }
        }
    }

    /// Webhook configuration
    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct WebhookConfig {
        /// Webhook URL
        pub url: String,
        /// Trigger events
        #[serde(default)]
        pub events: Vec<String>,
        /// Custom headers
        #[serde(default)]
        pub headers: HashMap<String, String>,
        /// Retry attempts
        #[serde(default = "default_retries")]
        pub retries: u32,
    }

    /// Output configuration
    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct OutputConfig {
        /// Default format
        #[serde(default = "default_format")]
        pub format: String,
        /// Enable colors
        #[serde(default = "default_true")]
        pub colors: bool,
        /// Verbose output
        #[serde(default)]
        pub verbose: bool,
        /// Report output path
        pub report_path: Option<String>,
    }

    impl Default for OutputConfig {
        fn default() -> Self {
            Self {
                format: default_format(),
                colors: true,
                verbose: false,
                report_path: None,
            }
        }
    }

    fn default_concurrency() -> usize {
        4
    }

    fn default_timeout() -> u64 {
        30
    }

    fn default_bind() -> String {
        "127.0.0.1".to_string()
    }

    fn default_port() -> u16 {
        8080
    }

    fn default_retries() -> u32 {
        3
    }

    fn default_format() -> String {
        "table".to_string()
    }

    fn default_true() -> bool {
        true
    }

    /// Generate default config file content
    pub fn generate_default_config() -> String {
        r#"# Phenotype Health Configuration
# See: https://github.com/phenotype-org/phenotype/tree/main/crates/phenotype-health-cli

[scan]
# Maximum concurrent project scans
concurrency = 4
# Timeout per project (seconds)
timeout_seconds = 30
# Enable security scanning
security_scan = true
# Enable compliance scanning
compliance_scan = true

[server]
# Server bind address
bind = "127.0.0.1"
# Server port
port = 8080
# Enable auto-reload on file changes
auto_reload = false

[output]
# Default output format: table, json, yaml, html
format = "table"
# Enable colored output
colors = true
# Verbose output
verbose = false

# Ignore patterns (directories to skip)
ignore = [
    "target",
    "node_modules",
    ".git",
    "__pycache__",
    "dist",
    "build",
]

# Webhook notifications (optional)
# [[webhooks]]
# url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
# events = ["health_change", "critical_finding"]
# retries = 3
"#
        .to_string()
    }
}

/// Webhook notification support
pub mod webhook {
    use phenotype_health::HealthStatus;
    use serde_json::json;
    use std::collections::HashMap;

    /// Webhook payload
    #[derive(Debug, Clone)]
    pub struct WebhookPayload {
        pub event: String,
        pub timestamp: chrono::DateTime<chrono::Utc>,
        pub data: serde_json::Value,
    }

    impl WebhookPayload {
        /// Create a health change payload
        pub fn health_change(
            project: &str,
            old_status: HealthStatus,
            new_status: HealthStatus,
        ) -> Self {
            Self {
                event: "health_change".to_string(),
                timestamp: chrono::Utc::now(),
                data: json!({
                    "project": project,
                    "old_status": format!("{:?}", old_status),
                    "new_status": format!("{:?}", new_status),
                    "message": format!(
                        "Project {} health changed from {:?} to {:?}",
                        project, old_status, new_status
                    ),
                }),
            }
        }

        /// Create a critical finding payload
        pub fn critical_finding(project: &str, finding: &str) -> Self {
            Self {
                event: "critical_finding".to_string(),
                timestamp: chrono::Utc::now(),
                data: json!({
                    "project": project,
                    "finding": finding,
                    "severity": "critical",
                    "message": format!("Critical finding in {}: {}", project, finding),
                }),
            }
        }

        /// Serialize to JSON
        pub fn to_json(&self) -> String {
            json!({
                "event": self.event,
                "timestamp": self.timestamp,
                "data": self.data,
            })
            .to_string()
        }
    }

    /// Webhook notifier
    pub struct WebhookNotifier {
        client: reqwest::Client,
        urls: Vec<String>,
        headers: HashMap<String, String>,
    }

    impl WebhookNotifier {
        /// Create a new notifier
        pub fn new(urls: Vec<String>) -> Self {
            Self {
                client: reqwest::Client::new(),
                urls,
                headers: HashMap::new(),
            }
        }

        /// Add custom headers
        pub fn with_headers(mut self, headers: HashMap<String, String>) -> Self {
            self.headers = headers;
            self
        }

        /// Send a webhook notification
        pub async fn notify(&self, payload: &WebhookPayload) -> Result<(), WebhookError> {
            let body = payload.to_json();

            for url in &self.urls {
                let mut request = self.client.post(url).body(body.clone());

                // Add custom headers
                for (key, value) in &self.headers {
                    request = request.header(key, value);
                }

                // Add content type
                request = request.header("Content-Type", "application/json");

                match request.send().await {
                    Ok(response) => {
                        if !response.status().is_success() {
                            tracing::warn!("Webhook {} returned status {}", url, response.status());
                        }
                    }
                    Err(e) => {
                        tracing::error!("Failed to send webhook to {}: {}", url, e);
                        return Err(WebhookError::SendFailed(e.to_string()));
                    }
                }
            }

            Ok(())
        }

        /// Send health change notification
        pub async fn notify_health_change(
            &self,
            project: &str,
            old_status: HealthStatus,
            new_status: HealthStatus,
        ) -> Result<(), WebhookError> {
            let payload = WebhookPayload::health_change(project, old_status, new_status);
            self.notify(&payload).await
        }
    }

    /// Webhook errors
    #[derive(Debug)]
    pub enum WebhookError {
        SendFailed(String),
        InvalidUrl(String),
    }

    impl std::fmt::Display for WebhookError {
        fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            match self {
                WebhookError::SendFailed(msg) => write!(f, "Failed to send webhook: {}", msg),
                WebhookError::InvalidUrl(url) => write!(f, "Invalid webhook URL: {}", url),
            }
        }
    }

    impl std::error::Error for WebhookError {}
}
