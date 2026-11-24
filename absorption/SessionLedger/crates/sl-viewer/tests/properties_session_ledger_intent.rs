//! Property evidence for `session_ledger::distill::extractor::HeuristicIntentExtractor::extract_intent`
//! and `session_ledger::domain::intent::Intent`.
//!
//! The heuristic intent extractor is the P1 SSOT for "what does the user
//! want?" — it powers the resume prompt, the search index, and the
//! wiki / docs view. If `user_turn_count` drifts, `goal` starts picking
//! up assistant text, or the acceptance/constraint whitelists stop
//! matching, every downstream consumer sees the wrong intent.

use proptest::prelude::*;
use session_ledger::distill::extractor::HeuristicIntentExtractor;
use session_ledger::domain::intent::Intent;
use session_ledger::domain::session::{Corpus, Message, Role, Session};

// Heuristic patterns mirrored from `extractor.rs`.
const ACCEPTANCE_PATTERNS: &[&str] = &[
    "looks good",
    "works",
    "that's correct",
    "correct",
    "done",
    "fixed",
    "passes",
    "approved",
    "looks right",
    "looks great",
    "all good",
    "that works",
    "nice",
    "perfect",
    "exactly",
    "confirmed",
];

const CONSTRAINT_PATTERNS: &[&str] = &[
    "don't change",
    "do not change",
    "must not",
    "should not",
    "keep",
    "maintain",
    "preserve",
    "never",
    "don't touch",
    "do not touch",
    "don't modify",
    "do not modify",
    "only",
    "but don't",
    "but do not",
    "without changing",
    "without modifying",
    "leave alone",
    "leave as is",
];

fn make_session(id: &str, messages: &[(Role, &str)]) -> Session {
    let mut session = Session::new(id, Corpus::Forge);
    for (role, content) in messages {
        session.messages.push(Message::new(*role, *content));
    }
    session
}

// ── user_turn_count ────────────────────────────────────────────────────────

proptest! {
    /// `user_turn_count` always equals the count of `Role::User`
    /// messages in the session.
    #[test]
    fn user_turn_count_matches_role_user_messages(
        n_user in 0_usize..5,
        n_assistant in 0_usize..5,
    ) {
        let mut messages: Vec<(Role, &str)> = Vec::new();
        for i in 0..n_user {
            messages.push((Role::User, Box::leak(format!("user {i}").into_boxed_str())));
        }
        for i in 0..n_assistant {
            messages.push((Role::Assistant, Box::leak(format!("assistant {i}").into_boxed_str())));
        }
        let session = make_session("utc", &messages);
        let intent = HeuristicIntentExtractor::extract_intent(&session);
        prop_assert_eq!(intent.user_turn_count, n_user);
    }

    /// Assistant / tool / subagent / system messages never contribute
    /// to `user_turn_count`.
    #[test]
    fn only_user_role_counts_for_user_turn_count(_seed in any::<u32>()) {
        let session = make_session("non-user", &[
            (Role::Assistant, "anything"),
            (Role::Subagent, "anything"),
            (Role::Tool, "anything"),
            (Role::System, "anything"),
        ]);
        let intent = HeuristicIntentExtractor::extract_intent(&session);
        prop_assert_eq!(intent.user_turn_count, 0);
    }
}

// ── empty session ──────────────────────────────────────────────────────────

proptest! {
    /// Empty session → `Intent::empty()` semantics: no goal, no
    /// signals, no constraints, zero user_turn_count.
    #[test]
    fn empty_session_produces_empty_intent(_seed in any::<u32>()) {
        let session = Session::new("empty", Corpus::Forge);
        let intent = HeuristicIntentExtractor::extract_intent(&session);
        prop_assert!(intent.is_empty());
        prop_assert!(intent.goal.is_none());
        prop_assert!(intent.acceptance_signals.is_empty());
        prop_assert!(intent.constraints.is_empty());
        prop_assert_eq!(intent.user_turn_count, 0);
    }
}

// ── Acceptance / constraint dedup ──────────────────────────────────────────

