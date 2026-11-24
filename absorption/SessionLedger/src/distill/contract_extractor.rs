//! Heuristic contract extraction — the P2 adapter for [`ContractExtractor`].
//!
//! This adapter uses lightweight string matching to extract acceptance criteria
//! from a session's message stream: success criteria, test commands, constraints,
//! and do-not-touch rules.
//!
//! Phase 3 will supersede this with an LLM-backed extractor behind the same
//! [`ContractExtractor`] trait — see `docs/DESIGN.md` §7.

use crate::domain::contract::Contract;
use crate::domain::session::Session;
use crate::ports::{ContractExtractor, PortError};

/// Heuristic-based contract extractor.
///
/// Scans user messages for:
/// - **Success criteria**: phrases like "goal", "need to", "make sure", "ensure".
/// - **Tests/verifications**: phrases like "test", "verify", "run tests".
/// - **Constraints**: phrases like "must", "important", "requirement".
/// - **Do-not-touch**: phrases like "don't touch", "leave alone".
///
/// This is intentionally simple. The LLM-backed extractor (Phase 3) will
/// replace it behind the same trait.
#[derive(Debug, Default, Clone, Copy)]
pub struct HeuristicContractExtractor;

// Patterns for success criteria (lowercased for matching).
const CRITERIA_PATTERNS: &[&str] = &[
    "goal",
    "objective",
    "need to",
    "needs to",
    "should work",
    "want to",
    "make sure",
    "ensure",
    "purpose",
    "aim",
    "requirement",
    "required",
];

// Patterns for test / verification commands.
const TEST_PATTERNS: &[&str] = &[
    "cargo test",
    "npm test",
    "npm run test",
    "yarn test",
    "go test",
    "pytest",
    "python -m pytest",
    "cargo check",
    "npm run check",
    "cargo build",
    "make test",
    "bazel test",
    "run tests",
    "verify",
    "verify that",
    "check that",
    "validate",
    "assert",
    "assert that",
    "test that",
    "should pass",
    "must pass",
];

// Patterns for constraints / invariants.
const CONSTRAINT_PATTERNS: &[&str] = &[
    "must",
    "must not",
    "mustn't",
    "important",
    "requirement",
    "required",
    "mandatory",
    "critical",
    "essential",
    "necessary",
    "must be",
    "has to",
    "have to",
    "needs to",
    "need to",
];

// Patterns for do-not-touch.
const DO_NOT_TOUCH_PATTERNS: &[&str] = &[
    "don't touch",
    "do not touch",
    "don't modify",
    "do not modify",
    "don't change",
    "do not change",
    "leave alone",
    "leave as is",
    "keep as is",
    "preserve",
    "maintain",
    "never change",
    "never modify",
    "stay as is",
];

impl HeuristicContractExtractor {
    #[must_use]
    pub fn new() -> Self {
        Self
    }

    /// Heuristically extract the acceptance contract from a session's messages.
    ///
    /// This is factored as a public associated function so it can be used
    /// directly by the compiler without going through the trait when no
    /// adapter injection is needed (P2 default).
    #[must_use]
    pub fn extract_contract(session: &Session) -> Contract {
        let mut success_criteria: Vec<String> = Vec::new();
        let mut tests_or_verifications: Vec<String> = Vec::new();
        let mut constraints: Vec<String> = Vec::new();
        let mut do_not_touch: Vec<String> = Vec::new();

        // Scan user and assistant messages for contract signals.
        for msg in &session.messages {
            let lower = msg.content.to_lowercase();

            // --- Success criteria ---
            for pat in CRITERIA_PATTERNS {
                if lower.contains(pat) {
                    let crit = format!("Goal/requirement: '{pat}'");
                    if !success_criteria.contains(&crit) {
                        success_criteria.push(crit);
                    }
                }
            }

            // --- Tests / verifications ---
            for pat in TEST_PATTERNS {
                if lower.contains(pat) {
                    let test = format!("Verification: '{pat}'");
                    if !tests_or_verifications.contains(&test) {
                        tests_or_verifications.push(test);
                    }
                }
            }

            // --- Constraints ---
            for pat in CONSTRAINT_PATTERNS {
                if lower.contains(pat) {
                    let constraint = format!("Constraint: '{pat}'");
                    if !constraints.contains(&constraint) {
                        constraints.push(constraint);
                    }
                }
            }

            // --- Do-not-touch ---
            for pat in DO_NOT_TOUCH_PATTERNS {
                if lower.contains(pat) {
                    let dnt = format!("Do-not-touch: '{pat}'");
                    if !do_not_touch.contains(&dnt) {
                        do_not_touch.push(dnt);
                    }
                }
            }
        }

        Contract { success_criteria, tests_or_verifications, constraints, do_not_touch }
    }
}

impl ContractExtractor for HeuristicContractExtractor {
    fn extract(&self, session: &Session) -> Result<Contract, PortError> {
        Ok(Self::extract_contract(session))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::session::{Corpus, Message, Role};

    fn fixture_session() -> Session {
        let mut s = Session::new("test-sess-ctr", Corpus::Forge);
        s.messages.push(Message::new(
            Role::User,
            "The goal is to add rate limiting. Needs to work with existing auth.",
        ));
        s.messages.push(Message::new(Role::Assistant, "I'll implement a token bucket approach."));
        s.messages.push(Message::new(
            Role::User,
            "Don't touch the database layer. Must pass cargo test.",
        ));
        s
    }

    #[test]
    fn extracts_success_criteria_from_goal_language() {
        let contract = HeuristicContractExtractor::extract_contract(&fixture_session());
        assert!(contract.success_criteria.iter().any(|c| c.contains("goal")));
        assert!(contract.success_criteria.len() >= 2);
    }

    #[test]
    fn extracts_test_verification_commands() {
        let contract = HeuristicContractExtractor::extract_contract(&fixture_session());
        assert!(contract.tests_or_verifications.iter().any(|t| t.contains("cargo test")));
    }

    #[test]
    fn extracts_do_not_touch_rules() {
        let contract = HeuristicContractExtractor::extract_contract(&fixture_session());
        assert!(contract.do_not_touch.iter().any(|d| d.contains("don't touch")));
    }

    #[test]
    fn extracts_constraints_from_modal_language() {
        let contract = HeuristicContractExtractor::extract_contract(&fixture_session());
        assert!(contract.constraints.iter().any(|c| c.contains("must") || c.contains("needs")));
    }

    #[test]
    fn returns_empty_contract_for_empty_session() {
        let s = Session::new("empty", Corpus::Forge);
        let contract = HeuristicContractExtractor::extract_contract(&s);
        assert!(contract.is_empty());
    }

    #[test]
    fn contract_extractor_trait_works() {
        let extractor = HeuristicContractExtractor::new();
        let contract = extractor.extract(&fixture_session()).expect("extraction should succeed");
        assert!(!contract.success_criteria.is_empty());
    }
}
