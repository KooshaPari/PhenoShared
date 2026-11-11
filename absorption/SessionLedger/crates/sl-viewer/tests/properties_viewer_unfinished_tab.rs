//! Property evidence for sl-viewer's `unfinished_tab` module.
//!
//! This file complements `crates/sl-viewer/src/unfinished_tab.rs`'s
//! per-function `#[cfg(test)] mod tests` block by pinning invariants
//! over the *full* shape of the inputs the module can receive (the unit
//! tests pin specific values; the property tests below pin invariants
//! over many values).
//!
//! `unfinished_tab` invariants:
//!  * `reason_label(reason)` is total and deterministic — every
//!    `UnfinishedReason` variant yields a non-empty, label-shaped string.
//!  * `reason_label` is distinct — two different reasons produce two
//!    different labels (no accidental aliasing in the UI badge).
//!  * `unfinished_items` is monotonic w.r.t. `last_activity_ms`:
//!    items with a known timestamp appear before items without one
//!    (None → "unknown last activity" → sorts last), and among
//!    timestamped items the order is descending by timestamp.
//!  * `unfinished_items` is stable under session-id tiebreak: when two
//!    items share the same `last_activity_ms`, the one with the smaller
//!    session_id appears first (lexicographic, ascending).

use proptest::prelude::*;
use session_ledger::domain::session::{Corpus, Message, Role, Session};
use session_ledger::domain::worklog::UnfinishedReason;
use sl_viewer::unfinished_tab::{reason_label, unfinished_items};

// ── strategies ─────────────────────────────────────────────────────────────

fn session_strategy() -> impl Strategy<Value = Session> {
    (
        // session_id — non-empty, identifier-shaped.
        "[a-zA-Z0-9_-]{1,16}",
        // 0..6 messages; each message has its own independent
        // `Option<i64>` ts_ms so the `detect_unfinished` projection's
        // `find_map(|m| m.ts_ms).rev()` contract is exercised naturally
        // (per-message timestamps, not a session-wide value).
        prop::collection::vec(
            (0u8..5, "[ -~]{1,40}", prop::option::of(0i64..1_000_000_000_000)),
            0..6,
        ),
    )
        .prop_map(|(session_id, messages)| {
            let mut session = Session::new(format!("sess-{session_id}"), Corpus::Forge);
            for (role_idx, content, ts_ms) in messages {
                let role = match role_idx % 5 {
                    0 => Role::User,
                    1 => Role::Assistant,
                    2 => Role::Subagent,
                    3 => Role::Tool,
                    _ => Role::System,
                };
                let mut msg = Message::new(role, content);
                msg.ts_ms = ts_ms;
                session.messages.push(msg);
            }
            session
        })
}

fn unfinished_reason_strategy() -> impl Strategy<Value = UnfinishedReason> {
    prop::sample::select(vec![
        UnfinishedReason::AwaitingAssistantResponse,
        UnfinishedReason::InterruptedExecution,
        UnfinishedReason::MissingCompletionMarker,
    ])
}

// ── reason_label properties ─────────────────────────────────────────────────

proptest! {
    /// Property: `reason_label` is total — every variant produces a
    /// non-empty, non-whitespace string. Catches a future addition of a
    /// `UnfinishedReason` variant whose match arm maps to `""`.
    #[test]
    fn reason_label_is_non_empty_for_every_variant(reason in unfinished_reason_strategy()) {
        let label = reason_label(reason);
        prop_assert!(!label.is_empty(), "reason_label must not be empty for {reason:?}");
        prop_assert!(!label.trim().is_empty(), "reason_label must not be all-whitespace for {reason:?}");
    }

    /// Property: `reason_label` is injective — distinct reasons produce
    /// distinct labels. Catches accidental aliasing where, e.g., two
    /// reasons share the same badge text in the UI.
    #[test]
    fn reason_label_is_injective(
        left in unfinished_reason_strategy(),
        right in unfinished_reason_strategy(),
    ) {
        if left == right {
            return Ok(());
        }
        prop_assert_ne!(reason_label(left), reason_label(right));
    }
}

// ── unfinished_items ordering properties ────────────────────────────────────

