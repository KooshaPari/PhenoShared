//! Health check integration for security aggregator
//!
//! Provides health monitoring based on security findings.

use crate::{AlertSource, Finding, SecurityAggregator, SecurityError, SecurityReport, Severity};
use phenotype_health::{
    ComponentHealthCheck, HealthCheck, HealthRegistry, HealthReport, HealthStatus, ReportSummary,
};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::time::timeout;
use tracing::{debug, error, info, warn};

/// Health check based on security findings
#[derive(Debug)]
pub struct SecurityHealthCheck {
    aggregator: Arc<SecurityAggregator>,
}

impl SecurityHealthCheck {
    /// Create a new security health check
    pub fn new(aggregator: Arc<SecurityAggregator>) -> Self {
        Self { aggregator }
    }
}

#[async_trait::async_trait]
impl HealthCheck for SecurityHealthCheck {
    fn name(&self) -> &str {
        "security"
    }

    async fn check(&self) -> Result<HealthStatus, phenotype_health::HealthCheckError> {
        // Run aggregation with a timeout
        match timeout(Duration::from_secs(60), self.aggregator.aggregate()).await {
            Ok(Ok(report)) => {
                // Determine health based on findings
                if report.summary.critical > 0 {
                    Ok(HealthStatus::Unhealthy)
                } else if report.summary.high > 0 {
                    Ok(HealthStatus::Degraded)
                } else {
                    Ok(HealthStatus::Healthy)
                }
            }
            Ok(Err(e)) => {
                warn!("Security aggregation failed: {}", e);
                Err(phenotype_health::HealthCheckError::CheckFailed(
                    e.to_string(),
                ))
            }
            Err(_) => {
                warn!("Security aggregation timed out");
                Err(phenotype_health::HealthCheckError::Timeout)
            }
        }
    }
}

/// Security health monitor
///
/// Monitors security status and provides health reports
#[derive(Debug)]
pub struct SecurityHealthMonitor {
    aggregator: Arc<SecurityAggregator>,
}

impl SecurityHealthMonitor {
    /// Create a new security health monitor
    pub fn new(aggregator: Arc<SecurityAggregator>) -> Self {
        Self { aggregator }
    }

    /// Check security health
    pub async fn check(&self) -> Result<HealthReport, SecurityError> {
        let report = self.aggregator.aggregate().await?;
        Ok(security_report_to_health_report(&report))
    }

    /// Get the underlying aggregator
    pub fn aggregator(&self) -> &Arc<SecurityAggregator> {
        &self.aggregator
    }

    /// Get a health score (0-100)
    pub async fn health_score(&self) -> Result<u8, SecurityError> {
        let report = self.aggregator.aggregate().await?;
        Ok(security_health_score(&report))
    }
}

impl Default for SecurityHealthMonitor {
    fn default() -> Self {
        Self::new(Arc::new(SecurityAggregator::new()))
    }
}

/// Convert security report to health report
fn security_report_to_health_report(security_report: &SecurityReport) -> HealthReport {
    let mut snapshots = Vec::new();

    // Group findings by severity and create health snapshots
    for finding in &security_report.findings {
        let status = match finding.severity {
            Severity::Critical => HealthStatus::Unhealthy,
            Severity::High => HealthStatus::Unhealthy,
            Severity::Medium => HealthStatus::Degraded,
            Severity::Low => HealthStatus::Degraded,
            Severity::Info => HealthStatus::Healthy,
        };

        snapshots.push(phenotype_health::HealthSnapshot {
            component: format!("{}: {} ({})", finding.source.short_name(), finding.id, finding.title),
            status,
            timestamp: finding.created_at,
            latency_ms: None,
            error: Some(finding.description.clone()),
        });
    }

    // Calculate overall status
    let overall = if security_report.summary.critical > 0 {
        HealthStatus::Unhealthy
    } else if security_report.summary.high > 0 {
        HealthStatus::Unhealthy
    } else if security_report.summary.medium > 0 {
        HealthStatus::Degraded
    } else if security_report.summary.low > 0 {
        HealthStatus::Degraded
    } else {
        HealthStatus::Healthy
    };

    HealthReport {
        overall_status: overall,
        checks: snapshots,
        summary: ReportSummary {
            total: security_report.findings.len(),
            healthy: snapshots.iter().filter(|s| s.status == HealthStatus::Healthy).count(),
            degraded: snapshots.iter().filter(|s| s.status == HealthStatus::Degraded).count(),
            unhealthy: snapshots.iter().filter(|s| s.status == HealthStatus::Unhealthy).count(),
        },
    }
}

