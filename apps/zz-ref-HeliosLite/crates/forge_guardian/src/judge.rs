//! Risk adjudication: the [`RiskJudge`] trait and its implementations.

use std::path::Path;

use forge_domain::PermissionOperation;

use crate::risk::{Risk, RiskFactor, RiskLabel};

/// A scoring layer that evaluates a [`PermissionOperation`] and returns a
/// normalized [`Risk`] before the rule engine makes its allow/deny/confirm
/// call.
///
/// The trait is intentionally *pure* (no side effects) so it can be swapped,
/// composed, and unit-tested independently of the orchestrator.
pub trait RiskJudge: Send + Sync {
    /// Score a [`PermissionOperation`]. Returns a `Risk` in `0.0..=1.0`.
    fn score(&self, op: &PermissionOperation) -> Risk;
}

/// A no-op judge that always reports low risk. Default when no heuristic or
/// LLM judge is configured. Produces zero factors so the audit trail shows
/// "unadjudicated".
#[derive(Debug, Default, Clone)]
pub struct NoopRiskJudge;

impl RiskJudge for NoopRiskJudge {
    fn score(&self, _op: &PermissionOperation) -> Risk {
        Risk::low()
    }
}

/// A rule-/static-heuristic judge that scores a [`PermissionOperation`]
/// without any LLM round-trip. Gives deterministic, explainable, near-free
/// adjudication for the common cases; a configured LLM judge layers on top.
#[derive(Debug, Clone)]
pub struct HeuristicRiskJudge {
    /// Root workspace directory used to classify "outside workspace".
    /// When `None`, outside-workspace checks are skipped.
    pub workspace: Option<std::path::PathBuf>,
    /// Command fragments that mark a shell/execute call as destructive.
    pub destructive_markers: Vec<String>,
    /// Path components (file names or directory segments) treated as sensitive.
    pub sensitive_markers: Vec<String>,
}

impl Default for HeuristicRiskJudge {
    fn default() -> Self {
        Self {
            workspace: None,
            destructive_markers: vec![
                "rm -rf".to_string(),
                "rm -fr".to_string(),
                "git push --force".to_string(),
                "git push -f".to_string(),
                "git reset --hard".to_string(),
                ":(){ :|:& };:".to_string(), // fork bomb
                "mkfs".to_string(),
                "dd if=/dev/zero of=/dev/".to_string(),
            ],
            sensitive_markers: vec![
                ".ssh".to_string(),
                ".env".to_string(),
                "id_rsa".to_string(),
                "id_ed25519".to_string(),
                "credential".to_string(),
                "secret".to_string(),
                "token".to_string(),
                "password".to_string(),
                ".pem".to_string(),
                ".key".to_string(),
                "aws".to_string(),
            ],
        }
    }
}

impl HeuristicRiskJudge {
    /// True when `path` resolves strictly outside `self.workspace`.
    fn is_outside_workspace(&self, path: &Path) -> bool {
        let Some(ws) = &self.workspace else {
            return false;
        };
        // Prefer canonical comparison when both paths resolve (e.g. a live
        // workspace dir on the host). This handles symlinks and `.`/`..`.
        if let (Ok(p), Ok(w)) = (path.canonicalize(), ws.canonicalize()) {
            return !p.starts_with(&w);
        }
        // Fall back to a lexical comparison of the raw paths so the check
        // still works on paths that don't exist on disk (tests, dry runs).
        let path = path.to_string_lossy();
        let ws = ws.to_string_lossy();
        !path.starts_with(ws.as_ref())
    }

    /// True when any marker appears in the lower-cased command string.
    fn has_destructive(&self, command: &str) -> bool {
        let lower = command.to_lowercase();
        self.destructive_markers
            .iter()
            .any(|m| lower.contains(&m.to_lowercase()))
    }

    /// True when any sensitive marker is a component of `path`.
    fn touches_sensitive(&self, path: &Path) -> bool {
        let path_str = path.to_string_lossy().to_lowercase();
        self.sensitive_markers
            .iter()
            .any(|m| path_str.contains(&m.to_lowercase()))
    }
}

impl RiskJudge for HeuristicRiskJudge {
    fn score(&self, op: &PermissionOperation) -> Risk {
        let mut factors: Vec<RiskFactor> = Vec::new();
        match op {
            PermissionOperation::Write { path, .. } => {
                if self.is_outside_workspace(path) {
                    factors.push(RiskFactor::new(RiskLabel::WriteOutsideWorkspace, 0.7));
                } else if self.touches_sensitive(path) {
                    factors.push(RiskFactor::new(RiskLabel::SensitivePath, 0.9));
                } else if is_tracked_file(path) {
                    factors.push(RiskFactor::new(RiskLabel::MutateTrackedFile, 0.4));
                }
            }
            PermissionOperation::Read { path, .. } => {
                if self.touches_sensitive(path) {
                    factors.push(RiskFactor::new(RiskLabel::SensitiveRead, 0.8));
                }
            }
            PermissionOperation::Execute { command, .. } => {
                if self.has_destructive(command) {
                    factors.push(RiskFactor::new(RiskLabel::DestructiveCommand, 0.95));
                }
                // Scan the command string for sensitive path markers too.
                if self
                    .sensitive_markers
                    .iter()
                    .any(|m| command.to_lowercase().contains(&m.to_lowercase()))
                {
                    factors.push(RiskFactor::new(RiskLabel::SensitivePath, 0.5));
                }
            }
            PermissionOperation::Fetch { .. } => {
                factors.push(RiskFactor::new(RiskLabel::NetworkFetch, 0.5));
            }
        }

        let score = factors.iter().map(|f| f.weight).fold(0.0_f64, f64::max);
        Risk::new(score, factors)
    }
}

