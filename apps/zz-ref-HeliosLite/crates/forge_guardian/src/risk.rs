//! Risk model produced by a [`RiskJudge`].

use serde::{Deserialize, Serialize};

/// A single risk label, useful for surfacing *why* a call scored high.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RiskLabel {
    /// Writes outside the workspace cwd.
    WriteOutsideWorkspace,
    /// Deletes / overwrites a tracked file (git-tracked) without explicit confirm.
    MutateTrackedFile,
    /// Shell executes a command with destructive flags (rm -rf, git push --force, etc.).
    DestructiveCommand,
    /// Shell command touches sensitive paths (credentials, .ssh, .env secrets).
    SensitivePath,
    /// Fetches a URL (network boundary crossed).
    NetworkFetch,
    /// Reads a sensitive file (secrets, keys, tokens).
    SensitiveRead,
    /// Operation requires a previously-confirmed permission that has since expired.
    ExpiredGrant,
}

/// Aggregated risk level, thresholds are cluster-globally configurable.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RiskLevel {
    Low,
    Medium,
    High,
}

impl RiskLevel {
    /// Map a raw score (0.0..=1.0) to a level.
    pub fn from_score(score: f64) -> Self {
        match score {
            s if s < 0.33 => RiskLevel::Low,
            s if s < 0.66 => RiskLevel::Medium,
            _ => RiskLevel::High,
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            RiskLevel::Low => "low",
            RiskLevel::Medium => "medium",
            RiskLevel::High => "high",
        }
    }
}

/// A single contributing reason (label + weight) used to compose scores.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RiskFactor {
    pub label: RiskLabel,
    /// 0..=1 contribution.
    pub weight: f64,
}

/// Normalized risk score 0..=1 plus the reasons that produced it.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Risk {
    /// Composite score in `0.0..=1.0`.
    pub score: f64,
    /// Contributing factors (for explainability / audit / UI).
    pub factors: Vec<RiskFactor>,
}

impl Risk {
    pub fn new(score: f64, factors: Vec<RiskFactor>) -> Self {
        Self { score: score.clamp(0.0, 1.0), factors }
    }

    pub fn low() -> Self {
        Self { score: 0.0, factors: Vec::new() }
    }
    pub fn high() -> Self {
        Self { score: 1.0, factors: Vec::new() }
    }

    pub fn level(&self) -> RiskLevel {
        RiskLevel::from_score(self.score)
    }
}

impl std::fmt::Display for Risk {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let lvl = self.level();
        write!(f, "[{}] score={:.2}", lvl.label(), self.score)?;
        for factor in &self.factors {
            write!(f, " ({})", factor.label_str())?;
        }
        Ok(())
    }
}

impl RiskFactor {
    pub fn new(label: RiskLabel, weight: f64) -> Self {
        Self { label, weight }
    }
    pub fn label_str(&self) -> &'static str {
        match self.label {
            RiskLabel::WriteOutsideWorkspace => "write-outside-workspace",
            RiskLabel::MutateTrackedFile => "mutate-tracked-file",
            RiskLabel::DestructiveCommand => "destructive-command",
            RiskLabel::SensitivePath => "sensitive-path",
            RiskLabel::NetworkFetch => "network-fetch",
            RiskLabel::SensitiveRead => "sensitive-read",
            RiskLabel::ExpiredGrant => "expired-grant",
        }
    }
}
