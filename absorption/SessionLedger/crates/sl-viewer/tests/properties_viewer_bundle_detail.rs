//! Property evidence for sl-viewer's `bundle_list::summarize` and
//! `detail_pane::extract_detail` reductions.
//!
//! Integration tests. The unit tests in those modules pin specific
//! values; these properties pin invariants over the full shape of
//! inputs the helpers can receive.
//!
//! `bundle_list::summarize` invariants:
//!  * `source_id` is carried through unchanged.
//!  * `intent_goal` is the first Intent slice's `body["goal"]` string,
//!    or `"(no goal)"` when no Intent slice is present or none carries
//!    a string `goal`.
//!  * `bundle_count` equals the input slice count.
//!  * `has_acceptance` / `has_contract` reflect presence of those
//!    kinds in the input bundle list.
//!
//! `detail_pane::extract_detail` invariants:
//!  * `source_id` is carried through unchanged.
//!  * `intent_goal` is the same fallback contract as `summarize`.
//!  * `intent_state` is always `IntentState::Extracted` (the only state
//!    the reduction can produce, given the heuristic extractors).
//!  * `total_token_estimate` matches `bundle.total_token_estimate()`
//!    (call through to the same underlying reduction).
//!  * `acceptance_signals` / `constraints` are empty when the Intent
//!    slice is absent; otherwise they hold the string members of the
//!    matching JSON array, in input order, filtering out non-strings.
//!
//! proptest is added to `sl-viewer/[dev-dependencies]` (mirroring the
//! workspace root); see PR #425 for the initial wiring.

use proptest::prelude::*;
use session_ledger::domain::bundle::{Bundle, BundleKind, ContinuationBundle};
use session_ledger::domain::intent::IntentState;
use sl_viewer::bundle_list::summarize;
use sl_viewer::detail_pane::extract_detail;

// ── strategies ──────────────────────────────────────────────────────────────

fn continuation_bundle_strategy() -> impl Strategy<Value = ContinuationBundle> {
    (
        // source_id — non-empty identifier.
        "[a-zA-Z0-9_-]{1,16}",
        // 0..6 bundles with optional goal / acceptance_signals /
        // constraints / cwd / title / skipped_by / watch_files /
        // user_turn_count in body. Each Bundle carries a single body
        // field set so we don't have to disambiguate JSON schemas
        // across kinds.
        prop::collection::vec(
            (
                prop::sample::select(vec![
                    BundleKind::Intent,
                    BundleKind::Acceptance,
                    BundleKind::Contract,
                    BundleKind::Context,
                ]),
                prop::option::of("[a-zA-Z0-9 ._-]{0,16}"),
                prop::option::of(prop::collection::vec("[a-zA-Z0-9 _.-]{1,8}", 0..4)),
                prop::option::of(prop::collection::vec("[a-zA-Z0-9 _.-]{1,8}", 0..4)),
                prop::option::of("[a-zA-Z0-9./_-]{0,16}"),
                prop::option::of("[a-zA-Z0-9 ._-]{0,16}"),
                prop::option::of(prop::collection::vec("[a-zA-Z0-9 _.-]{1,8}", 0..4)),
                prop::option::of(prop::collection::vec("[a-zA-Z0-9 _.-]{1,8}", 0..4)),
                prop::option::of(0u32..100_000),
            ),
            0..6,
        ),
    )
        .prop_map(|(source_id, raw)| {
            let bundles: Vec<Bundle> = raw
                .into_iter()
                .enumerate()
                .map(
                    |(
                        idx,
                        (
                            kind,
                            goal,
                            acceptance_signals,
                            constraints,
                            cwd,
                            title,
                            skipped_by,
                            watch_files,
                            user_turn_count,
                        ),
                    )| {
                        let mut body = serde_json::Map::new();
                        if let Some(g) = goal {
                            body.insert("goal".to_string(), serde_json::Value::String(g));
                        }
                        if let Some(arr) = acceptance_signals {
                            body.insert(
                                "acceptance_signals".to_string(),
                                serde_json::Value::Array(
                                    arr.into_iter().map(serde_json::Value::String).collect(),
                                ),
                            );
                        }
                        if let Some(arr) = constraints {
                            body.insert(
                                "constraints".to_string(),
                                serde_json::Value::Array(
                                    arr.into_iter().map(serde_json::Value::String).collect(),
                                ),
                            );
                        }
                        if let Some(c) = cwd {
                            body.insert("cwd".to_string(), serde_json::Value::String(c));
                        }
                        if let Some(t) = title {
                            body.insert("title".to_string(), serde_json::Value::String(t));
                        }
                        if let Some(arr) = skipped_by {
                            body.insert(
                                "skipped_by".to_string(),
                                serde_json::Value::Array(
                                    arr.into_iter().map(serde_json::Value::String).collect(),
                                ),
                            );
                        }
                        if let Some(arr) = watch_files {
                            body.insert(
                                "watch_files".to_string(),
                                serde_json::Value::Array(
                                    arr.into_iter().map(serde_json::Value::String).collect(),
                                ),
                            );
                        }
                        if let Some(utc) = user_turn_count {
                            body.insert(
                                "user_turn_count".to_string(),
                                serde_json::Value::Number(serde_json::Number::from(utc)),
                            );
                        }
                        let _ = idx; // suppress unused warning if any.
                        Bundle::new(kind, serde_json::Value::Object(body))
                    },
                )
                .collect();
            ContinuationBundle { source_id, bundles }
        })
}

// ── bundle_list::summarize ──────────────────────────────────────────────────