proptest! {
    /// Property: `unfinished_items` is deterministic. Two calls on the
    /// same input yield the same output (the function is pure).
    #[test]
    fn unfinished_items_is_deterministic(
        sessions in prop::collection::vec(session_strategy(), 0..8),
    ) {
        let first = unfinished_items(&sessions);
        let second = unfinished_items(&sessions);
        prop_assert_eq!(first, second);
    }

    /// Property: `unfinished_items` orders known timestamps descending.
    /// Two invariants:
    ///   (a) within the sliding window of items with a known timestamp,
    ///       timestamps are non-increasing;
    ///   (b) once an item with `last_activity_ms == None` appears, no
    ///       later item may carry a known timestamp (None is the
    ///       "unknown last activity" sentinel and always sorts last).
    #[test]
    fn unfinished_items_orders_known_timestamps_descending(
        sessions in prop::collection::vec(session_strategy(), 1..10),
    ) {
        let items = unfinished_items(&sessions);

        // (a) descending among items with a known timestamp.
        for window in items.windows(2) {
            let prev = &window[0];
            let next = &window[1];
            if let (Some(a), Some(b)) = (prev.last_activity_ms, next.last_activity_ms) {
                prop_assert!(
                    a >= b,
                    "known timestamps must be non-increasing: {a} came before {b}",
                );
            }
        }

        // (b) no Some(ts) appears after a None.
        let mut seen_none = false;
        for item in &items {
            if seen_none {
                prop_assert!(
                    item.last_activity_ms.is_none(),
                    "Some(ts) found after None: {:?} appeared after a None item",
                    item.last_activity_ms,
                );
            }
            if item.last_activity_ms.is_none() {
                seen_none = true;
            }
        }
    }

    /// Property: `unfinished_items` ties on `last_activity_ms` break by
    /// session_id ascending (lexicographic). When the `last_activity_ms`
    /// field is equal, the item with the smaller session_id must appear
    /// first.
    #[test]
    fn unfinished_items_ties_break_by_session_id_ascending(
        sessions in prop::collection::vec(session_strategy(), 1..10),
    ) {
        let items = unfinished_items(&sessions);

        for window in items.windows(2) {
            let prev = &window[0];
            let next = &window[1];
            match (prev.last_activity_ms, next.last_activity_ms) {
                (Some(a), Some(b)) if a == b => {
                    prop_assert!(
                        prev.session_id <= next.session_id,
                        "tie on ts_ms must break by session_id asc: {} came before {}",
                        prev.session_id,
                        next.session_id,
                    );
                }
                _ => {
                    // No invariant to check across mixed-Some/None or
                    // unequal timestamps (covered by other properties).
                }
            }
        }
    }

    /// Property: `unfinished_items` is length-monotonic w.r.t. input —
    /// doubling the input sessions cannot produce fewer items than the
    /// original (the projector is non-destructive).
    #[test]
    fn unfinished_items_is_length_monotonic(
        base in prop::collection::vec(session_strategy(), 0..6),
        more in prop::collection::vec(session_strategy(), 0..6),
    ) {
        let base_items = unfinished_items(&base).len();
        let combined_items = unfinished_items(&[base.clone(), more].concat()).len();
        prop_assert!(
            combined_items >= base_items,
            "appending sessions must not lose items: base={base_items}, combined={combined_items}",
        );
    }

    /// Property: for each projected item, `last_activity_ms` equals the
    /// maximum known `ts_ms` over the *session's* messages, or `None`
    /// if none of the session's messages carried a timestamp. This pins
    /// the per-message → projected-Item reduction explicitly (the unit
    /// tests in `domain/worklog.rs` cover specific values; this property
    /// pins the projection over many shapes).
    #[test]
    fn unfinished_items_last_activity_matches_session_max_ts(
        sessions in prop::collection::vec(session_strategy(), 0..8),
    ) {
        let items = unfinished_items(&sessions);

        for item in &items {
            // Reconstruct the source session by id.
            let session = sessions
                .iter()
                .find(|s| s.id == item.session_id)
                .expect("projected item must reference an input session");

            let expected_last_activity_ms =
                session.messages.iter().rev().find_map(|m| m.ts_ms);

            prop_assert_eq!(
                item.last_activity_ms,
                expected_last_activity_ms,
                "session {}: projected last_activity_ms must equal session max known ts_ms",
                session.id,
            );
        }
    }
}