/// Heuristic: a non-existent path is conservatively treated as a (potential)
/// tracked-file mutation only when it looks like a source file under a git
/// workspace. Without a git backend here we keep this conservative: return
/// true only when the path has a source-y extension, so the caller can opt
/// to raise the factor.
fn is_tracked_file(path: &Path) -> bool {
    matches!(
        path.extension().and_then(|e| e.to_str()),
        Some(
            "rs" | "toml"
                | "ts"
                | "tsx"
                | "js"
                | "jsx"
                | "py"
                | "go"
                | "c"
                | "h"
                | "cpp"
                | "hpp"
                | "json"
                | "yaml"
                | "yml"
        )
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use forge_domain::PermissionOperation;

    fn ws() -> Option<std::path::PathBuf> {
        Some(std::path::PathBuf::from("/home/user/proj"))
    }

    #[test]
    fn noop_judge_always_low() {
        let j = NoopRiskJudge;
        let op = PermissionOperation::Execute {
            command: "rm -rf /".into(),
            cwd: std::path::PathBuf::from("/home/user/proj"),
        };
        assert_eq!(j.score(&op).level(), crate::risk::RiskLevel::Low);
        assert!(j.score(&op).factors.is_empty());
    }

    #[test]
    fn heuristic_marks_destructive_execute_high() {
        let j = HeuristicRiskJudge { workspace: ws(), ..Default::default() };
        let op = PermissionOperation::Execute {
            command: "rm -rf /home/user/proj/vendor".into(),
            cwd: std::path::PathBuf::from("/home/user/proj"),
        };
        let risk = j.score(&op);
        assert_eq!(risk.level(), crate::risk::RiskLevel::High);
        assert!(
            risk.factors
                .iter()
                .any(|f| f.label == RiskLabel::DestructiveCommand)
        );
    }

    #[test]
    fn heuristic_marks_write_outside_workspace() {
        let j = HeuristicRiskJudge { workspace: ws(), ..Default::default() };
        let op = PermissionOperation::Write {
            path: std::path::PathBuf::from("/etc/hosts"),
            cwd: std::path::PathBuf::from("/home/user/proj"),
            message: "modify hosts".into(),
        };
        let risk = j.score(&op);
        assert!(
            risk.factors
                .iter()
                .any(|f| f.label == RiskLabel::WriteOutsideWorkspace)
        );
    }

    #[test]
    fn heuristic_marks_sensitive_read() {
        let j = HeuristicRiskJudge { workspace: ws(), ..Default::default() };
        let op = PermissionOperation::Read {
            path: std::path::PathBuf::from("/home/user/proj/.env"),
            cwd: std::path::PathBuf::from("/home/user/proj"),
            message: "read env".into(),
        };
        let risk = j.score(&op);
        assert!(
            risk.factors
                .iter()
                .any(|f| f.label == RiskLabel::SensitiveRead)
        );
    }

    #[test]
    fn heuristic_low_for_innocuous_read_within_workspace() {
        let j = HeuristicRiskJudge { workspace: ws(), ..Default::default() };
        let op = PermissionOperation::Read {
            path: std::path::PathBuf::from("/home/user/proj/src/lib.rs"),
            cwd: std::path::PathBuf::from("/home/user/proj"),
            message: "read lib".into(),
        };
        assert_eq!(j.score(&op).level(), crate::risk::RiskLevel::Low);
    }

    #[test]
    fn heuristic_marks_network_fetch_medium() {
        let j = HeuristicRiskJudge::default();
        let op = PermissionOperation::Fetch {
            url: "https://example.com/x".into(),
            cwd: std::path::PathBuf::from("/home/user/proj"),
            message: "fetch".into(),
        };
        let risk = j.score(&op);
        assert!(
            risk.factors
                .iter()
                .any(|f| f.label == RiskLabel::NetworkFetch)
        );
    }

    #[test]
    fn risk_score_is_bounded() {
        let j = HeuristicRiskJudge::default();
        let op = PermissionOperation::Execute {
            command: "rm -rf / pass ".into(),
            cwd: std::path::PathBuf::from("/x"),
        };
        let risk = j.score(&op);
        assert!((0.0..=1.0).contains(&risk.score));
    }
}
