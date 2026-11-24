//! Property evidence for `session_ledger::detect_unfinished`,
//! `project_unfinished_work`, and `WorklogProjection::from_session`
//! (the crash-recovery / lost-work projection pipeline).
//!
//! The worklog projector is the SSOT that decides whether a session
//! is "safe to discard" or "needs a resume". If `detect_unfinished`
//! drifts (false positives inflate the Unfinished tab; false
//! negatives strand real recovery work) the operator loses trust in
//! the viewer.
//!
//! Every `Role` ↔ `UnfinishedReason` mapping, the completion-marker
//! whitelist, and the `summarize` budget are pinned here.

use proptest::prelude::*;
use session_ledger::domain::session::{Corpus, Message, Role, Session};
use session_ledger::domain::worklog::{
    detect_unfinished, project_unfinished_work, UnfinishedReason, WorklogProjection,
};

// ── Strategies ─────────────────────────────────────────────────────────────

const ROLES: &[Role] = &[Role::User, Role::Assistant, Role::Subagent, Role::Tool, Role::System];

const COMPLETION_MARKERS: &[&str] = &[
    "complete",
    "completed",
    "done",
    "[completed]",
    "<completed>",
    "status: complete",
    "status: completed",
    "task complete",
    "task completed",
];

fn role_choice() -> impl Strategy<Value = Role> {
    prop::sample::select(ROLES.to_vec())
}

// ── detect_unfinished ──────────────────────────────────────────────────────

proptest! {
    /// Empty session → `None` (nothing to detect).
    #[test]
    fn empty_session_detects_no_unfinished_work(_seed in any::<u32>()) {
        let session = Session::new("empty", Corpus::Forge);
        prop_assert!(detect_unfinished(&session).is_none());
    }

    /// A session whose final message is `Role::User` projects as
    /// `AwaitingAssistantResponse`.
    #[test]
    fn final_user_turn_is_awaiting_assistant_response(
        content in "[a-zA-Z0-9 .,!?-]{1,40}",
    ) {
        let mut session = Session::new("u", Corpus::Forge);
        session.messages = vec![Message::new(Role::User, content)];
        let item = detect_unfinished(&session).expect("user work is unfinished");
        prop_assert_eq!(item.reason, UnfinishedReason::AwaitingAssistantResponse);
        prop_assert_eq!(item.session_id, "u");
        prop_assert_eq!(item.message_count, 1);
    }

    /// A session whose final message is `Role::Tool` or `Role::Subagent`
    /// projects as `InterruptedExecution`.
    #[test]
    fn final_tool_or_subagent_turn_is_interrupted_execution(
        final_role in prop::sample::select(vec![Role::Tool, Role::Subagent]),
    ) {
        let mut session = Session::new("i", Corpus::Forge);
        session.messages = vec![
            Message::new(Role::User, "Run migration"),
            Message::new(Role::Assistant, "starting"),
            Message::new(final_role, "log line"),
        ];
        let item = detect_unfinished(&session).expect("tool/subagent tail is unfinished");
        prop_assert_eq!(item.reason, UnfinishedReason::InterruptedExecution);
    }

    /// A session whose final assistant message has a completion marker
    /// (any of the documented whitelist strings) projects as `None`.
    #[test]
    fn assistant_with_completion_marker_is_finished(
        marker_idx in 0..COMPLETION_MARKERS.len(),
    ) {
        let marker = COMPLETION_MARKERS[marker_idx];
        let mut session = Session::new("d", Corpus::Forge);
        session.messages = vec![
            Message::new(Role::User, "do it"),
            Message::new(Role::Assistant, format!("intro\n{marker}\nmore text")),
        ];
        prop_assert!(detect_unfinished(&session).is_none(),
            "marker {marker:?} should mark session finished");
    }

    /// A session whose final assistant message lacks any completion
    /// marker projects as `MissingCompletionMarker`.
    #[test]
    fn assistant_without_completion_marker_is_unfinished(
        body in "[a-zA-Z0-9 .,!?]{1,40}",
    ) {
        let mut session = Session::new("a", Corpus::Forge);
        session.messages = vec![
            Message::new(Role::User, "do it"),
            Message::new(Role::Assistant, body),
        ];
        let item = detect_unfinished(&session).expect("missing marker is unfinished");
        prop_assert_eq!(item.reason, UnfinishedReason::MissingCompletionMarker);
    }

    /// Every `UnfinishedWorkItem` carries the originating session id
    /// and the original `message_count`.
    #[test]
    fn unfinished_item_carries_session_metadata(
        n in 1_usize..5,
    ) {
        let mut session = Session::new("session-meta", Corpus::Forge);
        session.messages = (0..n)
            .map(|i| Message::new(Role::User, format!("prompt {i}")))
            .collect();
        let item = detect_unfinished(&session).expect("non-empty is unfinished");
        prop_assert_eq!(item.session_id, "session-meta");
        prop_assert_eq!(item.message_count, n);
        prop_assert_eq!(item.corpus, Corpus::Forge);
    }

    /// The summary field never exceeds 241 characters (240 + an ellipsis
    /// suffix when the source is longer).
    #[test]
    fn summary_bounded_at_241_chars(
        body in ".{0,500}",
    ) {
        let mut session = Session::new("s", Corpus::Forge);
        session.messages = vec![Message::new(Role::User, body)];
        let item = detect_unfinished(&session).expect("user work is unfinished");
        prop_assert!(item.summary.chars().count() <= 241,
            "summary len {} > 241: {:?}", item.summary.chars().count(), item.summary);
    }

    /// The summary never carries embedded newlines or tab characters
    /// (the content was whitespace-normalized).
    #[test]
    fn summary_is_single_line(
        body in ".{1,200}",
    ) {
        let mut session = Session::new("s", Corpus::Forge);
        session.messages = vec![Message::new(Role::User, body)];
        let item = detect_unfinished(&session).expect("user work is unfinished");
        prop_assert!(!item.summary.contains('\n'));
        prop_assert!(!item.summary.contains('\t'));
    }
}

