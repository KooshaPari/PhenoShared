//! Security alert aggregation from multiple sources (Snyk, CodeQL, Dependabot, etc.).
//!
//! Provides unified security posture tracking for project health dashboards.

#![warn(missing_docs)]

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use phenotype_health::{DimensionScore, Finding, Severity};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tracing::debug;

/// Aggregates security alerts from multiple sources
#[derive(Debug, Clone)]
pub struct SecurityAggregator {
    sources: Vec<Box<dyn SecuritySource>>,
}

impl SecurityAggregator {
    /// Create a new aggregator
    pub fn new() -> Self {
        Self {
            sources: Vec::new(),
        }
    }

    /// Add a security source to aggregate from
    pub fn add_source(&mut self, source: impl SecuritySource + 'static) {
        self.sources.push(Box::new(source));
    }

    /// Aggregate security score from all configured sources
    pub async fn aggregate_security_score(
        &self,
        owner: &str,
        repo: &str,
    ) -> anyhow::Result<DimensionScore> {
        let mut all_alerts = Vec::new();

        for source in &self.sources {
            match source.fetch_alerts(owner, repo).await {
                Ok(alerts) => {
                    debug!("Fetched {} alerts from source", alerts.len());
                    all_alerts.extend(alerts);
                }
                Err(e) => {
                    tracing::warn!("Security source failed: {}", e);
                }
            }
        }

        // Calculate score based on severity counts
        let critical = all_alerts
            .iter()
            .filter(|a| matches!(a.severity, Severity::Critical))
            .count();
        let high = all_alerts
            .iter()
            .filter(|a| matches!(a.severity, Severity::Error))
            .count();
        let medium = all_alerts
            .iter()
            .filter(|a| matches!(a.severity, Severity::Warning))
            .count();

        let score = 100.0_f32
            .saturating_sub(critical as f32 * 25.0)
            .saturating_sub(high as f32 * 10.0)
            .saturating_sub(medium as f32 * 2.0);

        let findings: Vec<Finding> = all_alerts
            .iter()
            .map(|a| Finding {
                severity: a.severity,
                message: format!(
                    "[{}] {}: {}",
                    a.source.short_name(),
                    a.package_name.as_deref().unwrap_or("unknown"),
                    a.title
                ),
                file_path: None,
                line_number: None,
            })
            .collect();

        Ok(DimensionScore {
            score,
            target: 100.0,
            raw_value: all_alerts.len() as f32,
            unit: "alerts".to_string(),
            findings,
        })
    }
}

impl Default for SecurityAggregator {
    fn default() -> Self {
        Self::new()
    }
}

/// Trait for security alert sources
#[async_trait]
pub trait SecuritySource: Send + Sync {
    /// Fetch alerts for a specific repository
    async fn fetch_alerts(&self, owner: &str, repo: &str) -> anyhow::Result<Vec<SecurityAlert>>;
}

/// Security alert from any source
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityAlert {
    /// Source of the alert
    pub source: AlertSource,
    /// Alert severity
    pub severity: Severity,
    /// Alert title
    pub title: String,
    /// Detailed description
    pub description: String,
    /// CVE ID if applicable
    pub cve_id: Option<String>,
    /// Affected package name
    pub package_name: Option<String>,
    /// Affected versions
    pub affected_versions: Option<String>,
    /// Fixed version if available
    pub fixed_version: Option<String>,
    /// When the alert was detected
    pub detected_at: DateTime<Utc>,
}

impl AlertSource {
    /// Get short name for display
    pub fn short_name(&self) -> &'static str {
        match self {
            AlertSource::Snyk => "SNYK",
            AlertSource::CodeQL => "CODEQL",
            AlertSource::CargoAudit => "CARGO",
            AlertSource::Dependabot => "DEPND",
            AlertSource::Trivy => "TRIVY",
            AlertSource::Custom(s) => s,
        }
    }
}

/// Source of a security alert
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AlertSource {
    /// Snyk vulnerability scanner
    Snyk,
    /// GitHub CodeQL analysis
    CodeQL,
    /// Rust cargo audit
    CargoAudit,
    /// GitHub Dependabot
    Dependabot,
    /// Trivy container/file scanner
    Trivy,
    /// Custom source
    Custom(String),
}

/// GitHub Dependabot security source
#[derive(Debug, Clone)]
pub struct GitHubDependabotSource {
    client: reqwest::Client,
    token: String,
}

impl GitHubDependabotSource {
    /// Create a new GitHub Dependabot source
    pub fn new(token: String) -> Self {
        Self {
            client: reqwest::Client::new(),
            token,
        }
    }
}

#[async_trait]
impl SecuritySource for GitHubDependabotSource {
    async fn fetch_alerts(
        &self,
        owner: &str,
        repo: &str,
    ) -> anyhow::Result<Vec<SecurityAlert>> {
        let url = format!(
            "https://api.github.com/repos/{}/{}/dependabot/alerts",
            owner, repo
        );

        let _response = self
            .client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.token))
            .header("Accept", "application/vnd.github+json")
            .header("X-GitHub-Api-Version", "2022-11-28")
            .send()
            .await?;

        // TODO: Parse JSON response into SecurityAlert structs
        // For now, return empty vec until full implementation
        Ok(Vec::new())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_aggregator() {
        let aggregator = SecurityAggregator::new();
        assert_eq!(aggregator.sources.len(), 0);
    }

    #[test]
    fn test_alert_source_short_name() {
        assert_eq!(AlertSource::Snyk.short_name(), "SNYK");
        assert_eq!(AlertSource::Dependabot.short_name(), "DEPND");
        assert_eq!(AlertSource::Custom("TEST".to_string()).short_name(), "TEST");
    }
}
