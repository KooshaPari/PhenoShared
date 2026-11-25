//! Sandbox tie-breaker (P0.1.5).
//!
//! When a risk judge returns a score landing near the allow/confirm
//! threshold, the guardian is genuinely uncertain whether a mid-range
//! operation should proceed. In that ambiguity window, the OS-level
//! sandbox's *containment capability* is the deciding factor:
//!
//! - If the sandbox is active and can fully contain a worst-case outcome
//!   (network isolated **and** workspace confined), the residual blast
//!   radius is small enough that running the operation is acceptable —
//!   the tie resolves to `Allow`.
//! - If the sandbox is off, not network-isolated, or not workspace-confined,
//!   the same operation carries unbounded blast radius — the tie resolves
//!   to `Confirm` (ask the user).
//!
//! This is deliberately a *pure, decision-only* module: it does not execute
//! anything, only reasons about a [`SandboxPolicy`] snapshot. The actual
//! sandbox execution lives in `forge_sandbox`; this module just consumes a
//! capability report so it stays unit-testable and dependency-free.

use crate::risk::{Risk, RiskFactor, RiskLabel};

/// The sandbox's capability report for a given operation.
///
/// This is a *snapshot* of what the OS-level sandbox can actually contain,
/// not a promise. A backend reports `false` for any capability it cannot
/// guarantee (e.g. the Windows JobObject placeholder can't enforce network
/// isolation yet, or Landlock <5.13 is unavailable).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SandboxPolicy {
    /// True if an OS-level sandbox (Landlock/Seatbelt/JobObject) is active.
    pub active: bool,
    /// True if the sandbox can block outbound network (no exfiltration).
    pub network_isolated: bool,
    /// True if the sandbox confines writes to the workspace root.
    pub workspace_confined: bool,
}

impl SandboxPolicy {
    /// A fully-containing sandbox — network-isolated and workspace-confined.
    pub fn fully_containing() -> Self {
        Self {
            active: true,
            network_isolated: true,
            workspace_confined: true,
        }
    }

    /// No sandbox (or one that can't guarantee containment).
    pub fn none() -> Self {
        Self {
            active: false,
            network_isolated: false,
            workspace_confined: false,
        }
    }
}

impl Default for SandboxPolicy {
    fn default() -> Self {
        Self::none()
    }
}

/// Whether the sandbox can contain a worst-case outcome for the operation.
pub fn can_contain(cap: &SandboxPolicy) -> bool {
    cap.active && cap.network_isolated && cap.workspace_confined
}

/// The tie-breaking decision between `Allow` and `Confirm` for a mid-range,
/// ambiguous risk score.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TieBreak {
    /// Sandbox fully contains the worst case — let it run.
    Allow,
    /// Sandbox can't contain the blast radius — ask the user.
    Confirm,
}

/// Break an allow/confirm tie using the sandbox containment capability.
///
/// `score` is the normalized risk `0.0..=1.0` from the judge. Only scores in
/// the ambiguity band around the threshold are resolved here; a caller should
/// handle clearly-low (allow) and clearly-high (deny/confirm) scores with the
/// rule engine before consulting this.
pub fn break_tie(cap: &SandboxPolicy) -> TieBreak {
    if can_contain(cap) {
        TieBreak::Allow
    } else {
        TieBreak::Confirm
    }
}

/// Human-readable justification of a tie-break decision, for the audit log /
/// risk display. Returns a one-line reason string.
pub fn tie_break_reason(decision: TieBreak, cap: &SandboxPolicy, score: f32) -> String {
    match decision {
        TieBreak::Allow => format!(
            "sandbox-contained (net={}, fs={}): allowed ambiguous score {:.2}",
            cap.network_isolated, cap.workspace_confined, score
        ),
        TieBreak::Confirm => {
            if !cap.active {
                format!("no OS sandbox active: confirm ambiguous score {:.2}", score)
            } else if !cap.network_isolated {
                format!(
                    "sandbox not network-isolated (exfil risk): confirm score {:.2}",
                    score
                )
            } else {
                format!(
                    "sandbox not workspace-confined (write risk): confirm score {:.2}",
                    score
                )
            }
        }
    }
}