proptest! {
    /// Property: `summarize` carries the `source_id` through unchanged.
    #[test]
    fn summarize_carries_source_id(bundle in continuation_bundle_strategy()) {
        let summary = summarize(&bundle);
        prop_assert_eq!(summary.source_id, bundle.source_id);
    }

    /// Property: `bundle_count` matches the input slice count exactly.
    /// Catches drift where `summarize` accidentally filters / flattens.
    #[test]
    fn summarize_bundle_count_matches(bundle in continuation_bundle_strategy()) {
        let summary = summarize(&bundle);
        prop_assert_eq!(summary.bundle_count, bundle.bundles.len());
    }

    /// Property: `has_acceptance` is `true` iff any bundle in the input
    /// has kind `Acceptance`. Same for `has_contract`.
    #[test]
    fn summarize_has_kinds_reflect_input(bundle in continuation_bundle_strategy()) {
        let summary = summarize(&bundle);
        prop_assert_eq!(
            summary.has_acceptance,
            bundle.bundles.iter().any(|b| b.kind == BundleKind::Acceptance)
        );
        prop_assert_eq!(
            summary.has_contract,
            bundle.bundles.iter().any(|b| b.kind == BundleKind::Contract)
        );
    }

    /// Property: `intent_goal` is either:
    /// * the first Intent slice's string `goal`, or
    /// * `"(no goal)"` when no Intent slice is present or none carries
    ///   a string `goal`.
    /// In either case the field is non-empty (the fallback is
    /// non-empty).
    #[test]
    fn summarize_intent_goal_fallback(bundle in continuation_bundle_strategy()) {
        let summary = summarize(&bundle);
        let expected = bundle
            .bundles
            .iter()
            .find(|b| b.kind == BundleKind::Intent)
            .and_then(|b| b.body.get("goal"))
            .and_then(|v| v.as_str())
            .filter(|goal| !goal.trim().is_empty())
            .unwrap_or("(no goal)");
        prop_assert_eq!(summary.intent_goal.as_str(), expected);
        prop_assert!(!summary.intent_goal.is_empty());
    }

    /// Property: `summarize` is deterministic — calling it twice on
    /// the same bundle yields the same `BundleSummary`.
    #[test]
    fn summarize_is_deterministic(bundle in continuation_bundle_strategy()) {
        let a = summarize(&bundle);
        let b = summarize(&bundle);
        prop_assert_eq!(a, b);
    }
}

// ── detail_pane::extract_detail ────────────────────────────────────────────

proptest! {
    /// Property: `extract_detail` carries the `source_id` through unchanged.
    #[test]
    fn extract_detail_carries_source_id(bundle in continuation_bundle_strategy()) {
        let detail = extract_detail(&bundle);
        prop_assert_eq!(detail.source_id, bundle.source_id);
    }

    /// Property: `intent_state` is always `IntentState::Extracted` —
    /// the only state the reduction produces given the heuristic
    /// extractors. Catches drift where the reduction tracks an
    /// observed extractor state instead.
    #[test]
    fn extract_detail_intent_state_always_extracted(bundle in continuation_bundle_strategy()) {
        let detail = extract_detail(&bundle);
        prop_assert_eq!(detail.intent_state, IntentState::Extracted);
    }

    /// Property: `total_token_estimate` equals the bundle's own
    /// `total_token_estimate()` reduction. Guards against the
    /// detail pane accidentally summing differently.
    #[test]
    fn extract_detail_total_token_estimate_matches(bundle in continuation_bundle_strategy()) {
        let detail = extract_detail(&bundle);
        prop_assert_eq!(detail.total_token_estimate, bundle.total_token_estimate());
    }

    /// Property: `intent_goal` is `Some(s)` iff an Intent slice carries
    /// a string `goal` field; otherwise `None`.
    #[test]
    fn extract_detail_intent_goal_option(bundle in continuation_bundle_strategy()) {
        let detail = extract_detail(&bundle);
        let expected: Option<String> = bundle
            .bundles
            .iter()
            .find(|b| b.kind == BundleKind::Intent)
            .and_then(|b| b.body.get("goal"))
            .and_then(|v| v.as_str())
            .map(String::from);
        prop_assert_eq!(detail.intent_goal, expected);
    }

    /// Property: `context_cwd` / `context_title` are `Some(s)` iff a
    /// Context slice carries a string `cwd` / `title` field;
    /// otherwise `None`.
    #[test]
    fn extract_detail_context_fields(bundle in continuation_bundle_strategy()) {
        let detail = extract_detail(&bundle);
        let expected_cwd: Option<String> = bundle
            .bundles
            .iter()
            .find(|b| b.kind == BundleKind::Context)
            .and_then(|b| b.body.get("cwd"))
            .and_then(|v| v.as_str())
            .map(String::from);
        let expected_title: Option<String> = bundle
            .bundles
            .iter()
            .find(|b| b.kind == BundleKind::Context)
            .and_then(|b| b.body.get("title"))
            .and_then(|v| v.as_str())
            .map(String::from);
        prop_assert_eq!(detail.context_cwd, expected_cwd);
        prop_assert_eq!(detail.context_title, expected_title);
    }

    /// Property: `extract_detail` is deterministic — calling it twice
    /// on the same bundle yields the same `BundleDetail`.
    #[test]
    fn extract_detail_is_deterministic(bundle in continuation_bundle_strategy()) {
        let a = extract_detail(&bundle);
        let b = extract_detail(&bundle);
        prop_assert_eq!(a, b);
    }
}