// ── project_unfinished_work ─────────────────────────────────────────────────

proptest! {
    /// `project_unfinished_work` returns one item per unfinished
    /// session in the input slice, in input order.
    #[test]
    fn project_unfinished_work_one_per_unfinished_session(
        n_finished in 0_usize..4,
        n_unfinished in 0_usize..4,
    ) {
        let mut sessions = Vec::new();
        for i in 0..n_finished {
            let mut s = Session::new(format!("finished-{i}"), Corpus::Forge);
            s.messages = vec![
                Message::new(Role::User, "do it"),
                Message::new(Role::Assistant, "complete"),
            ];
            sessions.push(s);
        }
        for i in 0..n_unfinished {
            let mut s = Session::new(format!("unfinished-{i}"), Corpus::Forge);
            s.messages = vec![Message::new(Role::User, "do it")];
            sessions.push(s);
        }
        let projected = project_unfinished_work(&sessions);
        prop_assert_eq!(projected.len(), n_unfinished);
        for (idx, item) in projected.iter().enumerate() {
            prop_assert_eq!(&item.session_id, &format!("unfinished-{idx}"));
        }
    }

    /// `project_unfinished_work` is deterministic across calls.
    #[test]
    fn project_unfinished_work_deterministic(
        n in 0_usize..5,
    ) {
        let mut sessions = Vec::new();
        for i in 0..n {
            let mut s = Session::new(format!("s-{i}"), Corpus::Forge);
            s.messages = vec![Message::new(Role::User, format!("msg {i}"))];
            sessions.push(s);
        }
        let a = project_unfinished_work(&sessions);
        let b = project_unfinished_work(&sessions);
        prop_assert_eq!(a, b);
    }
}

// ── WorklogProjection::from_session ─────────────────────────────────────────

proptest! {
    /// `WorklogProjection::from_session` carries `message_count` and
    /// zero or one unfinished item, matching `detect_unfinished`.
    #[test]
    fn worklog_projection_matches_detect(
        n in 0_usize..5,
        final_role in role_choice(),
    ) {
        let mut session = Session::new("wp", Corpus::Forge);
        session.messages = (0..n)
            .map(|i| {
                // Alternate user / assistant so the message list is
                // meaningful; final role is whatever the strategy picks.
                let role = if i == n - 1 { final_role } else if i % 2 == 0 { Role::User } else { Role::Assistant };
                let content = match role {
                    Role::Assistant => "complete".to_string(),
                    _ => format!("msg {i}"),
                };
                Message::new(role, content)
            })
            .collect();
        let projection = WorklogProjection::from_session(&session);
        prop_assert_eq!(projection.message_count, n);
        let detected = detect_unfinished(&session);
        match detected {
            Some(_) => prop_assert_eq!(projection.unfinished.len(), 1),
            None => prop_assert!(projection.unfinished.is_empty()),
        }
    }
}
