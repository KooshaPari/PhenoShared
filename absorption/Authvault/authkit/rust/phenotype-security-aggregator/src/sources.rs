//! Real security source implementations
//!
//! Provides actual implementations for fetching security data from:
//! - GitHub Security Advisories
//! - Snyk API
//! - Cargo Audit (for Rust projects)
//! - OSV (Open Source Vulnerabilities) database

use crate::{AlertSource, Finding, SecurityError, SecuritySource, Severity};
use async_trait::async_trait;
use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;
use std::process::Command;
use tracing::{debug, error, info, warn};

/// GitHub Security Advisory source
pub struct GitHubSecuritySource {
    owner: String,
    repo: String,
    token: Option<String>,
    client: reqwest::Client,
}

impl GitHubSecuritySource {
    /// Create a new GitHub security source
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use phenotype_security_aggregator::sources::GitHubSecuritySource;
    ///
    /// let source = GitHubSecuritySource::new("owner", "repo");
    /// ```
    pub fn new(owner: impl Into<String>, repo: impl Into<String>) -> Self {
        let token = std::env::var("GITHUB_TOKEN").ok();

        Self {
            owner: owner.into(),
            repo: repo.into(),
            token,
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(30))
                .build()
                .expect("Failed to create HTTP client"),
        }
    }

    /// Set authentication token
    pub fn with_token(mut self, token: impl Into<String>) -> Self {
        self.token = Some(token.into());
        self
    }
}

#[derive(Debug, Deserialize)]
struct GitHubAlert {
    number: i64,
    security_advisory: Option<GitHubAdvisory>,
    security_vulnerability: Option<GitHubVulnerability>,
    state: String,
}

#[derive(Debug, Deserialize)]
struct GitHubAdvisory {
    ghsa_id: String,
    summary: String,
    description: String,
    severity: String,
    cvss: Option<GitHubCvss>,
}

#[derive(Debug, Deserialize)]
struct GitHubCvss {
    score: f32,
}

#[derive(Debug, Deserialize)]
struct GitHubVulnerability {
    package: GitHubPackage,
}

#[derive(Debug, Deserialize)]
struct GitHubPackage {
    name: String,
}

#[async_trait]
impl SecuritySource for GitHubSecuritySource {
    fn name(&self) -> &str {
        "github-security"
    }

    async fn fetch_findings(&self) -> Result<Vec<Finding>, SecurityError> {
        let url = format!(
            "https://api.github.com/repos/{}/{}/dependabot/alerts",
            self.owner, self.repo
        );

        info!("Fetching GitHub security alerts for {}/{}", self.owner, self.repo);

        let mut request = self.client.get(&url);

        if let Some(token) = &self.token {
            request = request.header("Authorization", format!("token {}", token));
        }

        request = request
            .header("Accept", "application/vnd.github+json")
            .header("X-GitHub-Api-Version", "2022-11-28");

        let response = request
            .send()
            .await
            .map_err(|e| SecurityError::SourceError(e.to_string()))?;

        if !response.status().is_success() {
            return Err(SecurityError::SourceError(format!(
                "GitHub API returned status: {}",
                response.status()
            )));
        }

        let alerts: Vec<GitHubAlert> = response
            .json()
            .await
            .map_err(|e| SecurityError::ParseError(e.to_string()))?;

        let findings: Vec<Finding> = alerts
            .into_iter()
            .filter(|alert| alert.state == "open")
            .filter_map(|alert| {
                alert.security_advisory.map(|advisory| {
                    let severity = parse_severity(&advisory.severity);
                    let package_name = alert
                        .security_vulnerability
                        .as_ref()
                        .map(|v| v.package.name.clone())
                        .unwrap_or_else(|| "unknown".to_string());

                    Finding::new(
                        format!("GHSA-{}", advisory.ghsa_id),
                        advisory.summary,
                        severity,
                        AlertSource::Dependabot,
                    )
                    .with_description(advisory.description)
                    .with_cvss(advisory.cvss.map(|c| c.score).unwrap_or(0.0))
                })
            })
            .collect();

        info!("Found {} security alerts from GitHub", findings.len());
        Ok(findings)
    }
}

/// Cargo Audit source for Rust projects
pub struct CargoAuditSource {
    project_path: std::path::PathBuf,
}

impl CargoAuditSource {
    /// Create a new cargo audit source
    pub fn new(project_path: impl AsRef<Path>) -> Self {
        Self {
            project_path: project_path.as_ref().to_path_buf(),
        }
    }
}

#[derive(Debug, Deserialize)]
struct AuditOutput {
    vulnerabilities: AuditVulnerabilities,
}

#[derive(Debug, Deserialize)]
struct AuditVulnerabilities {
    list: Vec<AuditVulnerability>,
}