/// Calculate security health score (0-100)
///
/// Returns 100 for no security issues, lower for projects with vulnerabilities
pub fn security_health_score(report: &SecurityReport) -> u8 {
    let total_findings = report.summary.total as f32;
    if total_findings == 0.0 {
        return 100;
    }

    // Weight findings by severity
    let critical_weight = report.summary.critical as f32 * 25.0;
    let high_weight = report.summary.high as f32 * 10.0;
    let medium_weight = report.summary.medium as f32 * 3.0;
    let low_weight = report.summary.low as f32 * 1.0;
    let info_weight = report.summary.info as f32 * 0.1;

    let total_weight = critical_weight + high_weight + medium_weight + low_weight + info_weight;
    let score = 100.0 - (total_weight / total_findings).min(100.0);

    score as u8
}

/// Security health summary for reporting
#[derive(Debug, Clone)]
pub struct SecurityHealthSummary {
    /// Overall health status
    pub status: HealthStatus,
    /// Security health score (0-100)
    pub score: u8,
    /// Number of critical findings
    pub critical_count: usize,
    /// Number of high findings
    pub high_count: usize,
    /// Total findings
    pub total_findings: usize,
    /// Number of data sources
    pub sources: usize,
}

impl SecurityHealthSummary {
    /// Create from a security report
    pub fn from_security_report(report: &SecurityReport) -> Self {
        Self {
            status: if report.summary.critical > 0 {
                HealthStatus::Unhealthy
            } else if report.summary.high > 0 {
                HealthStatus::Degraded
            } else {
                HealthStatus::Healthy
            },
            score: security_health_score(report),
            critical_count: report.summary.critical,
            high_count: report.summary.high,
            total_findings: report.summary.total,
            sources: report.summary.sources,
        }
    }
}

/// Check health for a specific source
pub async fn check_source_health(
    aggregator: &SecurityAggregator,
    source_name: &str,
) -> Result<HealthStatus, SecurityError> {
    let report = aggregator.aggregate().await?;

    // Find findings from this specific source
    let source_findings: Vec<&Finding> = report
        .findings
        .iter()
        .filter(|f| f.source.short_name().to_lowercase() == source_name.to_lowercase())
        .collect();

    if source_findings.is_empty() {
        return Ok(HealthStatus::Healthy);
    }

    let has_critical = source_findings.iter().any(|f| f.severity == Severity::Critical);
    let has_high = source_findings.iter().any(|f| f.severity == Severity::High);

    if has_critical {
        Ok(HealthStatus::Unhealthy)
    } else if has_high {
        Ok(HealthStatus::Degraded)
    } else {
        Ok(HealthStatus::Healthy)
    }
}

/// Aggregate security findings and return health status by source
pub async fn health_by_source(
    aggregator: &SecurityAggregator,
) -> Result<HashMap<String, HealthStatus>, SecurityError> {
    let report = aggregator.aggregate().await?;
    let mut status_by_source: HashMap<String, HealthStatus> = HashMap::new();

    // Group findings by source
    for finding in &report.findings {
        let source_name = finding.source.short_name().to_string();
        let entry = status_by_source.entry(source_name).or_insert(HealthStatus::Healthy);

        // Update status based on this finding
        if finding.severity == Severity::Critical {
            *entry = HealthStatus::Unhealthy;
        } else if finding.severity == Severity::High && *entry != HealthStatus::Unhealthy {
            *entry = HealthStatus::Degraded;
        } else if finding.severity == Severity::Medium
            && *entry == HealthStatus::Healthy
        {
            *entry = HealthStatus::Degraded;
        }
    }

    Ok(status_by_source)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_security_health_score_perfect() {
        let report = SecurityReport {
            summary: crate::ReportSummary {
                total: 0,
                critical: 0,
                high: 0,
                medium: 0,
                low: 0,
                info: 0,
                sources: 0,
            },
            ..Default::default()
        };

        assert_eq!(security_health_score(&report), 100);
    }

    #[test]
    fn test_security_health_score_with_findings() {
        let report = SecurityReport {
            summary: crate::ReportSummary {
                total: 10,
                critical: 1,
                high: 2,
                medium: 3,
                low: 4,
                info: 0,
                sources: 1,
            },
            ..Default::default()
        };

        let score = security_health_score(&report);
        assert!(score < 100);
        assert!(score > 0);
    }

    #[tokio::test]
    async fn test_security_health_monitor() {
        let aggregator = Arc::new(SecurityAggregator::new());
        let monitor = SecurityHealthMonitor::new(aggregator);

        let report = monitor.check().await.unwrap();
        // Should be healthy with no sources
        assert_eq!(report.overall_status, HealthStatus::Healthy);
    }
}
