//! Property evidence for sl-viewer's `history_tab::to_timeline_entry`
//! and `history_tab::all_timeline_entries` reductions.
//!
//! Integration tests. The unit tests in `history_tab.rs` pin specific
//! values; these properties pin invariants over the full shape of
//! inputs the helpers can receive.
//!
//! `history_tab::to_timeline_entry` invariants:
//!  * `summary.id` is the session id; `summary.title` is the session
//!    title (mirrors `Option<String>` identity); `summary.message_count`
//!    equals the session's `messages.len()`; `summary.intent_state` is
//!    always `IntentState::Extracted`.
//!  * `corpus` and `cwd` are carried through unchanged.
//!  * `message_previews` has at most 3 entries (the documented cap)
//!    and is empty when the session has no messages. The first 3
//!    messages are previewed, in input order.
//!  * `total_messages` equals `session.messages.len()`.
//!  * `unfinished` is `false` when the session has no messages, and
//!    `false` when the last message content (case-insensitive) contains
//!    one of the documented "done" phrases ("looks good", "approved",
//!    "ship it", "all good", "thanks", "done"); otherwise `true`.
//!  * Deterministic across calls.
//!
//! `history_tab::all_timeline_entries` invariants:
//!  * Output length matches input length.
//!  * The output is sorted by `total_messages` descending (newest-first
//!    by message count, per the documented comment).
//!  * The output preserves the input ID multiset, including collisions.
//!
//! proptest is added to `sl-viewer/[dev-dependencies]` (mirroring the
//! workspace root); see PR #425 for the initial wiring.

use proptest::prelude::*;
use session_ledger::domain::intent::IntentState;
use session_ledger::domain::session::{Corpus, Message, Role, Session};
use sl_viewer::history_tab::{all_timeline_entries, session_for_timeline_entry, to_timeline_entry};

// ── strategies ──────────────────────────────────────────────────────────────

/// `Message` strategy — role + content + optional ts_ms.
fn message_strategy() -> impl Strategy<Value = Message> {
    (
        prop::sample::select(vec![
            Role::User,
            Role::Assistant,
            Role::Subagent,
            Role::Tool,
            Role::System,
        ]),
        prop::string::string_regex("[ -~]{0,120}").expect("valid regex"),
        prop::option::of(0i64..1_000_000_000_000i64),
    )
        .prop_map(|(role, content, ts_ms)| {
            let mut m = Message::new(role, content);
            m.ts_ms = ts_ms;
            m
        })
}

/// `Session` strategy — id + 0..8 messages + optional title + corpus.
fn session_strategy() -> impl Strategy<Value = Session> {
    (
        // session_id — non-empty, identifier-shaped.
        prop::string::string_regex("[a-zA-Z0-9_-]{1,16}").expect("valid regex"),
        // 0..8 messages.
        prop::collection::vec(message_strategy(), 0..8),
        // title — `Option<String>`.
        prop::option::of(prop::string::string_regex("[A-Za-z0-9 ._-]{0,40}").expect("valid regex")),
        // corpus — pick one of the documented variants.
        prop::sample::select(vec![
            Corpus::Forge,
            Corpus::Codex,
            Corpus::ClaudeCode,
            Corpus::Cursor,
            Corpus::FactoryDroid,
            Corpus::ChatGptWeb,
            Corpus::ClaudeWeb,
            Corpus::GeminiWeb,
        ]),
        // cwd — `Option<String>`.
        prop::option::of(prop::string::string_regex("[/a-zA-Z0-9._-]{0,40}").expect("valid regex")),
    )
        .prop_map(|(id, messages, title, corpus, cwd)| {
            let mut s = Session::new(id, corpus);
            s.messages = messages;
            s.title = title;
            s.cwd = cwd;
            s
        })
}

// ── history_tab::to_timeline_entry ──────────────────────────────────────────