#[derive(Debug, Deserialize)]
struct AuditVulnerability {
    package: AuditPackage,
    advisory: AuditAdvisory,
}

#[derive(Debug, Deserialize)]
struct AuditPackage {
    name: String,
    version: String,
}

#[derive(Debug, Deserialize)]
struct AuditAdvisory {
    id: String,
    title: String,
    description: String,
}

#[async_trait]
impl SecuritySource for CargoAuditSource {
    fn name(&self) -> &str {
        "cargo-audit"
    }

    async fn fetch_findings(&self) -> Result<Vec<Finding>, SecurityError> {
        info!("Running cargo audit for {}", self.project_path.display());

        // Run cargo audit as a blocking operation
        let output = tokio::task::spawn_blocking({
            let path = self.project_path.clone();
            move || {
                Command::new("cargo")
                    .args(["audit", "--json", "-d", path.to_str().unwrap_or(".")])
                    .output()
            }
        })
        .await
        .map_err(|e| SecurityError::SourceError(e.to_string()))?;

        match output {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(&output.stdout);

                // Parse JSON output
                let audit_output: AuditOutput = serde_json::from_str(&stdout)
                    .map_err(|e| SecurityError::ParseError(e.to_string()))?;

                let findings: Vec<Finding> = audit_output
                    .vulnerabilities
                    .list
                    .into_iter()
                    .map(|v| {
                        Finding::new(
                            v.advisory.id,
                            v.advisory.title,
                            Severity::High, // Cargo audit doesn't provide severity
                            AlertSource::CargoAudit,
                        )
                        .with_description(v.advisory.description)
                        .with_file(
                            format!("{}@{}\n", v.package.name, v.package.version),
                            0,
                        )
                    })
                    .collect();

                info!("Found {} vulnerabilities from cargo audit", findings.len());
                Ok(findings)
            }
            Err(e) => {
                warn!("cargo audit failed: {}", e);
                // Return empty if cargo audit is not available
                Ok(Vec::new())
            }
        }
    }
}

/// OSV (Open Source Vulnerabilities) source
pub struct OsvSource {
    package_name: String,
    ecosystem: String,
    version: String,
    client: reqwest::Client,
}

impl OsvSource {
    /// Create a new OSV source
    pub fn new(
        package_name: impl Into<String>,
        ecosystem: impl Into<String>,
        version: impl Into<String>,
    ) -> Self {
        Self {
            package_name: package_name.into(),
            ecosystem: ecosystem.into(),
            version: version.into(),
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(30))
                .build()
                .expect("Failed to create HTTP client"),
        }
    }
}

#[derive(Debug, Serialize)]
struct OsvQuery {
    package: OsvPackage,
    version: String,
}

#[derive(Debug, Serialize)]
struct OsvPackage {
    name: String,
    ecosystem: String,
}

#[derive(Debug, Deserialize)]
struct OsvResponse {
    vulns: Option<Vec<OsvVulnerability>>,
}

#[derive(Debug, Deserialize)]
struct OsvVulnerability {
    id: String,
    summary: Option<String>,
    details: Option<String>,
    severity: Option<Vec<OsvSeverity>>,
}

#[derive(Debug, Deserialize)]
struct OsvSeverity {
    r#type: String,
    score: String,
}

#[async_trait]
impl SecuritySource for OsvSource {
    fn name(&self) -> &str {
        "osv"
    }

    async fn fetch_findings(&self) -> Result<Vec<Finding>, SecurityError> {
        let url = "https://api.osv.dev/v1/query";

        info!(
            "Querying OSV for {} {}@{}",
            self.ecosystem, self.package_name, self.version
        );

        let query = OsvQuery {
            package: OsvPackage {
                name: self.package_name.clone(),
                ecosystem: self.ecosystem.clone(),
            },
            version: self.version.clone(),
        };

        let response = self
            .client
            .post(url)
            .json(&query)
            .send()
            .await
            .map_err(|e| SecurityError::SourceError(e.to_string()))?;

        if !response.status().is_success() {
            return Err(SecurityError::SourceError(format!(
                "OSV API returned status: {}",
                response.status()
            )));
        }

        let osv_response: OsvResponse = response
            .json()
            .await
            .map_err(|e| SecurityError::ParseError(e.to_string()))?;

        let findings: Vec<Finding> = osv_response
            .vulns
            .unwrap_or_default()
            .into_iter()
            .map(|vuln| {
                let severity = vuln
                    .severity
                    .as_ref()
                    .and_then(|s| s.first())
                    .map(|s| parse_cvss_score(&s.score))
                    .unwrap_or(Severity::Medium);

                Finding::new(
                    vuln.id,
                    vuln.summary.unwrap_or_else(|| "Unknown vulnerability".to_string()),
                    severity,
                    AlertSource::Custom("OSV".to_string()),
                )
                .with_description(vuln.details.unwrap_or_default())
            })
            .collect();

        info!("Found {} vulnerabilities from OSV", findings.len());
        Ok(findings)
    }
}

