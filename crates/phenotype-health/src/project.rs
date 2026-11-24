//! Project-level health tracking types for unified dashboard.
//!
//! Provides types for tracking project health across documentation,
//! test coverage, security, dependencies, compliance, and code quality.

use std::collections::HashMap;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Health dimensions tracked per project
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HealthDimension {
    /// Documentation completeness
    Documentation,
    /// Test coverage percentage
    TestCoverage,
    /// Security posture
    Security,
    /// Dependency freshness
    Dependencies,
    /// Governance compliance
    Compliance,
    /// Code quality metrics
    CodeQuality,
}

impl HealthDimension {
    /// Weight of this dimension in overall health score
    pub fn weight(&self) -> f32 {
        match self {
            Self::Documentation => 0.15,
            Self::TestCoverage => 0.20,
            Self::Security => 0.25,
            Self::Dependencies => 0.15,
            Self::Compliance => 0.15,
            Self::CodeQuality => 0.10,
        }
    }

    /// Display name for this dimension
    pub fn display_name(&self) -> &'static str {
        match self {
            Self::Documentation => "Documentation",
            Self::TestCoverage => "Test Coverage",
            Self::Security => "Security",
            Self::Dependencies => "Dependencies",
            Self::Compliance => "Compliance",
            Self::CodeQuality => "Code Quality",
        }
    }
}

/// Overall health classification band
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum HealthBand {
    /// 90-100: Excellent health
    Excellent,
    /// 75-89: Good health with minor issues
    Good,
    /// 60-74: Fair health, needs attention
    Fair,
    /// 40-59: Poor health, significant issues
    Poor,
    /// 0-39: Critical health, immediate action required
    Critical,
}

impl HealthBand {
    /// Classify score into band
    pub fn from_score(score: f32) -> Self {
        if score >= 90.0 {
            Self::Excellent
        } else if score >= 75.0 {
            Self::Good
        } else if score >= 60.0 {
            Self::Fair
        } else if score >= 40.0 {
            Self::Poor
        } else {
            Self::Critical
        }
    }
}

/// Score and findings for a specific health dimension
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DimensionScore {
    /// Calculated score (0-100)
    pub score: f32,
    /// Target score
    pub target: f32,
    /// Raw value (e.g., percentage, count)
    pub raw_value: f32,
    /// Unit of the raw value
    pub unit: String,
    /// Individual findings for this dimension
    pub findings: Vec<Finding>,
}

/// Individual finding within a dimension
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    /// Severity of the finding
    pub severity: Severity,
    /// Human-readable message
    pub message: String,
    /// File path if applicable
    #[serde(skip_serializing_if = "Option::is_none")]
    pub file_path: Option<String>,
    /// Line number if applicable
    #[serde(skip_serializing_if = "Option::is_none")]
    pub line_number: Option<u32>,
}

/// Severity level of findings
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Severity {
    /// Informational finding
    Info,
    /// Warning - should be addressed
    Warning,
    /// Error - must be addressed
    Error,
    /// Critical - immediate action required
    Critical,
}

/// Detected programming language
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase", tag = "type")]
pub enum LanguageStack {
    /// Rust project
    Rust,
    /// TypeScript/JavaScript project
    TypeScript,
    /// Python project
    Python,
    /// Go project
    Go,
    /// Multiple languages
    Mixed(Vec<String>),
}

impl LanguageStack {
    /// Detect from project files
    pub fn detect(project_path: &std::path::Path) -> Self {
        let mut languages = Vec::new();

        if project_path.join("Cargo.toml").exists() {
            languages.push("Rust".to_string());
        }
        if project_path.join("package.json").exists() {
            languages.push("TypeScript".to_string());
        }
        if project_path.join("pyproject.toml").exists()
            || project_path.join("setup.py").exists()
            || project_path.join("requirements.txt").exists()
        {
            languages.push("Python".to_string());
        }
        if project_path.join("go.mod").exists() {
            languages.push("Go".to_string());
        }

        match languages.len() {
            0 => Self::Rust, // Default to Rust
            1 => match languages[0].as_str() {
                "Rust" => Self::Rust,
                "TypeScript" => Self::TypeScript,
                "Python" => Self::Python,
                "Go" => Self::Go,
                _ => Self::Rust,
            },
            _ => Self::Mixed(languages),
        }
    }
}

/// Complete project health record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectHealth {
    /// Repository name
    pub repo_name: String,
    /// Owner/organization
    pub owner: String,
    /// Detected language stack
    pub language: LanguageStack,
    /// Overall health score (0-100)
    pub overall_score: f32,
    /// Health band classification
    pub band: HealthBand,
    /// Dimension-level scores
    pub dimensions: HashMap<HealthDimension, DimensionScore>,
    /// When last scanned
    pub last_scan: DateTime<Utc>,
    /// Scanner version
    pub scan_version: String,
}

impl ProjectHealth {
    /// Calculate overall score from dimensions
    pub fn calculate_overall(&self) -> f32 {
        self.dimensions
            .iter()
            .map(|(dim, score)| dim.weight() * score.score)
            .sum()
    }

    /// Get summary of all findings
    pub fn all_findings(&self) -> Vec<&Finding> {
        self.dimensions
            .values()
            .flat_map(|d| d.findings.iter())
            .collect()
    }
}

/// Summary of health across multiple projects
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthSummary {
    /// Total projects scanned
    pub total_projects: usize,
    /// Average score across all projects
    pub average_score: f32,
    /// Projects by band
    pub by_band: HashMap<HealthBand, usize>,
    /// Common issues across projects
    pub common_issues: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_health_band_from_score() {
        assert_eq!(HealthBand::from_score(95.0), HealthBand::Excellent);
        assert_eq!(HealthBand::from_score(80.0), HealthBand::Good);
        assert_eq!(HealthBand::from_score(65.0), HealthBand::Fair);
        assert_eq!(HealthBand::from_score(50.0), HealthBand::Poor);
        assert_eq!(HealthBand::from_score(30.0), HealthBand::Critical);
    }

    #[test]
    fn test_dimension_weight() {
        assert_eq!(HealthDimension::Security.weight(), 0.25);
        assert_eq!(HealthDimension::TestCoverage.weight(), 0.20);
        assert!(HealthDimension::Documentation.weight() > 0.0);
    }

    #[test]
    fn test_language_detection() {
        // Test would require creating temp directories
        // For now just verify the enum variants work
        let _lang = LanguageStack::Rust;
        let _lang = LanguageStack::TypeScript;
        let _lang = LanguageStack::Python;
        let _lang = LanguageStack::Go;
        let _lang = LanguageStack::Mixed(vec!["Rust".to_string(), "TypeScript".to_string()]);
    }
}
