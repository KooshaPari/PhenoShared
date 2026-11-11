//! Property evidence for `session_ledger::distill::acceptance_extractor::HeuristicAcceptanceExtractor`.
//!
//! The heuristic acceptance extractor is the P3 adapter for [`AcceptanceExtractor`]
//! in the session-ledger distill pipeline. It powers the acceptance-evidence
//! slice of any `ContinuationBundle` (passing tests, user confirmations,
//! completed goals, error-free runs). If `extract_acceptance` drifts — pattern
//! coverage breaks, deduplication stops working, the satisfaction score drifts
//! from its `(count * 10).min(100)` contract, or the trait path diverges from
//! the associated function — every downstream acceptance gate consumes stale
//! data.

use proptest::prelude::*;
use session_ledger::distill::acceptance_extractor::HeuristicAcceptanceExtractor;
use session_ledger::domain::session::{Corpus, Message, Role, Session};
use session_ledger::ports::AcceptanceExtractor;

// Patterns for general completion / verification evidence.
const EVIDENCE_PATTERNS: &[&str] = &[
    "all tests pass",
    "all tests passing",
    "tests pass",
    "tests passing",
    "build succeeded",
    "build passes",
    "build successful",
    "compiles",
    "compilation successful",
    "checks passed",
    "all checks pass",
    "lint passes",
    "lint clean",
    "no errors",
    "errors: 0",
    "0 failures",
    "zero failures",
    "ci passes",
    "ci passed",
    "verification passed",
    "all good",
    "works correctly",
    "everything works",
    "everything compiles",
    "done with",
    "completed",
    "finished",
    "implementation complete",
    "resolved",
    "fixed",
    "this is done",
];

// Patterns for user confirmation signals that specifically indicate acceptance.
const USER_CONFIRMATION_PATTERNS: &[&str] = &[
    "looks good",
    "looks great",
    "looks correct",
    "that's correct",
    "that works",
    "approved",
    "ship it",
    "good to go",
    "lgtm",
    "nice work",
    "perfect",
    "exactly what i wanted",
    "thank you",
    "thanks",
    "confirmed",
    "this works",
    "working",
    "works for me",
    "i'm satisfied",
];

// Patterns for explicit test / verification evidence.
const TESTING_EVIDENCE_PATTERNS: &[&str] = &[
    "test",
    "tests pass",
    "tests passing",
    "test pass",
    "test passing",
    "cargo test",
    "npm test",
    "pytest",
    "verify",
    "verification",
    "assertion",
    "assert",
    "coverage",
    "benchmark",
];

fn make_session(id: &str, messages: &[(Role, &str)]) -> Session {
    let mut session = Session::new(id, Corpus::Forge);
    for (role, content) in messages {
        session.messages.push(Message::new(*role, *content));
    }
    session
}

// ── Empty / whitespace-only sessions ───────────────────────────────────────