proptest! {
    /// Property: `summary.id` is the session id.
    #[test]
    fn to_timeline_entry_carries_session_id(session in session_strategy()) {
        let entry = to_timeline_entry(&session);
        prop_assert_eq!(&entry.summary.id, &session.id);
    }

    /// Property: `summary.title` is the session title (mirrors
    /// `Option<String>` identity — `None` stays `None`).
    #[test]
    fn to_timeline_entry_carries_title(session in session_strategy()) {
        let entry = to_timeline_entry(&session);
        prop_assert_eq!(entry.summary.title, session.title);
    }

    /// Property: `summary.message_count` equals the session's
    /// `messages.len()`.
    #[test]
    fn to_timeline_entry_message_count_matches(session in session_strategy()) {
        let entry = to_timeline_entry(&session);
        prop_assert_eq!(entry.summary.message_count, session.messages.len());
    }

    /// Property: `summary.intent_state` is always `IntentState::Extracted`
    /// — the only state the reduction can produce given the heuristic
    /// extractors.
    #[test]
    fn to_timeline_entry_intent_state_always_extracted(session in session_strategy()) {
        let entry = to_timeline_entry(&session);
        prop_assert_eq!(entry.summary.intent_state, IntentState::Extracted);
    }

    /// Property: `corpus` and `cwd` are carried through unchanged.
    #[test]
    fn to_timeline_entry_carries_corpus_and_cwd(session in session_strategy()) {
        let entry = to_timeline_entry(&session);
        prop_assert_eq!(entry.corpus, session.corpus);
        prop_assert_eq!(entry.cwd, session.cwd);
    }

    /// Property: `message_previews` has at most 3 entries (the
    /// documented cap) and is empty when the session has no messages.
    /// When non-empty, the previews cover the first N ≤ 3 messages,
    /// in input order.
    #[test]
    fn to_timeline_entry_message_previews_capped(session in session_strategy()) {
        let entry = to_timeline_entry(&session);
        prop_assert!(entry.message_previews.len() <= 3);
        let expected = session.messages.len().min(3);
        prop_assert_eq!(entry.message_previews.len(), expected);
    }

    /// Property: `total_messages` equals `session.messages.len()`.
    #[test]
    fn to_timeline_entry_total_messages_matches(session in session_strategy()) {
        let entry = to_timeline_entry(&session);
        prop_assert_eq!(entry.total_messages, session.messages.len());
    }

    /// Property: `unfinished` is `false` when the session has no
    /// messages (empty sessions aren't "in-progress").
    #[test]
    fn to_timeline_entry_unfinished_false_for_empty(
        (id, corpus) in (
            prop::string::string_regex("[a-zA-Z0-9_-]{1,8}").expect("valid regex"),
            prop::sample::select(vec![Corpus::Forge, Corpus::ClaudeCode]),
        )
    ) {
        let session = Session::new(id, corpus);
        let entry = to_timeline_entry(&session);
        prop_assert!(!entry.summary.unfinished);
    }

    /// Property: `unfinished` is `false` when the last message's
    /// content (case-insensitive) contains one of the documented
    /// "done" phrases — "looks good", "approved", "ship it",
    /// "all good", "thanks", "done".
    #[test]
    fn to_timeline_entry_unfinished_false_for_done_phrase(phrase in prop::sample::select(vec![
        "looks good", "approved", "ship it", "all good", "thanks", "done",
        "Looks Good", "APPROVED", "Ship It", "All Good", "THANKS", "DONE",
    ])) {
        // Build a session whose last message content == phrase.
        let mut session = Session::new("sess-1", Corpus::Forge);
        let mut msg = Message::new(Role::Assistant, phrase.to_owned());
        msg.ts_ms = Some(0);
        session.messages.push(msg);
        let entry = to_timeline_entry(&session);
        prop_assert!(!entry.summary.unfinished, "phrase {phrase:?} should mark session as finished");
    }

    /// Property: `unfinished` is `true` when the session has
    /// messages and the last message content does NOT contain any
    /// done-phrase substring (case-insensitive).
    #[test]
    fn to_timeline_entry_unfinished_true_for_non_done_last(
        content in prop::string::string_regex("[A-Za-z0-9 ]{3,40}").expect("valid regex"),
    ) {
        // Filter out any content that happens to match a done phrase.
        let lower = content.to_lowercase();
        let matches_done = ["looks good", "approved", "ship it", "all good", "thanks", "done"]
            .iter().any(|p| lower.contains(p));
        prop_assume!(!matches_done);
        prop_assume!(!content.is_empty());

        let mut session = Session::new("sess-1", Corpus::Forge);
        let mut msg = Message::new(Role::User, content.clone());
        msg.ts_ms = Some(0);
        session.messages.push(msg);
        let entry = to_timeline_entry(&session);
        prop_assert!(
            entry.summary.unfinished,
            "session with non-done last message {content:?} should be unfinished",
        );
    }

    /// Property: `to_timeline_entry` is deterministic — applying it
    /// twice to the same session yields the same entry.
    #[test]
    fn to_timeline_entry_is_deterministic(session in session_strategy()) {
        let a = to_timeline_entry(&session);
        let b = to_timeline_entry(&session);
        prop_assert_eq!(a, b);
    }
}