/// The residual-sandbox-gap label folded into the risk surface when the
/// sandbox can't fully contain an ambiguous operation. We use the closest
/// existing [`RiskLabel`] so no new enum variant is required (backwards
/// compatible per the ADR).
pub fn gap_label(cap: &SandboxPolicy) -> RiskLabel {
    if !cap.network_isolated {
        RiskLabel::NetworkFetch
    } else {
        RiskLabel::SensitivePath
    }
}

/// Append a sandbox-containment verdict as a risk factor. This lets the
/// caller fold the tie-break back into a [`Risk`] so the audit trail shows
/// *why* the decision was made. If already fully containing, this is a
/// no-op (nothing to penalize).
pub fn append_tie_break_factor(risk: &mut Risk, cap: &SandboxPolicy) {
    if can_contain(cap) {
        return;
    }
    let label = gap_label(cap);
    let weight = if cap.active {
        // A partially-capable sandbox still shrinks the blast radius.
        0.12
    } else {
        // No sandbox at all: the gap is more severe.
        0.25
    };
    risk.factors.push(RiskFactor::new(label, weight));
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::risk::{Risk, RiskLabel};

    #[test]
    fn fully_containing_allows() {
        let cap = SandboxPolicy::fully_containing();
        assert!(can_contain(&cap));
        assert_eq!(break_tie(&cap), TieBreak::Allow);
    }

    #[test]
    fn absent_sandbox_confirms() {
        let cap = SandboxPolicy::none();
        assert!(!can_contain(&cap));
        assert_eq!(break_tie(&cap), TieBreak::Confirm);
    }

    #[test]
    fn active_but_network_forward_confirms() {
        // Active + workspace-confined but NOT network-isolated.
        let cap = SandboxPolicy {
            active: true,
            network_isolated: false,
            workspace_confined: true,
        };
        assert!(!can_contain(&cap));
        assert_eq!(break_tie(&cap), TieBreak::Confirm);
        let reason = tie_break_reason(TieBreak::Confirm, &cap, 0.5);
        assert!(reason.contains("network-isolated"));
    }

    #[test]
    fn active_but_not_workspace_confined_confirms() {
        let cap = SandboxPolicy {
            active: true,
            network_isolated: true,
            workspace_confined: false,
        };
        assert_eq!(break_tie(&cap), TieBreak::Confirm);
        let reason = tie_break_reason(TieBreak::Confirm, &cap, 0.6);
        assert!(reason.contains("workspace-confined"));
    }

    #[test]
    fn tie_break_reason_allow_mentions_containment() {
        let cap = SandboxPolicy::fully_containing();
        let reason = tie_break_reason(TieBreak::Allow, &cap, 0.55);
        assert!(reason.contains("sandbox-contained"));
    }

    #[test]
    fn append_factor_noop_when_containing() {
        let cap = SandboxPolicy::fully_containing();
        let mut risk = Risk::new(0.5, vec![]);
        let before = risk.factors.len();
        append_tie_break_factor(&mut risk, &cap);
        assert_eq!(risk.factors.len(), before);
    }

    #[test]
    fn append_factor_adds_when_unsandboxed() {
        let cap = SandboxPolicy::none();
        let mut risk = Risk::new(0.55, vec![]);
        append_tie_break_factor(&mut risk, &cap);
        assert_eq!(risk.factors.len(), 1);
    }

    #[test]
    fn gap_label_maps_network_and_fs() {
        let net = SandboxPolicy {
            active: true,
            network_isolated: false,
            workspace_confined: true,
        };
        let fs = SandboxPolicy {
            active: true,
            network_isolated: true,
            workspace_confined: false,
        };
        assert_eq!(gap_label(&net), RiskLabel::NetworkFetch);
        assert_eq!(gap_label(&fs), RiskLabel::SensitivePath);
    }
}
