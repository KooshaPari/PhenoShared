//! Phenotype Compliance Scanner
//!
//! Provides compliance scanning functionality for security and policy enforcement.

use regex::Regex;
use thiserror::Error;

/// Result type for compliance operations
pub type Result<T> = std::result::Result<T, ComplianceError>;

/// Error type for compliance scanner
#[derive(Error, Debug)]
pub enum ComplianceError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Regex error: {0}")]
    Regex(#[from] regex::Error),
    #[error("Other error: {0}")]
    Other(String),
}

/// Compliance check result
#[derive(Debug, Clone)]
pub struct ComplianceResult {
    pub rule_id: String,
    pub passed: bool,
    pub message: String,
    pub severity: Severity,
}

/// Severity levels for compliance violations
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Severity {
    Info,
    Low,
    Medium,
    High,
    Critical,
}

impl std::fmt::Display for Severity {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Severity::Info => write!(f, "INFO"),
            Severity::Low => write!(f, "LOW"),
            Severity::Medium => write!(f, "MEDIUM"),
            Severity::High => write!(f, "HIGH"),
            Severity::Critical => write!(f, "CRITICAL"),
        }
    }
}

/// Scanner for compliance checks
pub struct Scanner {
    rules: Vec<Box<dyn ComplianceRule>>,
}

/// KodeVibe rule category configuration.
#[derive(Debug, Clone)]
pub struct KodeVibeCategoryConfig {
    pub enabled: bool,
    pub level: String,
    pub max_function_length: Option<u32>,
    pub max_nesting_depth: Option<u32>,
    pub max_bundle_size: Option<String>,
    pub min_commit_message_length: Option<u32>,
    pub check_vulnerabilities: Option<bool>,
}

impl KodeVibeCategoryConfig {
    fn new(enabled: bool, level: impl Into<String>) -> Self {
        Self {
            enabled,
            level: level.into(),
            max_function_length: None,
            max_nesting_depth: None,
            max_bundle_size: None,
            min_commit_message_length: None,
            check_vulnerabilities: None,
        }
    }
}

/// Full KodeVibe rule-set configuration.
#[derive(Debug, Clone)]
pub struct KodeVibeRuleSet {
    pub security: KodeVibeCategoryConfig,
    pub code: KodeVibeCategoryConfig,
    pub performance: KodeVibeCategoryConfig,
    pub file: KodeVibeCategoryConfig,
    pub git: KodeVibeCategoryConfig,
    pub dependency: KodeVibeCategoryConfig,
    pub documentation: KodeVibeCategoryConfig,
}

impl Default for KodeVibeRuleSet {
    fn default() -> Self {
        Self {
            security: KodeVibeCategoryConfig::new(true, "strict"),
            code: KodeVibeCategoryConfig {
                max_function_length: Some(50),
                max_nesting_depth: Some(4),
                ..KodeVibeCategoryConfig::new(true, "moderate")
            },
            performance: KodeVibeCategoryConfig {
                max_bundle_size: Some("2MB".to_string()),
                ..KodeVibeCategoryConfig::new(true, "moderate")
            },
            file: KodeVibeCategoryConfig::new(true, "strict"),
            git: KodeVibeCategoryConfig {
                min_commit_message_length: Some(10),
                ..KodeVibeCategoryConfig::new(true, "moderate")
            },
            dependency: KodeVibeCategoryConfig {
                check_vulnerabilities: Some(true),
                ..KodeVibeCategoryConfig::new(true, "moderate")
            },
            documentation: KodeVibeCategoryConfig::new(false, "moderate"),
        }
    }
}

/// Regex-backed KodeVibe compliance rule.
pub struct KodeVibeRule {
    id: String,
    description: String,
    message: String,
    severity: Severity,
    pattern: Regex,
}