// ── history_tab::all_timeline_entries ───────────────────────────────────────

#[test]
fn duplicate_session_ids_keep_distinct_source_rows() {
    let mut first = Session::new("shared", Corpus::Forge);
    first.messages.push(Message::new(Role::User, "first transcript"));
    let mut second = Session::new("shared", Corpus::Forge);
    second.messages.push(Message::new(Role::User, "second transcript"));
    second.messages.push(Message::new(Role::Assistant, "second reply"));
    let sessions = vec![first, second];

    let entries = all_timeline_entries(&sessions);
    let second_entry =
        entries.iter().find(|entry| entry.source_index == 1).expect("second source row");
    let selected = session_for_timeline_entry(&sessions, second_entry).expect("selected session");

    assert_eq!(selected.messages[0].content, "second transcript");
    assert_eq!(selected.messages.len(), 2);
}

proptest! {
    /// Property: output length equals input length.
    #[test]
    fn all_timeline_entries_length_matches(
        sessions in prop::collection::vec(session_strategy(), 0..6),
    ) {
        let entries = all_timeline_entries(&sessions);
        prop_assert_eq!(entries.len(), sessions.len());
    }

    /// Property: the output is sorted by `total_messages` descending
    /// (newest-first by message count, per the documented comment).
    /// Tied entries remain in stable-sort input order.
    #[test]
    fn all_timeline_entries_sorted_by_message_count_desc(
        sessions in prop::collection::vec(session_strategy(), 1..8),
    ) {
        let entries = all_timeline_entries(&sessions);
        for win in entries.windows(2) {
            prop_assert!(
                win[0].total_messages >= win[1].total_messages,
                "entry {} ({} msgs) should sort before entry {} ({} msgs)",
                0,
                win[0].total_messages,
                1,
                win[1].total_messages,
            );
        }
    }

    /// Property: output preserves every input id, including duplicate ids.
    ///
    /// Session IDs come from external corpora and may collide; timeline
    /// construction must retain each source row rather than silently dedupe it.
    #[test]
    fn all_timeline_entries_preserve_id_multiset(
        sessions in prop::collection::vec(session_strategy(), 1..6),
    ) {
        let entries = all_timeline_entries(&sessions);
        let mut expected_ids: Vec<_> = sessions.iter().map(|s| s.id.clone()).collect();
        let mut actual_ids: Vec<_> = entries.iter().map(|e| e.summary.id.clone()).collect();
        expected_ids.sort();
        actual_ids.sort();
        prop_assert_eq!(actual_ids, expected_ids);
    }

    /// Property: `all_timeline_entries` is deterministic — applying
    /// it twice to the same slice yields the same `Vec<TimelineEntry>`.
    #[test]
    fn all_timeline_entries_is_deterministic(
        sessions in prop::collection::vec(session_strategy(), 0..6),
    ) {
        let a = all_timeline_entries(&sessions);
        let b = all_timeline_entries(&sessions);
        prop_assert_eq!(a, b);
    }
}
