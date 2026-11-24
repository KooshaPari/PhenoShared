//! Session-mode gate (P0.1.1).
//!
//! A `SessionMode` is the *outer envelope* of allowed operation classes.
//! It runs **before** rule evaluation: it decides whether a tool operation
//! is even allowed to proceed to the normal rule/guardian flow, forcing a
//! confirm for side-effecting operations in conservative modes and
//! short-circuiting the user-prompt in `yolo` mode.

use std::fmt::Display;

use serde::{Deserialize, Serialize};

use forge_domain::Permission;

/// The outer operational envelope for the current session.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum SessionMode {
    /// Read-only exploration. Every Write / Execute / Fetch is forced to
    /// `Confirm` (strict default-deny; no operation auto-allowed).
    Plan,
    /// Standard mode: the rule engine decides, then the guardian reviews
    /// only `Confirm`-worthy operations.
    #[default]
    Build,
    /// Diff-review only: local edits (no new file) are auto-allowed; new
    /// files and anything else go through `Confirm`.
    AcceptEdits,
    /// Yolo: every `Confirm` becomes `Allow` (audit-only) for the session
    /// duration. The audit log is the only backstop. **Deny is absolute.**
    Yolo,
}

impl SessionMode {
    /// Only `plan` forces every side-effecting operation to confirm. `build`
    /// is the neutral default — the rule engine decides and the guardian
    /// merely reviews. `accept-edits` auto-allows local edits rather than
    /// forcing a uniform confirm.
    pub fn forces_confirm_for_side_effects(&self) -> bool {
        matches!(self, SessionMode::Plan)
    }

    /// `yolo` downgrades `Confirm` (but never `Deny`).
    pub fn downgrades_confirm_to_allow(&self) -> bool {
        matches!(self, SessionMode::Yolo)
    }

    /// In `plan` mode every operation (even reads) is forced to confirm.
    pub fn is_plan(&self) -> bool {
        matches!(self, SessionMode::Plan)
    }

    /// `accept-edits` auto-allows local writes.
    pub fn is_accept_edits(&self) -> bool {
        matches!(self, SessionMode::AcceptEdits)
    }

    /// Pure runtime mode-gate: given the rule engine's decision and whether
    /// the operation is side-effecting, return the final permission.
    ///
    /// * `plan` — any side-effecting op is forced to `Confirm`.
    /// * `yolo` — any `Confirm` becomes `Allow` (audit-only); `Deny` is absolute.
    /// * `build` / `accept-edits` — the rule decision passes through unchanged.
    pub fn apply(&self, rule: Permission, is_side_effecting: bool) -> Permission {
        match self {
            SessionMode::Plan if is_side_effecting => Permission::Confirm,
            SessionMode::Yolo if rule == Permission::Confirm => Permission::Allow,
            _ => rule,
        }
    }
}

impl Display for SessionMode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let s = match self {
            SessionMode::Plan => "plan",
            SessionMode::Build => "build",
            SessionMode::AcceptEdits => "accept-edits",
            SessionMode::Yolo => "yolo",
        };
        write!(f, "{s}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn plan_forces_confirm_for_side_effects() {
        assert!(SessionMode::Plan.forces_confirm_for_side_effects());
        assert!(SessionMode::Plan.is_plan());
    }

    #[test]
    fn build_is_neutral() {
        assert!(!SessionMode::Build.forces_confirm_for_side_effects());
        assert!(!SessionMode::Build.downgrades_confirm_to_allow());
        assert!(!SessionMode::Build.is_plan());
    }

    #[test]
    fn yolo_downgrades_but_not_plan() {
        assert!(SessionMode::Yolo.downgrades_confirm_to_allow());
        assert!(!SessionMode::Yolo.is_plan());
    }

    #[test]
    fn accept_edits_not_plan_or_yolo() {
        assert!(SessionMode::AcceptEdits.is_accept_edits());
        assert!(!SessionMode::AcceptEdits.is_plan());
        assert!(!SessionMode::AcceptEdits.downgrades_confirm_to_allow());
    }

    #[test]
    fn default_is_build() {
        assert_eq!(SessionMode::default(), SessionMode::Build);
    }

    #[test]
    fn plan_forces_confirm_on_side_effecting() {
        assert_eq!(
            SessionMode::Plan.apply(Permission::Allow, true),
            Permission::Confirm
        );
        // Non-side-effecting (e.g. a read) is left alone.
        assert_eq!(
            SessionMode::Plan.apply(Permission::Allow, false),
            Permission::Allow
        );
    }

    #[test]
    fn yolo_downgrades_confirm_but_never_deny() {
        assert_eq!(
            SessionMode::Yolo.apply(Permission::Confirm, true),
            Permission::Allow
        );
        assert_eq!(
            SessionMode::Yolo.apply(Permission::Deny, true),
            Permission::Deny
        );
    }

    #[test]
    fn build_is_neutral_gate() {
        assert_eq!(
            SessionMode::Build.apply(Permission::Confirm, true),
            Permission::Confirm
        );
        assert_eq!(
            SessionMode::Build.apply(Permission::Allow, true),
            Permission::Allow
        );
    }

    #[test]
    fn accept_edits_passes_through() {
        assert_eq!(
            SessionMode::AcceptEdits.apply(Permission::Allow, true),
            Permission::Allow
        );
        assert_eq!(
            SessionMode::AcceptEdits.apply(Permission::Deny, true),
            Permission::Deny
        );
    }

    #[test]
    fn serde_kebab_case() {
        let mode = SessionMode::AcceptEdits;
        let json = serde_json::to_string(&mode).unwrap();
        assert_eq!(json, "\"accept-edits\"");
        let back: SessionMode = serde_json::from_str(&json).unwrap();
        assert_eq!(back, mode);
    }

    #[test]
    fn display_names() {
        assert_eq!(SessionMode::Plan.to_string(), "plan");
        assert_eq!(SessionMode::Yolo.to_string(), "yolo");
        assert_eq!(SessionMode::AcceptEdits.to_string(), "accept-edits");
    }
}
