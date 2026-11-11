//! Intent lifecycle FSM and structured intent model.
//!
//! Mirrors forgecode's forward-only intent DAG so `SessionLedger` and forgecode
//! agree on lifecycle semantics (forgecode is both an ingestion source and the
//! proven blueprint — see `docs/DESIGN.md`). The `SessionLedger` ledger acts as
//! the missing `IntentExtractor` forgecode currently stubs with `NoopIntentExtractor`.
//!
//! In addition to the FSM, this module defines the structured [`Intent`] type —
//! the output of the [`IntentExtractor`](crate::ports::IntentExtractor) port —
//! which captures the user's goal, acceptance signals, and constraints.

use serde::{Deserialize, Serialize};

/// Structured intent extracted from a session's messages.
///
/// This is the output of the [`IntentExtractor`](crate::ports::IntentExtractor)
/// port: what the user is trying to achieve, how they will know it's done, and
/// what boundaries the continuation must respect.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Intent {
    /// The user's primary goal or objective (e.g. "fix the login bug").
    pub goal: Option<String>,
    /// Signals the user uses to confirm success (e.g. "tests pass", "looks good").
    pub acceptance_signals: Vec<String>,
    /// Constraints / boundaries the continuation must honor (e.g. "don't touch auth").
    pub constraints: Vec<String>,
    /// Number of user turns contributing to this intent.
    pub user_turn_count: usize,
}

impl Intent {
    /// Empty intent — nothing extracted yet.
    #[must_use]
    pub fn empty() -> Self {
        Self {
            goal: None,
            acceptance_signals: Vec::new(),
            constraints: Vec::new(),
            user_turn_count: 0,
        }
    }

    /// Whether the extractor found any meaningful intent data.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.goal.is_none() && self.acceptance_signals.is_empty() && self.constraints.is_empty()
    }
}

/// Forward-only intent extraction lifecycle.
///
/// `Pending → Extracting → Extracted → Verified → Pruned`. A revert to
/// `Pending` is allowed (re-extraction); `Pruned` is terminal.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum IntentState {
    Pending,
    Extracting,
    Extracted,
    Verified,
    Pruned,
}

impl IntentState {
    /// Whether a transition `self → next` is permitted by the FSM.
    #[must_use]
    pub fn can_transition(self, next: IntentState) -> bool {
        use IntentState::{Extracted, Extracting, Pending, Pruned, Verified};
        matches!(
            (self, next),
            (Extracting | Extracted | Verified, Pending)
                | (Pending, Extracting)
                | (Extracting, Extracted)
                | (Extracted, Verified)
                | (Verified, Pruned)
        )
    }

    /// `Pruned` is terminal — no further transitions.
    #[must_use]
    pub fn is_terminal(self) -> bool {
        matches!(self, IntentState::Pruned)
    }

