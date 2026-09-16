// @trace QG-CFG-001: per-repo configuration via .qgate.toml

use serde::{Deserialize, Serialize};
use std::path::Path;

/// Per-repo configuration loaded from `.qgate.toml`.
/// All fields are optional; defaults are the strict lab-wide thresholds.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct QGateConfig {
    /// Minimum line coverage % for every module (default: 85.0).
    #[serde(default = "default_coverage_threshold")]
    pub coverage_threshold: f64,

    /// Minimum mutation score % (default: 75.0).
    #[serde(default = "default_mutation_threshold")]
    pub mutation_threshold: f64,

    /// Minimum chaos resiliency score % (default: 80.0).
    #[serde(default = "default_chaos_threshold")]
    pub chaos_threshold: f64,

    /// Maximum init time in ms for perf gate (default: 15 000).
    #[serde(default = "default_perf_init_ms")]
    pub perf_init_ms: f64,

    /// Maximum edit latency in ms for perf gate (default: 5 000).
    #[serde(default = "default_perf_edit_ms")]
    pub perf_edit_ms: f64,

    /// Categories explicitly declared N/A for this repo.
    #[serde(default)]
    pub not_applicable: Vec<String>,

    /// Coverage report format: "cobertura", "lcov", "json" (default: "lcov").
    #[serde(default = "default_coverage_format")]
    pub coverage_format: String,

    /// Path to the coverage report file (default: "coverage/lcov.info").
    #[serde(default = "default_coverage_path")]
    pub coverage_path: String,

    /// Optional shell command to generate a CycloneDX SBOM at
    /// `target/sbom.cdx.json` (e.g. `cyclonedx-py -o target/sbom.cdx.json`).
    /// When set, SBOM category runs the command and verifies the artifact
    /// exists; missing/unset means SBOM is auto-SKIPPED unless artifact
    /// already exists at `target/sbom.cdx.json`.
    #[serde(default)]
    pub sbom_command: Option<String>,
}

fn default_coverage_threshold() -> f64 {
    85.0
}
fn default_mutation_threshold() -> f64 {
    75.0
}
fn default_chaos_threshold() -> f64 {
    80.0
}
fn default_perf_init_ms() -> f64 {
    15_000.0
}
fn default_perf_edit_ms() -> f64 {
    5_000.0
}
fn default_coverage_format() -> String {
    "lcov".into()
}
fn default_coverage_path() -> String {
    "coverage/lcov.info".into()
}

impl Default for QGateConfig {
    fn default() -> Self {
        Self {
            coverage_threshold: default_coverage_threshold(),
            mutation_threshold: default_mutation_threshold(),
            chaos_threshold: default_chaos_threshold(),
            perf_init_ms: default_perf_init_ms(),
            perf_edit_ms: default_perf_edit_ms(),
            not_applicable: vec![],
            coverage_format: default_coverage_format(),
            coverage_path: default_coverage_path(),
            sbom_command: None,
        }
    }
}

impl QGateConfig {
    /// Load config from `.qgate.toml` in the given directory, or return defaults.
    pub fn load(project_root: &Path) -> Self {
        let config_path = project_root.join(".qgate.toml");
        if config_path.exists() {
            let content = std::fs::read_to_string(&config_path).unwrap_or_default();
            toml::from_str(&content).unwrap_or_default()
        } else {
            Self::default()
        }
    }

    /// True when the named category is declared not-applicable.
    pub fn is_na(&self, category: &str) -> bool {
        self.not_applicable.iter().any(|s| s == category)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_are_strict() {
        let cfg = QGateConfig::default();
        assert_eq!(cfg.coverage_threshold, 85.0);
        assert_eq!(cfg.mutation_threshold, 75.0);
        assert_eq!(cfg.chaos_threshold, 80.0);
    }

    #[test]
    fn is_na_check() {
        let cfg = QGateConfig {
            not_applicable: vec!["a11y".into(), "chaos".into()],
            ..QGateConfig::default()
        };
        assert!(cfg.is_na("a11y"));
        assert!(!cfg.is_na("unit"));
    }
}
