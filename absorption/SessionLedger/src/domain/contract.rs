//! Contract bundle model — the concrete acceptance criteria the work must satisfy.
//!
//! Extracted from a session's message stream: success criteria, test commands,
//! constraints, and do-not-touch rules that a continuation must honor.

use serde::{Deserialize, Serialize};

/// Structured acceptance contract extracted from a session's messages.
///
/// This is the output of the [`ContractExtractor`](crate::ports::ContractExtractor)
/// port: the concrete done-criteria, verifications, invariants, and boundaries
/// that define what "done" means and what the continuation must not break.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Contract {
    /// Explicit success criteria / acceptance conditions (e.g. "login flow works").
    pub success_criteria: Vec<String>,
    /// Test commands or verification steps (e.g. "cargo test", "npm run check").
    pub tests_or_verifications: Vec<String>,
    /// Invariants / constraints the continuation must honor.
    pub constraints: Vec<String>,
    /// Files, modules, or sections that must not be modified.
    pub do_not_touch: Vec<String>,
}

impl Contract {
    /// Empty contract — nothing extracted yet.
    #[must_use]
    pub fn empty() -> Self {
        Self {
            success_criteria: Vec::new(),
            tests_or_verifications: Vec::new(),
            constraints: Vec::new(),
            do_not_touch: Vec::new(),
        }
    }

    /// Whether the extractor found any meaningful contract data.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.success_criteria.is_empty()
            && self.tests_or_verifications.is_empty()
            && self.constraints.is_empty()
            && self.do_not_touch.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_contract_is_empty() {
        assert!(Contract::empty().is_empty());
    }

    #[test]
    fn empty_contract_all_vecs_empty() {
        let c = Contract::empty();
        assert!(c.success_criteria.is_empty());
        assert!(c.tests_or_verifications.is_empty());
        assert!(c.constraints.is_empty());
        assert!(c.do_not_touch.is_empty());
    }

    #[test]
    fn success_criteria_alone_makes_non_empty() {
        let mut c = Contract::empty();
        c.success_criteria.push("login works".into());
        assert!(!c.is_empty());
    }

    #[test]
    fn tests_or_verifications_alone_makes_non_empty() {
        let mut c = Contract::empty();
        c.tests_or_verifications.push("cargo test".into());
        assert!(!c.is_empty());
    }

    #[test]
    fn constraints_alone_makes_non_empty() {
        let mut c = Contract::empty();
        c.constraints.push("no breaking changes".into());
        assert!(!c.is_empty());
    }

    #[test]
    fn do_not_touch_alone_makes_non_empty() {
        let mut c = Contract::empty();
        c.do_not_touch.push("src/auth.rs".into());
        assert!(!c.is_empty());
    }

    #[test]
    fn fully_populated_contract_is_not_empty() {
        let c = Contract {
            success_criteria: vec!["ok".into()],
            tests_or_verifications: vec!["test".into()],
            constraints: vec!["con".into()],
            do_not_touch: vec!["file".into()],
        };
        assert!(!c.is_empty());
    }
}