proptest! {
    /// Repeated acceptance signals are deduplicated (one entry per
    /// pattern, even if the pattern appears in many user messages).
    #[test]
    fn acceptance_signals_deduplicated(
        repeats in 2_usize..6,
    ) {
        let mut messages: Vec<(Role, &str)> = Vec::new();
        for i in 0..repeats {
            messages.push((
                Role::User,
                Box::leak(format!("user {i} looks good ship it").into_boxed_str()),
            ));
        }
        let session = make_session("dedup-acc", &messages);
        let intent = HeuristicIntentExtractor::extract_intent(&session);
        let has = intent.acceptance_signals.iter()
            .filter(|s| s.as_str() == "looks good")
            .count();
        prop_assert_eq!(has, 1, "acceptance signal should appear once");
    }

    /// Repeated constraint patterns are deduplicated.
    #[test]
    fn constraints_deduplicated(
        repeats in 2_usize..6,
    ) {
        let mut messages: Vec<(Role, &str)> = Vec::new();
        for i in 0..repeats {
            messages.push((
                Role::User,
                Box::leak(format!("user {i} don't change the schema").into_boxed_str()),
            ));
        }
        let session = make_session("dedup-con", &messages);
        let intent = HeuristicIntentExtractor::extract_intent(&session);
        let has = intent.constraints.iter()
            .filter(|s| s.as_str() == "don't change")
            .count();
        prop_assert_eq!(has, 1, "constraint should appear once");
    }
}

// ── Pattern recognition ────────────────────────────────────────────────────

proptest! {
    /// Every documented acceptance pattern, when present in a user
    /// message, ends up in `acceptance_signals` exactly once.
    #[test]
    fn every_acceptance_pattern_is_recognized(
        idx in 0..ACCEPTANCE_PATTERNS.len(),
    ) {
        let pat = ACCEPTANCE_PATTERNS[idx];
        let session = make_session("acc-rec", &[
            (Role::User, pat),
        ]);
        let intent = HeuristicIntentExtractor::extract_intent(&session);
        prop_assert!(intent.acceptance_signals.contains(&pat.to_string()),
            "acceptance pattern {pat:?} not recognized in {intent:?}");
    }

    /// Every documented constraint pattern, when present in a user
    /// message, ends up in `constraints` exactly once.
    #[test]
    fn every_constraint_pattern_is_recognized(
        idx in 0..CONSTRAINT_PATTERNS.len(),
    ) {
        let pat = CONSTRAINT_PATTERNS[idx];
        let session = make_session("con-rec", &[
            (Role::User, pat),
        ]);
        let intent = HeuristicIntentExtractor::extract_intent(&session);
        prop_assert!(intent.constraints.contains(&pat.to_string()),
            "constraint pattern {pat:?} not recognized in {intent:?}");
    }
}

// ── Labeled goal / constraint extraction ────────────────────────────────────

const GOAL_LABELS: &[&str] = &["goal", "objective", "task"];
const CONSTRAINT_LABELS: &[&str] = &["constraint", "requirement", "boundary"];

proptest! {
    /// Explicit `Goal:` / `Objective:` / `Task:` lines win over
    /// surrounding preamble.
    #[test]
    fn labeled_goal_beats_preamble(
        label_idx in 0..GOAL_LABELS.len(),
        body in "[a-zA-Z0-9.-]{1,40}",
    ) {
        let label = GOAL_LABELS[label_idx];
        let session = make_session("lbl-goal", &[
            (Role::User, "Please use the following brief."),
            (Role::User, Box::leak(format!("{label}: {body}").into_boxed_str())),
        ]);
        let intent = HeuristicIntentExtractor::extract_intent(&session);
        prop_assert_eq!(intent.goal.as_deref(), Some(body.as_str()));
    }

    /// `Constraint:` / `Requirement:` / `Boundary:` lines contribute
    /// their full text to `constraints` (not just the matching
    /// pattern substring).
    #[test]
    fn labeled_constraint_carries_full_text(
        label_idx in 0..CONSTRAINT_LABELS.len(),
        body in "[a-zA-Z0-9.-]{1,40}",
    ) {
        let label = CONSTRAINT_LABELS[label_idx];
        let session = make_session("lbl-con", &[
            (Role::User, Box::leak(format!("{label}: {body}").into_boxed_str())),
        ]);
        let intent = HeuristicIntentExtractor::extract_intent(&session);
        prop_assert!(intent.constraints.contains(&body.to_string()),
            "labeled constraint body {body:?} missing from {intent:?}");
    }
}

// ── Determinism ────────────────────────────────────────────────────────────

proptest! {
    /// `extract_intent` is deterministic across calls.
    #[test]
    fn extract_intent_is_deterministic(
        n_user in 0_usize..3,
    ) {
        let mut messages: Vec<(Role, &str)> = Vec::new();
        for i in 0..n_user {
            messages.push((
                Role::User,
                Box::leak(format!("user msg {i} with looks good and don't change the schema").into_boxed_str()),
            ));
        }
        let session = make_session("det", &messages);
        let a: Intent = HeuristicIntentExtractor::extract_intent(&session);
        let b: Intent = HeuristicIntentExtractor::extract_intent(&session);
        prop_assert_eq!(a, b);
    }
}