    /// Pruning is intent-gated (ADR-103): only verified intent may be pruned.
    #[must_use]
    pub fn is_prune_eligible(self) -> bool {
        matches!(self, IntentState::Verified)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── is_terminal ──────────────────────────────────────────────────────────

    #[test]
    fn pruned_is_terminal() {
        assert!(IntentState::Pruned.is_terminal());
    }

    #[test]
    fn pending_is_not_terminal() {
        assert!(!IntentState::Pending.is_terminal());
    }

    #[test]
    fn extracting_is_not_terminal() {
        assert!(!IntentState::Extracting.is_terminal());
    }

    #[test]
    fn extracted_is_not_terminal() {
        assert!(!IntentState::Extracted.is_terminal());
    }

    #[test]
    fn verified_is_not_terminal() {
        assert!(!IntentState::Verified.is_terminal());
    }

    // ── is_prune_eligible ────────────────────────────────────────────────────

    #[test]
    fn verified_is_prune_eligible() {
        assert!(IntentState::Verified.is_prune_eligible());
    }

    #[test]
    fn pending_is_not_prune_eligible() {
        assert!(!IntentState::Pending.is_prune_eligible());
    }

    #[test]
    fn extracting_is_not_prune_eligible() {
        assert!(!IntentState::Extracting.is_prune_eligible());
    }

    #[test]
    fn extracted_is_not_prune_eligible() {
        assert!(!IntentState::Extracted.is_prune_eligible());
    }

    #[test]
    fn pruned_is_not_prune_eligible() {
        assert!(!IntentState::Pruned.is_prune_eligible());
    }

    // ── can_transition — legal forward path ──────────────────────────────────

    #[test]
    fn pending_to_extracting_allowed() {
        assert!(IntentState::Pending.can_transition(IntentState::Extracting));
    }

    #[test]
    fn extracting_to_extracted_allowed() {
        assert!(IntentState::Extracting.can_transition(IntentState::Extracted));
    }

    #[test]
    fn extracted_to_verified_allowed() {
        assert!(IntentState::Extracted.can_transition(IntentState::Verified));
    }

    #[test]
    fn verified_to_pruned_allowed() {
        assert!(IntentState::Verified.can_transition(IntentState::Pruned));
    }

    // ── can_transition — legal revert to Pending ─────────────────────────────

    #[test]
    fn extracting_to_pending_allowed() {
        assert!(IntentState::Extracting.can_transition(IntentState::Pending));
    }

    #[test]
    fn extracted_to_pending_allowed() {
        assert!(IntentState::Extracted.can_transition(IntentState::Pending));
    }

    #[test]
    fn verified_to_pending_allowed() {
        assert!(IntentState::Verified.can_transition(IntentState::Pending));
    }

    // ── can_transition — illegal transitions ─────────────────────────────────

    #[test]
    fn pending_to_pending_illegal() {
        assert!(!IntentState::Pending.can_transition(IntentState::Pending));
    }

    #[test]
    fn pending_to_extracted_illegal() {
        assert!(!IntentState::Pending.can_transition(IntentState::Extracted));
    }

    #[test]
    fn pending_to_verified_illegal() {
        assert!(!IntentState::Pending.can_transition(IntentState::Verified));
    }

    #[test]
    fn pending_to_pruned_illegal() {
        assert!(!IntentState::Pending.can_transition(IntentState::Pruned));
    }

    #[test]
    fn extracting_to_verified_illegal() {
        assert!(!IntentState::Extracting.can_transition(IntentState::Verified));
    }

    #[test]
    fn extracting_to_pruned_illegal() {
        assert!(!IntentState::Extracting.can_transition(IntentState::Pruned));
    }

    #[test]
    fn extracted_to_extracting_illegal() {
        assert!(!IntentState::Extracted.can_transition(IntentState::Extracting));
    }

    #[test]
    fn extracted_to_pruned_illegal() {
        assert!(!IntentState::Extracted.can_transition(IntentState::Pruned));
    }

    #[test]
    fn verified_to_extracted_illegal() {
        assert!(!IntentState::Verified.can_transition(IntentState::Extracted));
    }

    #[test]
    fn verified_to_extracting_illegal() {
        assert!(!IntentState::Verified.can_transition(IntentState::Extracting));
    }

    #[test]
    fn pruned_to_pending_illegal() {
        assert!(!IntentState::Pruned.can_transition(IntentState::Pending));
    }

    #[test]
    fn pruned_to_extracting_illegal() {
        assert!(!IntentState::Pruned.can_transition(IntentState::Extracting));
    }

    #[test]
    fn pruned_to_extracted_illegal() {
        assert!(!IntentState::Pruned.can_transition(IntentState::Extracted));
    }

    #[test]
    fn pruned_to_verified_illegal() {
        assert!(!IntentState::Pruned.can_transition(IntentState::Verified));
    }

    #[test]
    fn pruned_to_pruned_illegal() {
        assert!(!IntentState::Pruned.can_transition(IntentState::Pruned));
    }

    // ── Intent::is_empty ─────────────────────────────────────────────────────

    #[test]
    fn empty_intent_is_empty() {
        assert!(Intent::empty().is_empty());
    }

    #[test]
    fn intent_with_goal_is_not_empty() {
        let mut i = Intent::empty();
        i.goal = Some("fix the bug".into());
        assert!(!i.is_empty());
    }

    #[test]
    fn intent_with_acceptance_signal_is_not_empty() {
        let mut i = Intent::empty();
        i.acceptance_signals.push("tests pass".into());
        assert!(!i.is_empty());
    }

    #[test]
    fn intent_with_constraint_is_not_empty() {
        let mut i = Intent::empty();
        i.constraints.push("don't touch auth".into());
        assert!(!i.is_empty());
    }

    #[test]
    fn intent_user_turn_count_does_not_affect_emptiness() {
        // user_turn_count alone does NOT make an intent non-empty
        let mut i = Intent::empty();
        i.user_turn_count = 5;
        assert!(i.is_empty());
    }

    #[test]
    fn empty_intent_fields_are_default() {
        let i = Intent::empty();
        assert!(i.goal.is_none());
        assert!(i.acceptance_signals.is_empty());
        assert!(i.constraints.is_empty());
        assert_eq!(i.user_turn_count, 0);
    }
}
