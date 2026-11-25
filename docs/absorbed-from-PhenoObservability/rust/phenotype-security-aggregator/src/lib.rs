use serde::{Deserialize, Serialize};

/// Severity level for security findings
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum Severity {
    Critical,
    High,
    Medium,
    Low,
    Info,
}

/// A single security finding
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    pub rule_id: String,
    pub severity: Severity,
    pub message: String,
    pub source: String,
}

/// Aggregated security report
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityReport {
    pub findings: Vec<Finding>,
    pub risk_score: f32,
}

/// Security aggregator that collects findings from multiple sources
#[derive(Debug, Clone)]
pub struct SecurityAggregator {
    sources: Vec<String>,
}

impl SecurityAggregator {
    /// Create a new security aggregator
    pub fn new() -> Self {
        Self {
            sources: Vec::new(),
        }
    }

    /// Add a security source
    pub fn add_source(&mut self, source: impl Into<String>) {
        self.sources.push(source.into());
    }

    /// Aggregate security findings from all sources
    pub async fn aggregate(&self) -> anyhow::Result<SecurityReport> {
        // Stub: return empty findings
        // In production, this would query each source and aggregate results
        Ok(SecurityReport {
            findings: Vec::new(),
            risk_score: 0.0,
        })
    }
}

impl Default for SecurityAggregator {
    fn default() -> Self {
        Self::new()
    }
}
