//! Guardian adjudication orchestrator (P0.1.1).
//!
//! `GuardianAdjudicator` is the **shell** that composes the pieces of the
//! P0.1 guardian into a single verdict for a single tool operation:
//!
//! ```text
//! op
//!  └─ SessionMode gate  ──(forces Confirm / Yolo downgrade)──┐
//!  └─ PolicyEngine      ──> Allow | Deny | Confirm           │
//!  └─ RiskJudge         ──> Risk (factors + level)           │
//!  └─ (P0.1.3) LlmRiskJudge / AuditableJudge                 │
//!      └─> allows / blocks / explains                        v
//!                                            RuleVerdict { verdict, risk, reason }
//! ```
//!
//! The [`RuleVerdict`] is a richer return envelope than the bare
//! `Permission` enum so the guardian can carry *risk* and a *reason* for the
//! audit log (`forge_audit`) and the interactive tool-call view (P0.4)
//! without changing the backwards-compatible `Permission` type.

use crate::judge::RiskJudge;
use crate::risk::Risk;
use crate::session::SessionMode;
use forge_domain::Permission;
use forge_domain::PermissionOperation;

/// Whether an operation mutates system state / crosses a boundary in a way
/// that conservative non-yolo session modes should force a confirm for.
fn op_is_side_effecting(op: &PermissionOperation) -> bool {
    match op {
        PermissionOperation::Read { .. } => false,
        PermissionOperation::Write { .. }
        | PermissionOperation::Execute { .. }
        | PermissionOperation::Fetch { .. } => true,
    }
}

/// A human-readable one-line description of an operation for the audit reason.
fn op_desc(op: &PermissionOperation) -> String {
    match op {
        PermissionOperation::Write { path, .. } => {
            format!("write {}", path.display())
        }
        PermissionOperation::Read { path, .. } => {
            format!("read {}", path.display())
        }
        PermissionOperation::Execute { command, .. } => {
            let head = command.split_whitespace().next().unwrap_or("cmd");
            format!("exec {head}")
        }
        PermissionOperation::Fetch { url, .. } => {
            format!("fetch {url}")
        }
    }
}

/// The verdict produced by the guardian for a single operation.
#[derive(Debug, Clone)]
pub struct RuleVerdict {
    /// The effective permission (allow / deny / confirm).
    pub verdict: Permission,
    /// The risk assessment (0.0..=1.0, level, factors).
    pub risk: Risk,
    /// Human-readable rationale, consumed by the audit log / tool view.
    pub reason: String,
    /// True when a conservative session mode downgraded the decision
    /// (e.g. `plan` forcing confirm, or `yolo` forcing allow).
    pub session_adjusted: bool,
}

impl RuleVerdict {
    pub fn is_allowed(&self) -> bool {
        self.verdict == Permission::Allow
    }

    pub fn requires_confirm(&self) -> bool {
        self.verdict == Permission::Confirm
    }
}

/// A minimal async boundary for any downstream effect the guardian may need
/// (future sandbox query / LLM adjudication writes). Kept as a trait so the
/// shell stays dependency-free and unit-testable.
pub trait AdjudicatorEffect: std::fmt::Debug + Send + Sync {
    /// Record a finalized verdict to the (future) audit ledger.
    fn record(&self, op: &PermissionOperation, verdict: &RuleVerdict);
}

/// A no-op effect sink for unit tests / unconfigured environments.
#[derive(Debug, Default, Clone, Copy)]
pub struct NoopEffect;

impl AdjudicatorEffect for NoopEffect {
    fn record(&self, _op: &PermissionOperation, _verdict: &RuleVerdict) {}
}

/// The guardian adjudicator.
#[derive(Debug)]
pub struct GuardianAdjudicator<J = crate::judge::HeuristicRiskJudge> {
    mode: SessionMode,
    judge: J,
    effect: Box<dyn AdjudicatorEffect>,
}

impl<J: RiskJudge + Default> GuardianAdjudicator<J> {
    pub fn new(mode: SessionMode) -> Self {
        Self { mode, judge: J::default(), effect: Box::new(NoopEffect) }
    }
}

impl<J: RiskJudge> GuardianAdjudicator<J> {
    /// Replace the effect sink (audit logging, telemetry).
    pub fn with_effect(mut self, effect: Box<dyn AdjudicatorEffect>) -> Self {
        self.effect = effect;
        self
    }

    /// The active session mode.
    pub fn mode(&self) -> SessionMode {
        self.mode
    }

