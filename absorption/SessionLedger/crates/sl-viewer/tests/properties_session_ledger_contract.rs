//! Property evidence for `session_ledger::distill::contract_extractor::HeuristicContractExtractor`.
//!
//! The heuristic contract extractor is the P2 adapter for [`ContractExtractor`]
//! in the session-ledger distill pipeline. It powers the acceptance-contract
//! slice of any `ContinuationBundle` (success criteria, test commands,
//! constraints, do-not-touch rules). If `extract_contract` drifts — pattern
//! coverage breaks, deduplication stops working, or the trait path diverges
//! from the associated function — every acceptance gate downstream consumes
//! stale contract data.

use proptest::prelude::*;
use session_ledger::distill::contract_extractor::HeuristicContractExtractor;
use session_ledger::domain::session::{Corpus, Message, Role, Session};
use session_ledger::ports::ContractExtractor;

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

fn make_session(id: &str, messages: &[(Role, &str)]) -> Session {
    let mut session = Session::new(id, Corpus::Forge);
    for (role, content) in messages {
        session.messages.push(Message::new(*role, *content));
    }
    session
}

// ── Empty / whitespace sessions ────────────────────────────────────────────

proptest! {
    /// Empty sessions always produce an empty `Contract`.
    #[test]
    fn empty_session_produces_empty_contract(_dummy in 0_u8..1) {
        let session = Session::new("empty", Corpus::Forge);
        let c = HeuristicContractExtractor::extract_contract(&session);
        prop_assert!(c.is_empty());
        prop_assert_eq!(c.success_criteria.len(), 0);
        prop_assert_eq!(c.tests_or_verifications.len(), 0);
        prop_assert_eq!(c.constraints.len(), 0);
        prop_assert_eq!(c.do_not_touch.len(), 0);
    }

    /// Whitespace-only messages never contribute findings.
    #[test]
    fn whitespace_only_messages_produce_empty_contract(
        n_blank in 1_usize..4,
    ) {
        let mut messages: Vec<(Role, &str)> = Vec::new();
        for _ in 0..n_blank {
            messages.push((Role::User, "   \t\n  "));
        }
        let session = make_session("blank", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        prop_assert!(c.success_criteria.is_empty());
        prop_assert!(c.tests_or_verifications.is_empty());
        prop_assert!(c.constraints.is_empty());
        prop_assert!(c.do_not_touch.is_empty());
    }
}

// ── Section shape ──────────────────────────────────────────────────────────

proptest! {
    /// Every success criterion starts with `Goal/requirement: '` and ends with `'`.
    #[test]
    fn success_criteria_section_shape(
        body in "[a-zA-Z0-9 .]{1,80}",
    ) {
        let owned = format!("the goal is {}", body);
        let s = owned.as_str();
        let messages = vec![(Role::User, s)];
        let session = make_session("criteria-shape", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        for crit in &c.success_criteria {
            prop_assert!(crit.starts_with("Goal/requirement: '"));
            prop_assert!(crit.ends_with("'"));
        }
    }

    /// Every test/verification string starts with `Verification: '` and ends with `'`.
    #[test]
    fn verification_section_shape(
        body in "[a-zA-Z0-9 .]{1,80}",
    ) {
        let owned = format!("verify {}", body);
        let s = owned.as_str();
        let messages = vec![(Role::User, s)];
        let session = make_session("verify-shape", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        for v in &c.tests_or_verifications {
            prop_assert!(v.starts_with("Verification: '"));
            prop_assert!(v.ends_with("'"));
        }
    }

    /// Every constraint string starts with `Constraint: '` and ends with `'`.
    #[test]
    fn constraint_section_shape(
        body in "[a-zA-Z0-9 .]{1,80}",
    ) {
        let owned = format!("this must {}", body);
        let s = owned.as_str();
        let messages = vec![(Role::User, s)];
        let session = make_session("constraint-shape", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        for ct in &c.constraints {
            prop_assert!(ct.starts_with("Constraint: '"));
            prop_assert!(ct.ends_with("'"));
        }
    }

    /// Every do-not-touch string starts with `Do-not-touch: '` and ends with `'`.
    #[test]
    fn do_not_touch_section_shape(
        body in "[a-zA-Z0-9 .]{1,80}",
    ) {
        let owned = format!("don't touch {}", body);
        let s = owned.as_str();
        let messages = vec![(Role::User, s)];
        let session = make_session("dnt-shape", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        for dnt in &c.do_not_touch {
            prop_assert!(dnt.starts_with("Do-not-touch: '"));
            prop_assert!(dnt.ends_with("'"));
        }
    }
}

// ── Pattern coverage ───────────────────────────────────────────────────────

proptest! {
    /// Every documented criteria pattern is detected on a minimal trigger.
    #[test]
    fn every_documented_criteria_pattern_detected(pat in proptest::sample::select(CRITERIA_PATTERNS)) {
        let body = format!("the {pat} is rust");
        let messages = vec![(Role::User, body.as_str())];
        let session = make_session("criteria-coverage", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        prop_assert!(!c.success_criteria.is_empty(), "criteria pattern {pat} must be detected");
    }

    /// Every documented test pattern is detected.
    #[test]
    fn every_documented_test_pattern_detected(pat in proptest::sample::select(TEST_PATTERNS)) {
        let body = format!("please {pat} now");
        let messages = vec![(Role::User, body.as_str())];
        let session = make_session("test-coverage", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        prop_assert!(!c.tests_or_verifications.is_empty(), "test pattern {pat} must be detected");
    }

    /// Every documented constraint pattern is detected.
    #[test]
    fn every_documented_constraint_pattern_detected(pat in proptest::sample::select(CONSTRAINT_PATTERNS)) {
        let body = format!("this {pat} works");
        let messages = vec![(Role::User, body.as_str())];
        let session = make_session("constraint-coverage", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        prop_assert!(!c.constraints.is_empty(), "constraint pattern {pat} must be detected");
    }

    /// Every documented do-not-touch pattern is detected.
    #[test]
    fn every_documented_do_not_touch_pattern_detected(pat in proptest::sample::select(DO_NOT_TOUCH_PATTERNS)) {
        let body = format!("please {pat} the file");
        let messages = vec![(Role::User, body.as_str())];
        let session = make_session("dnt-coverage", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        prop_assert!(!c.do_not_touch.is_empty(), "do-not-touch pattern {pat} must be detected");
    }
}

// ── Case sensitivity ───────────────────────────────────────────────────────

proptest! {
    /// All patterns are detected case-insensitively.
    #[test]
    fn all_patterns_case_insensitive(
        pat in proptest::sample::select(CRITERIA_PATTERNS),
    ) {
        let upper = pat.to_uppercase();
        let body = format!("we have a {upper} now");
        let messages = vec![(Role::User, body.as_str())];
        let session = make_session("criteria-case", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        prop_assert!(!c.success_criteria.is_empty(), "criteria pattern {pat} must match case-insensitively");
    }
}

// ── Deduplication ──────────────────────────────────────────────────────────

proptest! {
    /// Repeated success criteria trigger phrases are deduplicated (the
    /// `Contract.try_join` strings are unique per pattern).
    #[test]
    fn success_criteria_deduplicated(
        body in "[a-zA-Z0-9 .]{1,40}",
    ) {
        let owned = format!("the goal is {}", body);
        let s = owned.as_str();
        let messages = vec![
            (Role::User, s),
            (Role::Assistant, s),
            (Role::User, s),
        ];
        let session = make_session("criteria-dedup", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        let goal_count = c.success_criteria.iter()
            .filter(|x| x.contains("'goal'"))
            .count();
        prop_assert_eq!(goal_count, 1, "duplicate criteria must be deduplicated");
    }

    /// Repeated do-not-touch trigger phrases are deduplicated.
    #[test]
    fn do_not_touch_deduplicated(
        body in "[a-zA-Z0-9 .]{1,40}",
    ) {
        let owned = format!("don't touch {}", body);
        let s = owned.as_str();
        let messages = vec![
            (Role::User, s),
            (Role::Assistant, s),
            (Role::User, s),
        ];
        let session = make_session("dnt-dedup", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        let dnt_count = c.do_not_touch.iter()
            .filter(|x| x.contains("don't touch"))
            .count();
        prop_assert_eq!(dnt_count, 1, "duplicate do-not-touch must be deduplicated");
    }

    /// Repeated constraint triggers are deduplicated.
    #[test]
    fn constraints_deduplicated(
        body in "[a-zA-Z0-9 .]{1,40}",
    ) {
        let owned = format!("must {}", body);
        let s = owned.as_str();
        let messages = vec![
            (Role::User, s),
            (Role::Assistant, s),
            (Role::User, s),
        ];
        let session = make_session("constraint-dedup", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        let must_count = c.constraints.iter()
            .filter(|x| x.contains("'must'"))
            .count();
        prop_assert_eq!(must_count, 1, "duplicate constraints must be deduplicated");
    }

    /// Repeated test patterns are deduplicated.
    #[test]
    fn tests_deduplicated(
        body in "[a-zA-Z0-9 .]{1,40}",
    ) {
        let owned = format!("cargo test {}", body);
        let s = owned.as_str();
        let messages = vec![
            (Role::User, s),
            (Role::Assistant, s),
            (Role::User, s),
        ];
        let session = make_session("test-dedup", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        let cargo_count = c.tests_or_verifications.iter()
            .filter(|x| x.contains("cargo test"))
            .count();
        prop_assert_eq!(cargo_count, 1, "duplicate test patterns must be deduplicated");
    }
}

// ── Determinism ────────────────────────────────────────────────────────────

proptest! {
    /// `extract_contract` is deterministic across repeated calls.
    #[test]
    fn extract_contract_is_deterministic(
        bodies in proptest::collection::vec("[a-zA-Z0-9 .]{1,40}", 0..6),
    ) {
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("det", &messages);
        let a = HeuristicContractExtractor::extract_contract(&session);
        let b = HeuristicContractExtractor::extract_contract(&session);
        prop_assert_eq!(a.success_criteria, b.success_criteria);
        prop_assert_eq!(a.tests_or_verifications, b.tests_or_verifications);
        prop_assert_eq!(a.constraints, b.constraints);
        prop_assert_eq!(a.do_not_touch, b.do_not_touch);
    }

    /// The `ContractExtractor` trait path yields the same `Contract` as the
    /// associated function.
    #[test]
    fn trait_path_matches_associated_function(
        bodies in proptest::collection::vec("[a-zA-Z0-9 .]{1,40}", 0..4),
    ) {
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("trait", &messages);
        let via_fn = HeuristicContractExtractor::extract_contract(&session);
        let extractor = HeuristicContractExtractor::new();
        let via_trait = extractor.extract(&session).expect("extract must succeed");
        prop_assert_eq!(via_fn.success_criteria, via_trait.success_criteria);
        prop_assert_eq!(via_fn.tests_or_verifications, via_trait.tests_or_verifications);
        prop_assert_eq!(via_fn.constraints, via_trait.constraints);
        prop_assert_eq!(via_fn.do_not_touch, via_trait.do_not_touch);
    }
}

// ── is_empty ↔ findings ───────────────────────────────────────────────────

proptest! {
    /// `is_empty()` is true iff every collection is empty.
    #[test]
    fn is_empty_iff_no_findings(
        bodies in proptest::collection::vec("[a-zA-Z0-9 .]{1,40}", 0..4),
    ) {
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("empty-iff", &messages);
        let c = HeuristicContractExtractor::extract_contract(&session);
        let all_empty = c.success_criteria.is_empty()
            && c.tests_or_verifications.is_empty()
            && c.constraints.is_empty()
            && c.do_not_touch.is_empty();
        if all_empty {
            prop_assert!(c.is_empty());
        }
        if !c.is_empty() {
            prop_assert!(!all_empty);
        }
    }
}