impl KodeVibeRule {
    pub fn new(
        id: impl Into<String>,
        description: impl Into<String>,
        message: impl Into<String>,
        severity: Severity,
        pattern: impl AsRef<str>,
    ) -> Result<Self> {
        Ok(Self {
            id: id.into(),
            description: description.into(),
            message: message.into(),
            severity,
            pattern: Regex::new(pattern.as_ref())?,
        })
    }
}

impl ComplianceRule for KodeVibeRule {
    fn id(&self) -> &str {
        &self.id
    }

    fn description(&self) -> &str {
        &self.description
    }

    fn check(&self, target: &ScanTarget) -> Result<ComplianceResult> {
        let content = match target {
            ScanTarget::Content(content) => content.as_str(),
            ScanTarget::File(path) | ScanTarget::Directory(path) => path.as_str(),
        };

        let passed = !self.pattern.is_match(content);
        Ok(ComplianceResult {
            rule_id: self.id.clone(),
            passed,
            message: if passed {
                format!("{} passed", self.description)
            } else {
                self.message.clone()
            },
            severity: self.severity,
        })
    }
}

pub fn default_kodevibe_rules() -> Vec<Box<dyn ComplianceRule>> {
    vec![
        Box::new(
            KodeVibeRule::new(
                "KODEVIBE-001",
                "Remove console.log statements before committing",
                "Remove console.log statements before committing",
                Severity::Low,
                r"console\.log\(",
            )
            .expect("valid kodevibe console.log rule"),
        ),
        Box::new(
            KodeVibeRule::new(
                "KODEVIBE-002",
                "TODO comments should be tracked in issues",
                "TODO comments should be tracked in issues",
                Severity::Info,
                r"(?i)\b(todo|fixme|hack|xxx)\b",
            )
            .expect("valid kodevibe todo rule"),
        ),
    ]
}

/// Trait for compliance rules
pub trait ComplianceRule: Send + Sync {
    fn id(&self) -> &str;
    fn description(&self) -> &str;
    fn check(&self, target: &ScanTarget) -> Result<ComplianceResult>;
}

/// Target to scan
#[derive(Debug, Clone)]
pub enum ScanTarget {
    File(String),
    Directory(String),
    Content(String),
}

impl Scanner {
    /// Create a new scanner
    pub fn new() -> Self {
        Self { rules: Vec::new() }
    }

    /// Add a compliance rule
    pub fn add_rule(&mut self, rule: Box<dyn ComplianceRule>) {
        self.rules.push(rule);
    }

    /// Scan a target against all rules
    pub fn scan(&self, target: &ScanTarget) -> Vec<ComplianceResult> {
        self.rules
            .iter()
            .filter_map(|rule| rule.check(target).ok())
            .collect()
    }
}

impl Default for Scanner {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct TestRule;

    impl ComplianceRule for TestRule {
        fn id(&self) -> &str {
            "TEST-001"
        }

        fn description(&self) -> &str {
            "Test rule"
        }

        fn check(&self, _target: &ScanTarget) -> Result<ComplianceResult> {
            Ok(ComplianceResult {
                rule_id: "TEST-001".to_string(),
                passed: true,
                message: "Test passed".to_string(),
                severity: Severity::Info,
            })
        }
    }

    #[test]
    fn test_scanner() {
        let mut scanner = Scanner::new();
        scanner.add_rule(Box::new(TestRule));

        let target = ScanTarget::Content("test".to_string());
        let results = scanner.scan(&target);

        assert_eq!(results.len(), 1);
        assert!(results[0].passed);
    }

    #[test]
    fn test_kodevibe_console_log_rule_fires() {
        let rule = default_kodevibe_rules()
            .into_iter()
            .find(|rule| rule.id() == "KODEVIBE-001")
            .expect("console.log rule should exist");

        let result = rule
            .check(&ScanTarget::Content("console.log('debug');".to_string()))
            .expect("rule check should succeed");

        assert!(!result.passed);
        assert_eq!(result.rule_id, "KODEVIBE-001");
        assert_eq!(
            result.message,
            "Remove console.log statements before committing"
        );
    }
}