    /// Evaluate a single operation to a [`RuleVerdict`].
    ///
    /// The `policy` callback is the existing rule engine's allow/deny/confirm
    /// decision; the guardian wraps it with session-mode gating and risk.
    pub fn adjudicate<F>(&self, op: &PermissionOperation, policy: F) -> RuleVerdict
    where
        F: FnOnce(&PermissionOperation) -> Permission,
    {
        // 1. Session-mode gate runs first (outer envelope).
        let mode_forces = self.mode_gate(op);

        // 2. Rule engine.
        let mut verdict = policy(op);

        // 3. Risk scoring (pure, decoupled).
        let risk = self.judge.score(op);

        // 4. Apply session adjustments.
        let mut session_adjusted = false;

        if matches!(mode_forces, SessionAdjust::Confirm) && verdict != Permission::Deny {
            verdict = Permission::Confirm;
            session_adjusted = true;
        } else if matches!(mode_forces, SessionAdjust::Allow) && verdict == Permission::Confirm {
            // yolo: Confirm -> Allow(record-only); Deny stays absolute.
            verdict = Permission::Allow;
            session_adjusted = true;
        }

        // 5. Reason reflecting the dominant factor.
        let reason = self.build_reason(op, &risk, session_adjusted);

        let rule = RuleVerdict { verdict, risk, reason, session_adjusted };
        self.effect.record(op, &rule);
        rule
    }

    /// Compute the session-mode adjustment, if any.
    fn mode_gate(&self, op: &PermissionOperation) -> SessionAdjust {
        // `plan` forces confirm for every operation.
        if self.mode.is_plan() {
            return SessionAdjust::Confirm;
        }
        // Conservative non-yolo modes force confirm on side-effecting ops.
        if self.mode.forces_confirm_for_side_effects() && op_is_side_effecting(op) {
            return SessionAdjust::Confirm;
        }
        // yolo downgrades confirm -> allow (audit-only).
        if self.mode.downgrades_confirm_to_allow() {
            return SessionAdjust::Allow;
        }
        SessionAdjust::None
    }

    fn build_reason(
        &self,
        op: &PermissionOperation,
        risk: &Risk,
        session_adjusted: bool,
    ) -> String {
        let mut parts = Vec::new();
        parts.push(format!("risk={}", risk.level().label()));
        for f in risk.factors.iter().take(2) {
            parts.push(f.label_str().to_string());
        }
        if session_adjusted {
            parts.push(format!("mode={}", self.mode));
        }
        format!("{}: {}", op_desc(op), parts.join(", "))
    }
}

/// Outcome of the session-mode gate before the rule engine runs.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum SessionAdjust {
    None,
    Confirm,
    Allow,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::judge::NoopRiskJudge;
    use forge_domain::Permission;
    use forge_domain::PermissionOperation;

    fn write_op() -> PermissionOperation {
        PermissionOperation::Write {
            path: "/tmp/out.txt".into(),
            cwd: "/home/u/proj".into(),
            message: "write".into(),
        }
    }

    fn never_allows(permission: Permission) -> impl Fn(&PermissionOperation) -> Permission {
        move |_| permission.clone()
    }

    #[test]
    fn build_mode_is_neutral() {
        let g = GuardianAdjudicator::<NoopRiskJudge>::new(SessionMode::Build);
        let v = g.adjudicate(&write_op(), never_allows(Permission::Allow));
        assert!(v.is_allowed());
        assert!(!v.session_adjusted);
    }

    #[test]
    fn plan_forces_confirm() {
        let g = GuardianAdjudicator::<NoopRiskJudge>::new(SessionMode::Plan);
        let v = g.adjudicate(&write_op(), never_allows(Permission::Allow));
        assert!(v.requires_confirm());
        assert!(v.session_adjusted);
    }

    #[test]
    fn yolo_downgrades_confirm_to_allow() {
        let g = GuardianAdjudicator::<NoopRiskJudge>::new(SessionMode::Yolo);
        let v = g.adjudicate(&write_op(), never_allows(Permission::Confirm));
        assert!(v.is_allowed());
        assert!(v.session_adjusted);
    }

    #[test]
    fn yolo_never_overrides_deny() {
        let g = GuardianAdjudicator::<NoopRiskJudge>::new(SessionMode::Yolo);
        let v = g.adjudicate(&write_op(), never_allows(Permission::Deny));
        assert!(!v.is_allowed());
        assert!(!v.session_adjusted); // denials are absolute, not "adjusted"
        assert_eq!(v.verdict, Permission::Deny);
    }

    #[test]
    fn effect_records_verdict() {
        use std::sync::{Arc, Mutex};
        let count = Arc::new(Mutex::new(0usize));
        #[derive(Debug)]
        struct Recording {
            count: Arc<Mutex<usize>>,
        }
        impl AdjudicatorEffect for Recording {
            fn record(&self, _op: &PermissionOperation, _v: &RuleVerdict) {
                *self.count.lock().unwrap() += 1;
            }
        }
        let rec = Recording { count: count.clone() };
        let g = GuardianAdjudicator::<NoopRiskJudge>::new(SessionMode::Build)
            .with_effect(Box::new(rec));
        g.adjudicate(&write_op(), never_allows(Permission::Allow));
        assert_eq!(*count.lock().unwrap(), 1);
    }

    #[test]
    fn risk_is_carried() {
        use crate::judge::HeuristicRiskJudge;
        let g = GuardianAdjudicator::<HeuristicRiskJudge>::new(SessionMode::Build);
        let op = PermissionOperation::Execute { command: "rm -rf /".into(), cwd: "/home/u".into() };
        let v = g.adjudicate(&op, never_allows(Permission::Confirm));
        // Heuristic judge flags destructive commands as high-ish risk.
        assert!(v.risk.score > 0.5);
        assert!(v.requires_confirm());
    }
}