/// Snyk security source
pub struct SnykSource {
    org_id: String,
    project_id: Option<String>,
    token: String,
    client: reqwest::Client,
}

impl SnykSource {
    /// Create a new Snyk source
    pub fn new(org_id: impl Into<String>) -> Result<Self, SecurityError> {
        let token = std::env::var("SNYK_TOKEN")
            .map_err(|_| SecurityError::SourceError("SNYK_TOKEN not set".to_string()))?;

        Ok(Self {
            org_id: org_id.into(),
            project_id: None,
            token,
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(30))
                .build()
                .expect("Failed to create HTTP client"),
        })
    }

    /// Set a specific project ID to query
    pub fn with_project(mut self, project_id: impl Into<String>) -> Self {
        self.project_id = Some(project_id.into());
        self
    }
}

#[derive(Debug, Deserialize)]
struct SnykIssues {
    issues: Vec<SnykIssue>,
}

#[derive(Debug, Deserialize)]
struct SnykIssue {
    id: String,
    title: String,
    severity: String,
    #[serde(rename = "CVSSv3")]
    cvss_v3: Option<String>,
}

#[async_trait]
impl SecuritySource for SnykSource {
    fn name(&self) -> &str {
        "snyk"
    }

    async fn fetch_findings(&self) -> Result<Vec<Finding>, SecurityError> {
        let url = if let Some(project_id) = &self.project_id {
            format!(
                "https://api.snyk.io/rest/orgs/{}/projects/{}/issues",
                self.org_id, project_id
            )
        } else {
            format!("https://api.snyk.io/rest/orgs/{}/issues", self.org_id)
        };

        info!("Fetching Snyk issues for org {}", self.org_id);

        let response = self
            .client
            .get(&url)
            .header("Authorization", format!("token {}", self.token))
            .header("Accept", "application/vnd.api+json")
            .send()
            .await
            .map_err(|e| SecurityError::SourceError(e.to_string()))?;

        if !response.status().is_success() {
            return Err(SecurityError::SourceError(format!(
                "Snyk API returned status: {}",
                response.status()
            )));
        }

        let issues: SnykIssues = response
            .json()
            .await
            .map_err(|e| SecurityError::ParseError(e.to_string()))?;

        let findings: Vec<Finding> = issues
            .issues
            .into_iter()
            .map(|issue| {
                let severity = parse_severity(&issue.severity);
                let cvss_score = issue
                    .cvss_v3
                    .as_ref()
                    .and_then(|s| s.parse::<f32>().ok())
                    .unwrap_or(0.0);

                Finding::new(issue.id, issue.title, severity, AlertSource::Snyk)
                    .with_cvss(cvss_score)
            })
            .collect();

        info!("Found {} issues from Snyk", findings.len());
        Ok(findings)
    }
}

/// Parse severity string to Severity enum
fn parse_severity(severity: &str) -> Severity {
    match severity.to_lowercase().as_str() {
        "critical" => Severity::Critical,
        "high" => Severity::High,
        "medium" => Severity::Medium,
        "low" => Severity::Low,
        "info" => Severity::Info,
        _ => Severity::Medium,
    }
}

/// Parse CVSS score to Severity enum
fn parse_cvss_score(score: &str) -> Severity {
    if let Ok(cvss) = score.parse::<f32>() {
        match cvss {
            0.0..=3.9 => Severity::Low,
            4.0..=6.9 => Severity::Medium,
            7.0..=8.9 => Severity::High,
            9.0..=10.0 => Severity::Critical,
            _ => Severity::Medium,
        }
    } else {
        Severity::Medium
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_severity() {
        assert_eq!(parse_severity("critical"), Severity::Critical);
        assert_eq!(parse_severity("HIGH"), Severity::High);
        assert_eq!(parse_severity("Medium"), Severity::Medium);
        assert_eq!(parse_severity("low"), Severity::Low);
        assert_eq!(parse_severity("unknown"), Severity::Medium);
    }

    #[test]
    fn test_parse_cvss_score() {
        assert_eq!(parse_cvss_score("2.5"), Severity::Low);
        assert_eq!(parse_cvss_score("5.5"), Severity::Medium);
        assert_eq!(parse_cvss_score("7.5"), Severity::High);
        assert_eq!(parse_cvss_score("9.8"), Severity::Critical);
    }
}
