//! Acceptance bundle model — the EVIDENCE / STATE of satisfaction.
//!
//! [`Acceptance`] captures what proof exists that a session's work was verified
//! or completed: passing tests, user confirmations, completed goals, error-free
//! runs. This is *distinct* from [`Contract`](super::contract::Contract), which
//! holds the *criteria* themselves; Acceptance is what proves they were met.

use serde::{Deserialize, Serialize};

/// Structured acceptance evidence extracted from a session's message stream.
///
/// This is the output of the [`AcceptanceExtractor`](crate::ports::AcceptanceExtractor)
/// port: evidence that the session's work was verified / completed.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Acceptance {
    /// Evidence statements describing verification results
    /// (e.g. "all 142 tests pass", "build succeeds", "lint clean").
    pub evidence: Vec<String>,

    /// Whether the user explicitly confirmed completion
    /// (e.g. "looks good", "ship it", "approved").
    pub user_confirmed: bool,

    /// Test / verification evidence (extracted test output, CI results, etc.).
    pub testing_evidence: Vec<String>,

    /// Heuristic satisfaction score (0–100). Derived from how many positive
    /// confirmation signals appear in the session.
    pub satisfaction_score: u8,
}

impl Acceptance {
    /// Empty acceptance — nothing extracted yet.
    #[must_use]
    pub fn empty() -> Self {
        Self {
            evidence: Vec::new(),
            user_confirmed: false,
            testing_evidence: Vec::new(),
            satisfaction_score: 0,
        }
    }

    /// Whether the extractor found any meaningful acceptance data.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.evidence.is_empty() && !self.user_confirmed && self.testing_evidence.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_acceptance_is_empty() {
        assert!(Acceptance::empty().is_empty());
    }

    #[test]
    fn empty_acceptance_defaults() {
        let a = Acceptance::empty();
        assert!(a.evidence.is_empty());
        assert!(!a.user_confirmed);
        assert!(a.testing_evidence.is_empty());
        assert_eq!(a.satisfaction_score, 0);
    }

    #[test]
    fn user_confirmed_alone_makes_it_non_empty() {
        let mut a = Acceptance::empty();
        a.user_confirmed = true;
        assert!(!a.is_empty());
    }

    #[test]
    fn evidence_alone_makes_it_non_empty() {
        let mut a = Acceptance::empty();
        a.evidence.push("all tests pass".into());
        assert!(!a.is_empty());
    }

    #[test]
    fn testing_evidence_alone_makes_it_non_empty() {
        let mut a = Acceptance::empty();
        a.testing_evidence.push("cargo test output".into());
        assert!(!a.is_empty());
    }

    #[test]
    fn satisfaction_score_alone_does_not_make_it_non_empty() {
        // satisfaction_score alone does NOT affect is_empty
        let mut a = Acceptance::empty();
        a.satisfaction_score = 99;
        assert!(a.is_empty());
    }

    #[test]
    fn fully_populated_is_not_empty() {
        let a = Acceptance {
            evidence: vec!["e".into()],
            user_confirmed: true,
            testing_evidence: vec!["t".into()],
            satisfaction_score: 100,
        };
        assert!(!a.is_empty());
    }
}
