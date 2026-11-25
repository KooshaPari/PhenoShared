//! Phenotype Compliance Scanner
//!
//! Provides compliance scanning functionality for security and policy enforcement.

use phenotype_error_core::{Error, Result};

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
            .filter_map(|rule| match rule.check(target) {
                Ok(result) => Some(result),
                Err(_) => None,
            })
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
}