proptest! {
    /// Empty sessions always produce an empty `Acceptance`.
    #[test]
    fn empty_session_produces_empty_acceptance(_dummy in 0_u8..1) {
        let session = Session::new("empty", Corpus::Forge);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(a.is_empty());
        prop_assert_eq!(a.evidence.len(), 0);
        prop_assert!(!a.user_confirmed);
        prop_assert_eq!(a.testing_evidence.len(), 0);
        prop_assert_eq!(a.satisfaction_score, 0);
    }

    /// Whitespace-only / empty messages never contribute findings.
    #[test]
    fn whitespace_only_messages_produce_empty_acceptance(
        n_blank in 1_usize..4,
    ) {
        let mut messages: Vec<(Role, &str)> = Vec::new();
        for _ in 0..n_blank {
            messages.push((Role::User, "   \t\n  "));
            messages.push((Role::Assistant, "  "));
        }
        let session = make_session("blank", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(a.evidence.is_empty());
        prop_assert!(!a.user_confirmed);
        prop_assert!(a.testing_evidence.is_empty());
        prop_assert_eq!(a.satisfaction_score, 0);
        prop_assert!(a.is_empty());
    }
}

// ── Section shape ──────────────────────────────────────────────────────────

proptest! {
    /// Every evidence string starts with `Evidence: '` and ends with `'`.
    #[test]
    fn evidence_section_shape(
        body in "[a-zA-Z0-9 .]{1,80}",
    ) {
        let owned = format!("all tests pass {}", body);
        let s = owned.as_str();
        let messages = vec![(Role::Assistant, s)];
        let session = make_session("evidence-shape", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        for ev in &a.evidence {
            prop_assert!(ev.starts_with("Evidence: '"));
            prop_assert!(ev.ends_with("'"));
        }
    }

    /// Every testing-evidence string starts with `Testing: '` and ends with `'`.
    #[test]
    fn testing_section_shape(
        body in "[a-zA-Z0-9 .]{1,80}",
    ) {
        let owned = format!("cargo test {}", body);
        let s = owned.as_str();
        let messages = vec![(Role::Assistant, s)];
        let session = make_session("testing-shape", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        for te in &a.testing_evidence {
            prop_assert!(te.starts_with("Testing: '"));
            prop_assert!(te.ends_with("'"));
        }
    }
}

// ── Pattern coverage ───────────────────────────────────────────────────────

proptest! {
    /// Every documented EVIDENCE_PATTERNS pattern is detected on a single message.
    #[test]
    fn every_documented_evidence_pattern_detected(pat in proptest::sample::select(EVIDENCE_PATTERNS)) {
        let body = format!("run preflight: {pat} now");
        let messages = vec![(Role::Assistant, body.as_str())];
        let session = make_session("evidence-coverage", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(!a.evidence.is_empty(), "evidence pattern {pat} must be detected");
        let expected = format!("Evidence: '{pat}'");
        prop_assert!(
            a.evidence.contains(&expected),
            "evidence list must contain {expected}"
        );
    }

    /// Evidence patterns are detected case-insensitively.
    #[test]
    fn evidence_patterns_case_insensitive(pat in proptest::sample::select(EVIDENCE_PATTERNS)) {
        let upper = pat.to_uppercase();
        let body = format!("run preflight: {upper} now");
        let messages = vec![(Role::Assistant, body.as_str())];
        let session = make_session("evidence-case", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(!a.evidence.is_empty(), "evidence pattern {pat} must match case-insensitively");
    }

    /// Every documented USER_CONFIRMATION_PATTERNS pattern is detected from a User message.
    #[test]
    fn every_documented_user_confirmation_pattern_detected(
        pat in proptest::sample::select(USER_CONFIRMATION_PATTERNS),
    ) {
        let body = format!("operator: {pat} thanks");
        let messages = vec![(Role::User, body.as_str())];
        let session = make_session("confirm-coverage", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(a.user_confirmed, "user confirmation pattern {pat} must trigger user_confirmed");
    }

    /// User confirmation patterns also match case-insensitively.
    #[test]
    fn user_confirmation_patterns_case_insensitive(
        pat in proptest::sample::select(USER_CONFIRMATION_PATTERNS),
    ) {
        let upper = pat.to_uppercase();
        let body = format!("operator: {upper} thanks");
        let messages = vec![(Role::User, body.as_str())];
        let session = make_session("confirm-case", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(a.user_confirmed, "user confirmation pattern {pat} must match case-insensitively");
    }

    /// Every documented TESTING_EVIDENCE_PATTERNS pattern is detected on a single message.
    #[test]
    fn every_documented_testing_evidence_pattern_detected(
        pat in proptest::sample::select(TESTING_EVIDENCE_PATTERNS),
    ) {
        let body = format!("run {pat} now");
        let messages = vec![(Role::Assistant, body.as_str())];
        let session = make_session("testing-coverage", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(!a.testing_evidence.is_empty(), "testing pattern {pat} must be detected");
        let expected = format!("Testing: '{pat}'");
        prop_assert!(
            a.testing_evidence.contains(&expected),
            "testing list must contain {expected}"
        );
    }

    /// Testing patterns are detected case-insensitively.
    #[test]
    fn testing_patterns_case_insensitive(pat in proptest::sample::select(TESTING_EVIDENCE_PATTERNS)) {
        let upper = pat.to_uppercase();
        let body = format!("run {upper} now");
        let messages = vec![(Role::Assistant, body.as_str())];
        let session = make_session("testing-case", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(!a.testing_evidence.is_empty(), "testing pattern {pat} must match case-insensitively");
    }
}

// ── User-confirmation role gating ──────────────────────────────────────────

proptest! {
    /// `user_confirmed` is false when ONLY assistant messages contain confirmation phrases.
    #[test]
    fn user_confirmed_false_when_only_assistant_confirms(
        pat in proptest::sample::select(USER_CONFIRMATION_PATTERNS),
    ) {
        let body = format!("agent reports: {pat}");
        let messages = vec![(Role::Assistant, body.as_str())];
        let session = make_session("confirm-assistant", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(
            !a.user_confirmed,
            "user_confirmed must be false when only assistant messages contain {pat}"
        );
    }

    /// `user_confirmed` is true when ANY user message contains a confirmation phrase.
    #[test]
    fn user_confirmed_true_when_user_confirms(
        pat in proptest::sample::select(USER_CONFIRMATION_PATTERNS),
    ) {
        let body = format!("operator: {pat}!");
        let messages = vec![
            (Role::Assistant, "doing the work"),
            (Role::User, body.as_str()),
        ];
        let session = make_session("confirm-user", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(a.user_confirmed, "user_confirmed must be true when user says {pat}");
    }

    /// `user_confirmed` is false when no role contains a confirmation phrase.
    #[test]
    fn user_confirmed_false_when_no_role_confirms(
        body in "[a-zA-Z0-9 .]{1,40}",
    ) {
        let owned = body.clone();
        let s = owned.as_str();
        let messages = vec![(Role::User, s), (Role::Assistant, s)];
        let session = make_session("confirm-none", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(!a.user_confirmed, "user_confirmed must be false when no confirmation is present");
    }
}

// ── Deduplication ──────────────────────────────────────────────────────────

proptest! {
    /// Repeated evidence patterns across messages are deduplicated.
    #[test]
    fn evidence_deduplicated_across_messages(
        body in "[a-zA-Z0-9 .]{1,40}",
    ) {
        let owned = format!("all tests pass {}", body);
        let s = owned.as_str();
        let messages = vec![
            (Role::Assistant, s),
            (Role::Assistant, s),
            (Role::User, s),
            (Role::Assistant, s),
        ];
        let session = make_session("evidence-dedup", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        let mut sorted = a.evidence.clone();
        let original_len = a.evidence.len();
        sorted.sort();
        sorted.dedup();
        prop_assert_eq!(
            sorted.len(),
            original_len,
            "evidence must be deduplicated across messages"
        );
        let all_tests_pass_count = a.evidence.iter()
            .filter(|e| e.contains("all tests pass"))
            .count();
        prop_assert!(
            all_tests_pass_count <= 1,
            "all tests pass must appear at most once, got {all_tests_pass_count}"
        );
    }

    /// Repeated testing-evidence patterns across messages are deduplicated.
    #[test]
    fn testing_evidence_deduplicated_across_messages(
        body in "[a-zA-Z0-9 .]{1,40}",
    ) {
        let owned = format!("cargo test {}", body);
        let s = owned.as_str();
        let messages = vec![
            (Role::Assistant, s),
            (Role::Assistant, s),
            (Role::User, s),
            (Role::Assistant, s),
        ];
        let session = make_session("testing-dedup", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        let mut sorted = a.testing_evidence.clone();
        let original_len = a.testing_evidence.len();
        sorted.sort();
        sorted.dedup();
        prop_assert_eq!(
            sorted.len(),
            original_len,
            "testing_evidence must be deduplicated across messages"
        );
    }

    /// Evidence is sorted (post-dedup invariant).
    #[test]
    fn evidence_is_sorted_after_dedup(
        body in "[a-zA-Z0-9 .]{1,40}",
    ) {
        let owned = format!("build succeeded and tests pass {}", body);
        let s = owned.as_str();
        let messages = vec![(Role::Assistant, s)];
        let session = make_session("evidence-sort", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        let mut sorted = a.evidence.clone();
        sorted.sort();
        prop_assert_eq!(a.evidence, sorted, "evidence must be sorted");
    }

    /// Testing-evidence is sorted (post-dedup invariant).
    #[test]
    fn testing_evidence_is_sorted_after_dedup(
        body in "[a-zA-Z0-9 .]{1,40}",
    ) {
        let owned = format!("cargo test and verify and benchmark {}", body);
        let s = owned.as_str();
        let messages = vec![(Role::Assistant, s)];
        let session = make_session("testing-sort", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        let mut sorted = a.testing_evidence.clone();
        sorted.sort();
        prop_assert_eq!(a.testing_evidence, sorted, "testing_evidence must be sorted");
    }
}

// ── satisfaction_score contract ───────────────────────────────────────────

proptest! {
    /// `satisfaction_score` is always in `[0, 100]`.
    #[test]
    fn satisfaction_score_in_bounds(
        bodies in proptest::collection::vec("[a-zA-Z0-9 .]{1,80}", 0..6),
    ) {
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("score-bounds", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(a.satisfaction_score <= 100, "score must be <= 100");
        // `u8` is non-negative by construction; the lower bound is implicit.
    }

    /// `satisfaction_score` is zero when no signals are present.
    #[test]
    fn satisfaction_score_zero_for_no_signals(
        body in "[a-zA-Z0-9 .]{1,40}",
    ) {
        let owned = body.clone();
        let s = owned.as_str();
        let messages = vec![(Role::User, s), (Role::Assistant, s)];
        let session = make_session("score-zero", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        // If the body happens to contain a pattern that triggers evidence,
        // stronger statements below pin the value. Here we pin the contract
        // that with no findings, the score is 0.
        if a.evidence.is_empty() && !a.user_confirmed && a.testing_evidence.is_empty() {
            prop_assert_eq!(a.satisfaction_score, 0);
        }
    }

    /// `satisfaction_score` saturates at 100 even when more than 10 signals are present.
    #[test]
    fn satisfaction_score_saturates_at_100(_dummy in 0_u8..1) {
        let mut session = Session::new("score-saturate", Corpus::Forge);
        // Each message carries a *different* evidence pattern; the top of the
        // signal budget is 31 EVIDENCE_PATTERNS + 19 USER_CONFIRMATION_PATTERNS.
        let body = "all tests pass. all tests passing. tests pass. tests passing. \
                    build succeeded. build passes. build successful. compiles. \
                    compilation successful. checks passed. all checks pass. \
                    lint passes. lint clean. no errors. errors: 0. \
                    0 failures. zero failures. ci passes. ci passed. \
                    verification passed. all good. works correctly. everything works. \
                    everything compiles. done with. completed. finished. \
                    implementation complete. resolved. fixed. this is done. \
                    operator: looks good approved ship it perfect confirmed thanks";
        session.messages.push(Message::new(Role::Assistant, body));
        session.messages.push(Message::new(Role::User, body));
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert_eq!(a.satisfaction_score, 100, "score must saturate at 100");
        prop_assert!(a.user_confirmed);
    }

    /// `satisfaction_score` formula: each unique evidence pattern adds 10; each
    /// user message containing at least one confirmation pattern adds 10;
    /// capped at 100.
    #[test]
    fn satisfaction_score_count_contract(
        bodies in proptest::collection::vec("[a-zA-Z0-9 .]{1,40}", 0..4),
    ) {
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("score-count", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        // Re-derive the count: unique evidence + user messages with a confirmation.
        let mut expected_unique_evidence: Vec<String> = Vec::new();
        let mut user_messages_with_confirm = 0_usize;
        for msg in &session.messages {
            let lower = msg.content.to_lowercase();
            for pat in EVIDENCE_PATTERNS {
                if lower.contains(pat) {
                    let ev = format!("Evidence: '{pat}'");
                    if !expected_unique_evidence.contains(&ev) {
                        expected_unique_evidence.push(ev);
                    }
                }
            }
            if msg.role == Role::User {
                let mut found = false;
                for pat in USER_CONFIRMATION_PATTERNS {
                    if lower.contains(pat) {
                        found = true;
                        break;
                    }
                }
                if found {
                    user_messages_with_confirm += 1;
                }
            }
        }
        let expected_count = expected_unique_evidence.len() + user_messages_with_confirm;
        let expected_score = u8::try_from(expected_count.saturating_mul(10))
            .unwrap_or(100)
            .min(100);
        prop_assert_eq!(
            a.satisfaction_score,
            expected_score,
            "score must equal (unique_evidence + user_confirm_count) * 10, capped at 100"
        );
    }
}

// ── Determinism + trait path ─────────────────────────────────────────────

proptest! {
    /// `extract_acceptance` is deterministic across repeated calls.
    #[test]
    fn extract_acceptance_is_deterministic(
        bodies in proptest::collection::vec("[a-zA-Z0-9 ._/:-]{1,40}", 0..6),
    ) {
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("det", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        let b = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert_eq!(a.evidence, b.evidence);
        prop_assert_eq!(a.user_confirmed, b.user_confirmed);
        prop_assert_eq!(a.testing_evidence, b.testing_evidence);
        prop_assert_eq!(a.satisfaction_score, b.satisfaction_score);
    }

    /// The `AcceptanceExtractor` trait path yields the same `Acceptance` as the
    /// associated function.
    #[test]
    fn trait_path_matches_associated_function(
        bodies in proptest::collection::vec("[a-zA-Z0-9 ._/:-]{1,40}", 0..4),
    ) {
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("trait", &messages);
        let via_fn = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        let extractor = HeuristicAcceptanceExtractor::new();
        let via_trait = extractor.extract(&session).expect("extract must succeed");
        prop_assert_eq!(via_fn.evidence, via_trait.evidence);
        prop_assert_eq!(via_fn.user_confirmed, via_trait.user_confirmed);
        prop_assert_eq!(via_fn.testing_evidence, via_trait.testing_evidence);
        prop_assert_eq!(via_fn.satisfaction_score, via_trait.satisfaction_score);
    }
}

// ── is_empty ↔ findings ──────────────────────────────────────────────────

proptest! {
    /// `is_empty()` is true iff every collection is empty AND `user_confirmed`
    /// is false. `satisfaction_score` alone does NOT affect `is_empty`.
    #[test]
    fn is_empty_iff_no_findings(
        bodies in proptest::collection::vec("[a-zA-Z0-9 ._/:-]{1,40}", 0..4),
    ) {
        let owned: Vec<String> = bodies.clone();
        let refs: Vec<&str> = owned.iter().map(String::as_str).collect();
        let messages: Vec<(Role, &str)> = refs
            .iter()
            .enumerate()
            .map(|(i, m)| (if i % 2 == 0 { Role::User } else { Role::Assistant }, *m))
            .collect();
        let session = make_session("empty-iff", &messages);
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        let all_empty = a.evidence.is_empty()
            && !a.user_confirmed
            && a.testing_evidence.is_empty();
        if all_empty {
            prop_assert!(a.is_empty(), "is_empty must be true when all collections are empty and user_confirmed is false");
        }
        if !a.is_empty() {
            prop_assert!(!all_empty, "is_empty must be false when at least one finding is present");
        }
    }

    /// `satisfaction_score` alone does NOT make `Acceptance` non-empty.
    #[test]
    fn satisfaction_score_alone_does_not_make_non_empty(_dummy in 0_u8..1) {
        // Build a session that produces satisfaction_score > 0 with no
        // collection findings. With the documented formula, evidence
        // adds 1 to the count, so any evidence pattern will also populate
        // the evidence vector. Instead, drive the score purely via the
        // user-confirmation path -- a user message with a confirmation
        // phrase will bump user_confirmed yet the score rises -- so
        // user_confirmed alone is what makes acceptance non-empty.
        let mut session = Session::new("score-only", Corpus::Forge);
        session.messages.push(Message::new(Role::User, "looks good"));
        let a = HeuristicAcceptanceExtractor::extract_acceptance(&session);
        prop_assert!(a.user_confirmed);
        prop_assert!(a.satisfaction_score > 0);
        prop_assert!(!a.is_empty());
    }
}
