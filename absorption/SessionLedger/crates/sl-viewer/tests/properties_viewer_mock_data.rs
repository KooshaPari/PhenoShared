//! Property evidence for sl-viewer's `mock_data::sample_bundles` and
//! `mock_data::sample_sessions` deterministic fixtures.
//!
//! These are the demo / dev-only fixtures that the viewer renders when
//! no real corpus is available. They drive the launch screenshots, the
//! preview panes, and the bundled web demo. If the shape of these
//! fixtures drifts, the screenshots and fixtures break silently — so
//! every visible property is pinned here.
//!
//! `mock_data::sample_bundles` invariants:
//!  * Output is non-empty.
//!  * Every `source_id` is unique across the sample.
//!  * Every `source_id` is non-empty.
//!  * Every `ContinuationBundle` contains at least one `Bundle` slice.
//!  * Every `ContinuationBundle` contains at least one `Intent` bundle.
//!  * Every `Intent` bundle carries a non-empty `goal` string field.
//!  * Every `Acceptance` bundle carries `ready: true`.
//!  * Output length matches the documented demo count (3).
//!  * Output is deterministic across calls.
//!
//! `mock_data::sample_sessions` invariants:
//!  * Output is non-empty.
//!  * Every session id is unique across the sample.
//!  * Every session id is non-empty.
//!  * Every session has at least one message.
//!  * Every session message has a non-empty `content`.
//!  * Every session has a non-empty `cwd` and `title`.
//!  * Every session contains at least one `User` and one `Assistant`
//!    message so the timeline / history UI can render both sides.
//!  * Output length matches the documented demo count (3).
//!  * Output is deterministic across calls.

use proptest::prelude::*;
use session_ledger::domain::bundle::BundleKind;
use session_ledger::domain::session::Role;
use sl_viewer::mock_data::{sample_bundles, sample_sessions};

// ── sample_bundles properties ───────────────────────────────────────────────

proptest! {
    /// `sample_bundles()` is non-empty (the demo must render at least one
    /// row to validate the UI against).
    #[test]
    fn sample_bundles_nonempty(_seed in any::<u32>()) {
        prop_assert!(!sample_bundles().is_empty());
    }

    /// `sample_bundles()` always returns the documented 3-entry sample.
    /// Guards against accidental truncation / extension of the demo.
    #[test]
    fn sample_bundles_length_matches_documented(_seed in any::<u32>()) {
        prop_assert_eq!(sample_bundles().len(), 3);
    }

    /// Every `source_id` is non-empty.
    #[test]
    fn sample_bundles_source_id_nonempty(_seed in any::<u32>()) {
        for cb in &sample_bundles() {
            prop_assert!(!cb.source_id.is_empty());
        }
    }

    /// Every `source_id` is unique across the sample.
    #[test]
    fn sample_bundles_source_id_unique(_seed in any::<u32>()) {
        let bundles = sample_bundles();
        let ids: Vec<&str> = bundles.iter().map(|cb| cb.source_id.as_str()).collect();
        let mut deduped = ids.clone();
        deduped.sort();
        deduped.dedup();
        prop_assert_eq!(deduped.len(), ids.len());
    }

    /// Every `ContinuationBundle` carries at least one bundle slice.
    #[test]
    fn sample_bundles_each_has_at_least_one_bundle(_seed in any::<u32>()) {
        for cb in &sample_bundles() {
            prop_assert!(!cb.bundles.is_empty());
        }
    }

    /// Every `ContinuationBundle` carries at least one `Intent` bundle
    /// so the UI can render an `intent_goal` summary.
    #[test]
    fn sample_bundles_each_has_intent_bundle(_seed in any::<u32>()) {
        for cb in &sample_bundles() {
            let n_intent = cb
                .bundles
                .iter()
                .filter(|b| b.kind == BundleKind::Intent)
                .count();
            prop_assert!(n_intent >= 1, "source_id {:?} has no Intent bundle", cb.source_id);
        }
    }

    /// Every `Intent` bundle carries a non-empty `goal` string field so
    /// the `bundle_list::summarize` summary does not fall back to
    /// `"(no goal)"`.
    #[test]
    fn sample_bundles_intent_has_goal(_seed in any::<u32>()) {
        for cb in &sample_bundles() {
            for b in cb.bundles.iter().filter(|b| b.kind == BundleKind::Intent) {
                let goal = b.body.get("goal").and_then(|v| v.as_str());
                prop_assert!(goal.is_some(), "Intent bundle missing `goal` field");
                prop_assert!(!goal.unwrap().is_empty(), "Intent `goal` is empty");
            }
        }
    }

    /// Every `Acceptance` bundle carries `ready: true` so the demo
    /// renders as ship-ready.
    #[test]
    fn sample_bundles_acceptance_ready(_seed in any::<u32>()) {
        for cb in &sample_bundles() {
            for b in cb.bundles.iter().filter(|b| b.kind == BundleKind::Acceptance) {
                let ready = b.body.get("ready").and_then(|v| v.as_bool());
                prop_assert_eq!(ready, Some(true));
            }
        }
    }

    /// `sample_bundles()` is deterministic across calls.
    #[test]
    fn sample_bundles_deterministic(_seed in any::<u32>()) {
        let a = sample_bundles();
        let b = sample_bundles();
        prop_assert_eq!(a.len(), b.len());
        for (x, y) in a.iter().zip(b.iter()) {
            prop_assert_eq!(&x.source_id, &y.source_id);
            prop_assert_eq!(x.bundles.len(), y.bundles.len());
            for (bx, by) in x.bundles.iter().zip(y.bundles.iter()) {
                prop_assert_eq!(bx.kind, by.kind);
                prop_assert_eq!(&bx.body, &by.body);
            }
        }
    }
}

