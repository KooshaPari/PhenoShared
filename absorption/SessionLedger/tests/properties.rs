//! Property evidence for dedup/merge/OKF contracts and intent lifecycle FSM.

use std::collections::HashSet;

use proptest::prelude::*;
use session_ledger::{
    detect_unfinished, parse_jsonl_sessions, process_session, Corpus, DedupKey, Intent,
    IntentState, MergeError, MergeExecutor, Message, OkfDocument, Role, Session, UnfinishedReason,
};

/// Legal intent FSM edges: forward path, re-extract to Pending, prune from Verified.
fn legal_intent_edges() -> &'static [(IntentState, IntentState)] {
    use IntentState::{Extracted, Extracting, Pending, Pruned, Verified};
    &[
        (Pending, Extracting),
        (Extracting, Extracted),
        (Extracting, Pending),
        (Extracted, Verified),
        (Extracted, Pending),
        (Verified, Pruned),
        (Verified, Pending),
    ]
}

fn intent_state(index: u8) -> IntentState {
    match index % 5 {
        0 => IntentState::Pending,
        1 => IntentState::Extracting,
        2 => IntentState::Extracted,
        3 => IntentState::Verified,
        _ => IntentState::Pruned,
    }
}

/// Apply only legal transitions; returns None when the step is rejected.
fn try_intent_step(state: IntentState, next: IntentState) -> Option<IntentState> {
    state.can_transition(next).then_some(next)
}

fn session_with_messages(
    id: &str,
    corpus: Corpus,
    cwd: &str,
    messages: Vec<(String, Option<i64>)>,
) -> Session {
    let mut session = Session::new(id, corpus);
    session.cwd = Some(cwd.to_owned());
    session.messages = messages
        .into_iter()
        .map(|(content, ts_ms)| Message { role: Role::User, content, ts_ms })
        .collect();
    session
}

fn role(index: u8) -> Role {
    match index % 5 {
        0 => Role::User,
        1 => Role::Assistant,
        2 => Role::Subagent,
        3 => Role::Tool,
        _ => Role::System,
    }
}

