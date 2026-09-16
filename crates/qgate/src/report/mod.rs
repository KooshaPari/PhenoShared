// @trace QG-RPT-001: machine-readable JSON report + human tree summary

use chrono::Utc;
use serde::{Deserialize, Serialize};

use crate::checks::{CheckMatrix, CheckStatus};
use crate::coverage::CoverageTree;

/// Overall gate outcome.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum GateStatus {
    Pass,
    Fail,
}

impl GateStatus {
    pub fn exit_code(self) -> i32 {
        match self {
            Self::Pass => 0,
            Self::Fail => 1,
        }
    }
}

/// The full gate report emitted as JSON and rendered as a human summary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateReport {
    pub status: GateStatus,
    pub timestamp: String,
    pub coverage: CoverageTree,
    pub checks: CheckMatrix,
}

impl GateReport {
    pub fn new(coverage: CoverageTree, checks: CheckMatrix) -> Self {
        let cov_pass = coverage.all_pass();
        let chk_pass = checks.all_pass();
        let status = if cov_pass && chk_pass {
            GateStatus::Pass
        } else {
            GateStatus::Fail
        };
        Self {
            status,
            timestamp: Utc::now().to_rfc3339(),
            coverage,
            checks,
        }
    }

    /// Emit machine-readable JSON to stdout.
    pub fn emit_json(&self) -> anyhow::Result<()> {
        println!("{}", serde_json::to_string_pretty(self)?);
        Ok(())
    }

    /// Render a human-readable tree summary (sent to stderr so JSON can be piped).
    pub fn render_summary(&self) -> String {
        let mut out = String::new();
        let gate_marker = if self.status == GateStatus::Pass {
            "✓ PASS"
        } else {
            "✗ FAIL"
        };
        out.push_str(&format!(
            "\n╔══ qgate {gate_marker} ══════════════════════════╗\n"
        ));

        // Coverage section
        let cov_pass = self.coverage.all_pass();
        let cov_marker = if cov_pass { "✓" } else { "✗" };
        out.push_str(&format!(
            "║  {cov_marker} Coverage  {:.1}%  (threshold {:.1}%)\n",
            self.coverage.overall_rate() * 100.0,
            self.coverage.threshold
        ));
        // Render tree nodes inline
        for line in self.coverage.render_tree().lines().skip(1) {
            out.push_str(&format!("║    {line}\n"));
        }

        // Checks section
        out.push_str("║\n║  Check Matrix:\n");
        for result in &self.checks.results {
            let marker = match result.status {
                CheckStatus::Passed => "✓",
                CheckStatus::Failed => "✗",
                CheckStatus::NotApplicable => "─",
                CheckStatus::Skipped => "?",
            };
            let score_str = match (result.score, result.threshold) {
                (Some(s), Some(t)) => format!("  {s:.1} / {t:.1}"),
                (Some(s), None) => format!("  {s:.1}"),
                _ => String::new(),
            };
            out.push_str(&format!(
                "║    {marker} {:16}{score_str}  {}\n",
                result.category.name(),
                result.details
            ));
        }

        out.push_str("╚══════════════════════════════════════════════╝\n");
        out
    }

    /// Render summary to stderr and JSON to stdout.
    pub fn emit_all(&self) -> anyhow::Result<()> {
        eprint!("{}", self.render_summary());
        self.emit_json()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::checks::{CheckCategory, CheckResult, CheckStatus};
    use crate::coverage::CoverageNode;

    fn passing_coverage() -> CoverageTree {
        CoverageTree {
            threshold: 85.0,
            nodes: vec![CoverageNode {
                path: "src/lib.rs".into(),
                line_rate: 0.90,
                branch_rate: 0.88,
                lines_covered: 90,
                lines_valid: 100,
                children: vec![],
            }],
        }
    }

    // @trace QG-RPT-001
    #[test]
    fn all_pass_is_pass() {
        let matrix = CheckMatrix::from_results(vec![CheckResult {
            category: CheckCategory::Unit,
            status: CheckStatus::Passed,
            score: Some(100.0),
            threshold: Some(100.0),
            details: String::new(),
        }]);
        let report = GateReport::new(passing_coverage(), matrix);
        assert_eq!(report.status, GateStatus::Pass);
    }

    // @trace QG-RPT-002
    #[test]
    fn check_failure_is_fail() {
        let matrix = CheckMatrix::from_results(vec![CheckResult {
            category: CheckCategory::Security,
            status: CheckStatus::Failed,
            score: Some(1.0),
            threshold: Some(0.0),
            details: "1 critical finding".into(),
        }]);
        let report = GateReport::new(passing_coverage(), matrix);
        assert_eq!(report.status, GateStatus::Fail);
    }

    // @trace QG-RPT-005
    #[test]
    fn exit_codes() {
        assert_eq!(GateStatus::Pass.exit_code(), 0);
        assert_eq!(GateStatus::Fail.exit_code(), 1);
    }
}