// ── sample_sessions properties ──────────────────────────────────────────────

proptest! {
    /// `sample_sessions()` is non-empty.
    #[test]
    fn sample_sessions_nonempty(_seed in any::<u32>()) {
        prop_assert!(!sample_sessions().is_empty());
    }

    /// `sample_sessions()` always returns the documented 3-entry sample.
    #[test]
    fn sample_sessions_length_matches_documented(_seed in any::<u32>()) {
        prop_assert_eq!(sample_sessions().len(), 3);
    }

    /// Every session id is non-empty.
    #[test]
    fn sample_sessions_id_nonempty(_seed in any::<u32>()) {
        for s in &sample_sessions() {
            prop_assert!(!s.id.is_empty());
        }
    }

    /// Every session id is unique across the sample.
    #[test]
    fn sample_sessions_id_unique(_seed in any::<u32>()) {
        let sessions = sample_sessions();
        let ids: Vec<&str> = sessions.iter().map(|s| s.id.as_str()).collect();
        let mut deduped = ids.clone();
        deduped.sort();
        deduped.dedup();
        prop_assert_eq!(deduped.len(), ids.len());
    }

    /// Every session has at least one message so the timeline renders.
    #[test]
    fn sample_sessions_has_messages(_seed in any::<u32>()) {
        for s in &sample_sessions() {
            prop_assert!(!s.messages.is_empty(), "session {:?} has no messages", s.id);
        }
    }

    /// Every session message has a non-empty `content`.
    #[test]
    fn sample_sessions_messages_have_content(_seed in any::<u32>()) {
        for s in &sample_sessions() {
            for m in &s.messages {
                prop_assert!(!m.content.is_empty(), "session {:?} has empty message", s.id);
            }
        }
    }

    /// Every session has a non-empty `cwd` and `title`.
    #[test]
    fn sample_sessions_has_cwd_and_title(_seed in any::<u32>()) {
        for s in &sample_sessions() {
            let cwd = s.cwd.as_deref();
            let title = s.title.as_deref();
            prop_assert!(cwd.is_some(), "session {:?} has no cwd", s.id);
            prop_assert!(!cwd.unwrap().is_empty(), "session {:?} has empty cwd", s.id);
            prop_assert!(title.is_some(), "session {:?} has no title", s.id);
            prop_assert!(!title.unwrap().is_empty(), "session {:?} has empty title", s.id);
        }
    }

    /// Every session contains at least one `User` and one `Assistant`
    /// message so the timeline UI can render a conversational pair.
    #[test]
    fn sample_sessions_has_user_and_assistant(_seed in any::<u32>()) {
        for s in &sample_sessions() {
            let has_user = s.messages.iter().any(|m| m.role == Role::User);
            let has_assistant = s.messages.iter().any(|m| m.role == Role::Assistant);
            prop_assert!(has_user, "session {:?} has no User message", s.id);
            prop_assert!(has_assistant, "session {:?} has no Assistant message", s.id);
        }
    }

    /// `sample_sessions()` is deterministic across calls.
    #[test]
    fn sample_sessions_deterministic(_seed in any::<u32>()) {
        let a = sample_sessions();
        let b = sample_sessions();
        prop_assert_eq!(a.len(), b.len());
        for (x, y) in a.iter().zip(b.iter()) {
            prop_assert_eq!(&x.id, &y.id);
            prop_assert_eq!(&x.cwd, &y.cwd);
            prop_assert_eq!(&x.title, &y.title);
            prop_assert_eq!(x.messages.len(), y.messages.len());
            for (mx, my) in x.messages.iter().zip(y.messages.iter()) {
                prop_assert_eq!(mx.role, my.role);
                prop_assert_eq!(&mx.content, &my.content);
            }
        }
    }
}
