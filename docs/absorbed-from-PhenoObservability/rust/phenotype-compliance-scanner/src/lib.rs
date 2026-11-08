use serde::{Deserialize, Serialize};
use std::path::Path;

/// Severity level for compliance findings
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum Severity {
    Critical,
    High,
    Medium,
    Low,
    Info,
}

/// A single compliance finding
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    pub rule_id: String,
    pub severity: Severity,
    pub message: String,
    pub file: Option<String>,
    pub line: Option<u32>,
}

/// Result of a compliance scan
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanResult {
    pub findings: Vec<Finding>,
    pub score: f32,
}

/// Compliance scanner for project compliance checks
#[derive(Debug, Clone, Default)]
pub struct ComplianceScanner {
    rules: Vec<ComplianceRule>,
}

#[derive(Debug, Clone)]
struct ComplianceRule {
    id: String,
    severity: Severity,
    check: fn(&Path) -> Option<String>,
}

impl ComplianceScanner {
    /// Create a new scanner with default rules
    pub fn new() -> Self {
        Self::default()
    }

    /// Scan a project path for compliance issues
    pub fn scan(&self, path: impl AsRef<Path>) -> anyhow::Result<ScanResult> {
        let path = path.as_ref();
        let mut findings = Vec::new();

        // Check for README
        if !path.join("README.md").exists() && !path.join("README.rst").exists() {
            findings.push(Finding {
                rule_id: "DOCS-001".to_string(),
                severity: Severity::High,
                message: "Missing README file".to_string(),
                file: None,
                line: None,
            });
        }

        // Check for LICENSE
        if !path.join("LICENSE").exists()
            && !path.join("LICENSE.md").exists()
            && !path.join("LICENSE.txt").exists()
        {
            findings.push(Finding {
                rule_id: "LICENSE-001".to_string(),
                severity: Severity::High,
                message: "Missing LICENSE file".to_string(),
                file: None,
                line: None,
            });
        }

        // Check for AGENTS.md
        if !path.join("AGENTS.md").exists() {
            findings.push(Finding {
                rule_id: "DOCS-002".to_string(),
                severity: Severity::Medium,
                message: "Missing AGENTS.md file".to_string(),
                file: None,
                line: None,
            });
        }

        // Calculate score
        let score = if findings.is_empty() {
            100.0
        } else {
            let penalty: f32 = findings
                .iter()
                .map(|f| match f.severity {
                    Severity::Critical => 20.0,
                    Severity::High => 10.0,
                    Severity::Medium => 5.0,
                    Severity::Low => 2.0,
                    Severity::Info => 0.5,
                })
                .sum();
            (100.0 - penalty).max(0.0)
        };

        Ok(ScanResult { findings, score })
    }
}