proptest! {
    #[test]
    fn dedup_key_is_stable_under_documented_normalization(
        cwd in "[a-zA-Z0-9_./-]{1,64}",
        topic in "[a-zA-Z0-9_-]{1,48}",
        left_id in "[a-zA-Z0-9_-]{1,24}",
        right_id in "[a-zA-Z0-9_-]{1,24}",
    ) {
        let mut left = Session::new(left_id, Corpus::Forge);
        left.cwd = Some(cwd.clone());

        let mut right = Session::new(right_id, Corpus::Cursor);
        right.cwd = Some(format!(" \t{}\n", cwd.to_ascii_uppercase()));

        let canonical = DedupKey::derive(&left, &topic);
        let normalized = DedupKey::derive(
            &right,
            &format!(" \t{}\n", topic.to_ascii_uppercase()),
        );

        prop_assert_eq!(&canonical, &normalized);
        prop_assert_eq!(canonical.as_str().len(), 64);
        prop_assert!(
            canonical
                .as_str()
                .bytes()
                .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        );
    }

    #[test]
    fn merge_is_permutation_invariant(
        topic in "[a-zA-Z0-9_-]{1,48}",
        alpha_messages in prop::collection::vec(
            ("[ -~]{0,80}", prop::option::of(any::<i64>())),
            0..12,
        ),
        beta_messages in prop::collection::vec(
            ("[ -~]{0,80}", prop::option::of(any::<i64>())),
            0..12,
        ),
    ) {
        let alpha = session_with_messages(
            "alpha",
            Corpus::Forge,
            "/same/scope",
            alpha_messages,
        );
        let beta = session_with_messages(
            "beta",
            Corpus::Cursor,
            "/same/scope",
            beta_messages,
        );

        let forward = MergeExecutor::default()
            .merge(&[alpha.clone(), beta.clone()], &topic)
            .expect("same-scope sessions merge");
        let reversed = MergeExecutor::default()
            .merge(&[beta, alpha], &topic)
            .expect("input permutation also merges");

        prop_assert_eq!(forward, reversed);
    }

    #[test]
    fn merge_is_idempotent_for_duplicate_members(
        topic in "[a-zA-Z0-9_-]{1,48}",
        messages in prop::collection::vec(
            ("[ -~]{0,80}", prop::option::of(any::<i64>())),
            0..12,
        ),
    ) {
        let source = session_with_messages(
            "source",
            Corpus::Codex,
            "/same/scope",
            messages,
        );

        let once = MergeExecutor::default()
            .merge(std::slice::from_ref(&source), &topic)
            .expect("single member merges");
        let duplicated = MergeExecutor::default()
            .merge(&[source.clone(), source], &topic)
            .expect("duplicate member merges");

        prop_assert_eq!(once, duplicated);
    }

    #[test]
    fn okf_json_roundtrip_preserves_structural_invariants(
        id in "[a-zA-Z0-9_-]{1,24}",
        cwd in prop::option::of("[a-zA-Z0-9_./ -]{0,64}"),
        title in prop::option::of("[ -~]{0,80}"),
        messages in prop::collection::vec(
            (
                0u8..5,
                "[ -~]{0,120}",
                prop::option::of(any::<i64>()),
            ),
            0..20,
        ),
    ) {
        let mut session = Session::new(id, Corpus::ClaudeCode);
        session.cwd = cwd;
        session.title = title;
        session.messages = messages
            .into_iter()
            .map(|(role_index, content, ts_ms)| Message {
                role: role(role_index),
                content,
                ts_ms,
            })
            .collect();

        let document = process_session(&session);
        let encoded = serde_json::to_vec(&document).expect("OKF serializes");
        let decoded: OkfDocument = serde_json::from_slice(&encoded).expect("OKF deserializes");

        prop_assert_eq!(&document, &decoded);
        prop_assert_eq!(&document.okf, "1.0");
        prop_assert_eq!(&document.source_id, &document.provenance.source_id);

        let entity_ids = document
            .entities
            .iter()
            .map(|entity| entity.id.as_str())
            .collect::<HashSet<_>>();
        prop_assert_eq!(entity_ids.len(), document.entities.len());
        for relation in &document.relations {
            prop_assert!(entity_ids.contains(relation.source.as_str()));
            prop_assert!(entity_ids.contains(relation.target.as_str()));
        }
    }

    #[test]
    fn dedup_keys_differ_for_distinct_normalized_scopes(
        left_cwd in "[a-zA-Z0-9_./-]{1,64}",
        right_cwd in "[a-zA-Z0-9_./-]{1,64}",
        left_topic in "[a-zA-Z0-9_-]{1,48}",
        right_topic in "[a-zA-Z0-9_-]{1,48}",
    ) {
        let left_scope = left_cwd.trim().to_lowercase();
        let right_scope = right_cwd.trim().to_lowercase();
        let left_slug = left_topic.trim().to_lowercase();
        let right_slug = right_topic.trim().to_lowercase();
        prop_assume!(left_scope != right_scope || left_slug != right_slug);

        let mut left = Session::new("left", Corpus::Forge);
        left.cwd = Some(left_cwd);
        let mut right = Session::new("right", Corpus::Cursor);
        right.cwd = Some(right_cwd);

        prop_assert_ne!(
            DedupKey::derive(&left, &left_topic),
            DedupKey::derive(&right, &right_topic)
        );
    }

    #[test]
    fn merge_with_derived_key_matches_plain_merge(
        topic in "[a-zA-Z0-9_-]{1,48}",
        wrong_topic in "[a-zA-Z0-9_-]{1,48}",
        alpha_messages in prop::collection::vec(
            ("[ -~]{0,80}", prop::option::of(any::<i64>())),
            0..8,
        ),
        beta_messages in prop::collection::vec(
            ("[ -~]{0,80}", prop::option::of(any::<i64>())),
            0..8,
        ),
    ) {
        prop_assume!(topic.trim().to_lowercase() != wrong_topic.trim().to_lowercase());

        let alpha = session_with_messages(
            "alpha",
            Corpus::Forge,
            "/same/scope",
            alpha_messages,
        );
        let beta = session_with_messages(
            "beta",
            Corpus::Cursor,
            "/same/scope",
            beta_messages,
        );
        let sessions = [alpha, beta];
        let expected_key = DedupKey::derive(&sessions[0], &topic);

        let plain = MergeExecutor::default()
            .merge(&sessions, &topic)
            .expect("same-scope sessions merge");
        let keyed = MergeExecutor::default()
            .merge_with_key(&sessions, &topic, &expected_key)
            .expect("derived key matches merge scope");
        prop_assert_eq!(&plain, &keyed);
        prop_assert_eq!(&plain.session.id, expected_key.as_str());
        prop_assert_eq!(&plain.manifest.dedup_key, &expected_key);

        let wrong_key = DedupKey::derive(&sessions[0], &wrong_topic);
        let mismatch = MergeExecutor::default()
            .merge_with_key(&sessions, &topic, &wrong_key)
            .expect_err("wrong key must be rejected");
        let is_key_mismatch = matches!(mismatch, MergeError::KeyMismatch { .. });
        prop_assert!(is_key_mismatch);
    }

    #[test]
    fn okf_pipeline_is_deterministic_and_jsonl_roundtrips(
        id in "[a-zA-Z0-9_-]{1,24}",
        cwd in prop::option::of("[a-zA-Z0-9_./ -]{0,64}"),
        title in prop::option::of("[ -~]{0,80}"),
        messages in prop::collection::vec(
            (
                0u8..5,
                "[ -~]{0,120}",
                prop::option::of(any::<i64>()),
            ),
            0..12,
        ),
        peer_id in "[a-zA-Z0-9_-]{1,24}",
    ) {
        let mut session = Session::new(id, Corpus::Codex);
        session.cwd = cwd;
        session.title = title;
        session.messages = messages
            .into_iter()
            .map(|(role_index, content, ts_ms)| Message {
                role: role(role_index),
                content,
                ts_ms,
            })
            .collect();

        let first = process_session(&session);
        let second = process_session(&session);
        prop_assert_eq!(&first, &second);
        prop_assert_eq!(&first.source_id, &session.id);
        prop_assert_eq!(&first.provenance.source_id, &session.id);
        prop_assert_eq!(first.provenance.corpus.as_str(), session.corpus.as_str());

        let peer = Session::new(peer_id, Corpus::Cursor);
        let jsonl = format!(
            "{}\n\n{}\n",
            serde_json::to_string(&session).expect("session serializes"),
            serde_json::to_string(&peer).expect("peer serializes"),
        );
        let parsed = parse_jsonl_sessions(jsonl.as_bytes()).expect("valid JSONL parses");
        prop_assert_eq!(parsed, vec![session, peer]);
    }

    // ── Intent lifecycle FSM ─────────────────────────────────────────────────

    #[test]
    fn intent_fsm_can_transition_matches_legal_edge_set(
        from_idx in 0u8..5,
        to_idx in 0u8..5,
    ) {
        let from = intent_state(from_idx);
        let to = intent_state(to_idx);
        let expected = legal_intent_edges().iter().any(|&(a, b)| a == from && b == to);
        prop_assert_eq!(from.can_transition(to), expected);
    }

    #[test]
    fn intent_fsm_pruned_is_terminal_for_all_successors(next_idx in 0u8..5) {
        let next = intent_state(next_idx);
        prop_assert!(IntentState::Pruned.is_terminal());
        prop_assert!(!IntentState::Pruned.can_transition(next));
        prop_assert!(!IntentState::Pruned.is_prune_eligible());
    }

    #[test]
    fn intent_fsm_prune_eligible_iff_verified(state_idx in 0u8..5) {
        let state = intent_state(state_idx);
        prop_assert_eq!(state.is_prune_eligible(), state == IntentState::Verified);
        prop_assert_eq!(
            state.can_transition(IntentState::Pruned),
            state == IntentState::Verified
        );
    }

    #[test]
    fn intent_fsm_non_pruned_states_are_not_terminal(state_idx in 0u8..4) {
        let state = intent_state(state_idx);
        prop_assume!(state != IntentState::Pruned);
        prop_assert!(!state.is_terminal());
    }

    #[test]
    fn intent_fsm_walk_rejects_illegal_steps_and_honors_legal_ones(
        start_idx in 0u8..5,
        steps in prop::collection::vec(0u8..5, 0..24),
    ) {
        let mut state = intent_state(start_idx);
        for step_idx in steps {
            let next = intent_state(step_idx);
            match try_intent_step(state, next) {
                Some(advanced) => {
                    prop_assert_eq!(advanced, next);
                    prop_assert!(
                        legal_intent_edges()
                            .iter()
                            .any(|&(a, b)| a == state && b == next)
                    );
                    state = advanced;
                }
                None => {
                    prop_assert!(!state.can_transition(next));
                }
            }
            if state.is_terminal() {
                prop_assert_eq!(state, IntentState::Pruned);
                for stuck_idx in 0u8..5 {
                    prop_assert!(!state.can_transition(intent_state(stuck_idx)));
                }
            }
        }
    }

    #[test]
    fn intent_fsm_forward_happy_path_reaches_pruned_only_via_verified(
        revert_budget in 0usize..4,
    ) {
        let mut state = IntentState::Pending;
        for _ in 0..revert_budget {
            prop_assert!(state.can_transition(IntentState::Extracting));
            state = IntentState::Extracting;
            prop_assert!(state.can_transition(IntentState::Pending));
            state = IntentState::Pending;
        }

        for (from, to) in [
            (IntentState::Pending, IntentState::Extracting),
            (IntentState::Extracting, IntentState::Extracted),
            (IntentState::Extracted, IntentState::Verified),
            (IntentState::Verified, IntentState::Pruned),
        ] {
            prop_assert_eq!(state, from);
            prop_assert!(state.can_transition(to));
            if to == IntentState::Pruned {
                prop_assert!(state.is_prune_eligible());
            }
            state = to;
        }
        prop_assert!(state.is_terminal());
        prop_assert!(!state.is_prune_eligible());
    }

    #[test]
    fn intent_emptiness_depends_only_on_payload_fields(
        goal in prop::option::of("[ -~]{1,64}"),
        signals in prop::collection::vec("[ -~]{1,48}", 0..6),
        constraints in prop::collection::vec("[ -~]{1,48}", 0..6),
        user_turn_count in 0usize..64,
    ) {
        let intent = Intent {
            goal: goal.clone(),
            acceptance_signals: signals.clone(),
            constraints: constraints.clone(),
            user_turn_count,
        };
        let expected_empty =
            goal.is_none() && signals.is_empty() && constraints.is_empty();
        prop_assert_eq!(intent.is_empty(), expected_empty);
        prop_assert_eq!(Intent::empty().is_empty(), true);
        prop_assert_eq!(Intent::empty().user_turn_count, 0);
    }

    // ── Unfinished-work lifecycle (session completion signals) ───────────────

    #[test]
    fn unfinished_detection_classifies_final_role_deterministically(
        id in "[a-zA-Z0-9_-]{1,24}",
        prefix in prop::collection::vec(
            (0u8..5, "[ -~]{0,40}"),
            0..8,
        ),
        final_role_idx in 0u8..5,
        final_content in "[ -~]{0,80}",
        include_user in any::<bool>(),
    ) {
        let mut session = Session::new(id, Corpus::Forge);
        if include_user {
            session.messages.push(Message {
                role: Role::User,
                content: "operator ask".into(),
                ts_ms: Some(1),
            });
        }
        for (role_idx, content) in prefix {
            session.messages.push(Message {
                role: role(role_idx),
                content,
                ts_ms: None,
            });
        }
        let final_role = role(final_role_idx);
        session.messages.push(Message {
            role: final_role,
            content: final_content.clone(),
            ts_ms: Some(9),
        });

        let has_user = session.messages.iter().any(|m| m.role == Role::User);
        let detected = detect_unfinished(&session);

        if !has_user {
            prop_assert!(detected.is_none());
            return Ok(());
        }

        let completed = final_role == Role::Assistant
            && final_content.lines().map(str::trim).any(|line| {
                matches!(
                    line.to_ascii_lowercase().as_str(),
                    "complete"
                        | "completed"
                        | "done"
                        | "[completed]"
                        | "<completed>"
                        | "status: complete"
                        | "status: completed"
                        | "task complete"
                        | "task completed"
                )
            });
        if completed {
            prop_assert!(detected.is_none());
            return Ok(());
        }

        let item = detected.expect("unfinished when user present without completion");
        prop_assert_eq!(&item.session_id, &session.id);
        prop_assert_eq!(item.message_count, session.messages.len());
        let expected_reason = match final_role {
            Role::User => UnfinishedReason::AwaitingAssistantResponse,
            Role::Tool | Role::Subagent => UnfinishedReason::InterruptedExecution,
            Role::Assistant | Role::System => UnfinishedReason::MissingCompletionMarker,
        };
        prop_assert_eq!(item.reason, expected_reason);
    }

    // ── IntentState serde round-trip (kebab-case contract) ─────────────────

    #[test]
    fn intent_state_json_round_trip_preserves_variant(state_idx in 0u8..5) {
        let state = intent_state(state_idx);
        let json = serde_json::to_string(&state).expect("serialize IntentState");
        // `#[serde(rename_all = "kebab-case")]` contract — every variant
        // serialises to its lowercase kebab-case Debug name. This guards
        // against drift in the rename attribute.
        let expected_name = match state {
            IntentState::Pending => "pending",
            IntentState::Extracting => "extracting",
            IntentState::Extracted => "extracted",
            IntentState::Verified => "verified",
            IntentState::Pruned => "pruned",
        };
        prop_assert_eq!(json.clone(), format!("\"{expected_name}\""));
        let restored: IntentState = serde_json::from_str(&json).expect("deserialize IntentState");
        prop_assert_eq!(restored, state);
    }

    #[test]
    fn intent_state_terminal_invariant_holds_across_serde(
        state_idx in 0u8..5,
    ) {
        // `is_terminal` must agree with the serde JSON representation:
        // Pruned is the only terminal state, and serialising + deserialising
        // it must not silently turn it into something non-terminal.
        let state = intent_state(state_idx);
        prop_assert_eq!(state.is_terminal(), state == IntentState::Pruned);
        let json = serde_json::to_string(&state).expect("serialize");
        let restored: IntentState = serde_json::from_str(&json).expect("deserialize");
        prop_assert_eq!(restored.is_terminal(), state.is_terminal());
    }
}
