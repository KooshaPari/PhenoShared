//! Property evidence for sl-viewer's `timeline` module.
//!
//! Complements `crates/sl-viewer/src/timeline.rs`'s per-function
//! `#[cfg(test)] mod tests` block by pinning invariants over the *full*
//! shape of the inputs the pure helpers can receive.
//!
//! `timeline` invariants:
//!  * `group_by_day` partitions every entry into exactly one group
//!    (no losses, no duplicates) and orders groups chronologically.
//!    Empty `day` lands in `"(unknown date)"`.
//!  * `normalize_widths` produces one width per input entry, all in
//!    `[MIN_PX, MAX_PX]`. Empty / all-zero inputs collapse to all
//!    `MIN_PX`; the max-tokened entry always renders at `MAX_PX`.
//!  * `model_hue` is deterministic and lands in `[0, 359]`.
//!  * `model_color` is deterministic and matches `hsl(<hue>, 60%, 55%)`.
//!  * `TimelineEntry::from_bundle` reduces a `ContinuationBundle`
//!    correctly: `day` is the leading 10 chars of `created_at`
//!    (else empty), `goal` falls back to `"(no goal)"`, `model` to
//!    `"unknown"`, `token_count` / `message_count` / `has_*` match the
//!    same reduction `OkfBundle::from_bundle` performs.

use proptest::prelude::*;
use session_ledger::domain::bundle::{Bundle, BundleKind, ContinuationBundle};
use sl_viewer::timeline::{
    group_by_day, model_color, model_hue, normalize_widths, TimelineEntry, MAX_PX, MIN_PX,
};

// ── strategies ─────────────────────────────────────────────────────────────

fn entry_strategy() -> impl Strategy<Value = TimelineEntry> {
    (
        // source_id — non-empty identifier.
        "[a-zA-Z0-9_-]{1,16}",
        // day — empty or "YYYY-MM-DD"-shaped (or arbitrary to exercise the
        // "unknown date" branch via the empty case).
        prop::option::of("[0-9]{4}-[0-9]{2}-[0-9]{2}"),
        // created_at — full ISO-8601 with optional suffix.
        prop::option::of("[0-9TZ:.+-]{1,24}"),
        // token_count — bounded.
        0u64..100_000,
        // model — bounded.
        "[a-zA-Z0-9._-]{0,16}",
        // goal — bounded.
        "[a-zA-Z0-9 ._-]{0,32}",
        // message_count.
        0usize..16,
        // has_acceptance / has_contract.
        any::<bool>(),
        any::<bool>(),
    )
        .prop_map(
            |(
                source_id,
                day,
                created_at,
                token_count,
                model,
                goal,
                message_count,
                has_acceptance,
                has_contract,
            )| {
                TimelineEntry {
                    source_id,
                    day: day.unwrap_or_default(),
                    created_at: created_at.unwrap_or_default(),
                    token_count,
                    model,
                    goal,
                    message_count,
                    has_acceptance,
                    has_contract,
                }
            },
        )
}

fn continuation_bundle_strategy() -> impl Strategy<Value = ContinuationBundle> {
    (
        // source_id.
        "[a-zA-Z0-9_-]{1,16}",
        // 0..6 bundles with optional token / goal / created_at / model in body.
        prop::collection::vec(
            (
                prop::sample::select(vec![
                    BundleKind::Intent,
                    BundleKind::Acceptance,
                    BundleKind::Contract,
                    BundleKind::Context,
                ]),
                prop::option::of(0u64..100_000),
                prop::option::of("[a-zA-Z0-9 ._-]{1,16}"),
                prop::option::of("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9TZ:.+-]{1,14}"),
                prop::option::of("[a-zA-Z0-9._-]{1,16}"),
            ),
            0..6,
        ),
    )
        .prop_map(|(source_id, raw)| {
            let bundles: Vec<Bundle> = raw
                .into_iter()
                .map(|(kind, tokens, goal, created_at, model)| {
                    let mut body = serde_json::Map::new();
                    if let Some(t) = tokens {
                        body.insert("user_turn_count".into(), serde_json::json!(t));
                    }
                    if let Some(g) = goal {
                        body.insert("goal".into(), serde_json::json!(g));
                    }
                    if let Some(c) = created_at {
                        body.insert("created_at".into(), serde_json::json!(c));
                    }
                    if let Some(m) = model {
                        body.insert("model".into(), serde_json::json!(m));
                    }
                    Bundle::new(kind, serde_json::Value::Object(body))
                })
                .collect();
            ContinuationBundle { source_id, bundles }
        })
}

// ── group_by_day properties ────────────────────────────────────────────────

proptest! {
    /// Property: `group_by_day` is a partition — every input entry lands
    /// in exactly one group, no losses, no duplicates.
    #[test]
    fn group_by_day_partitions_entries(
        entries in prop::collection::vec(entry_strategy(), 0..12),
    ) {
        let groups = group_by_day(&entries);
        let flat: Vec<TimelineEntry> =
            groups.iter().flat_map(|(_, v)| v.iter()).cloned().collect();
        prop_assert_eq!(
            flat.len(),
            entries.len(),
            "every input entry must appear in exactly one group",
        );
    }

    /// Property: `group_by_day` orders groups chronologically (the empty
    /// `day` group lands first because `""` sorts before any "YYYY-..."
    /// string in lexicographic order). The first group is the empty-day
    /// group only when at least one entry has an empty day.
    #[test]
    fn group_by_day_groups_ordered_by_day(
        entries in prop::collection::vec(entry_strategy(), 0..12),
    ) {
        let groups = group_by_day(&entries);
        let days: Vec<&str> = groups.iter().map(|(d, _)| d.as_str()).collect();
        let mut sorted_days = days.clone();
        sorted_days.sort();
        prop_assert_eq!(&days[..], &sorted_days[..], "groups must be sorted by day ascending");
    }

    /// Property: `group_by_day` collapses every group of empty-day entries
    /// under the literal label `"(unknown date)"`.
    #[test]
    fn group_by_day_empty_day_label_is_unknown(
        empty_count in 1usize..5,
        known_count in 0usize..5,
    ) {
        let mut entries: Vec<TimelineEntry> = (0..empty_count)
            .map(|i| TimelineEntry {
                source_id: format!("empty-{i}"),
                day: String::new(),
                created_at: String::new(),
                token_count: 0,
                model: "test".into(),
                goal: "test".into(),
                message_count: 1,
                has_acceptance: false,
                has_contract: false,
            })
            .collect();
        for i in 0..known_count {
            entries.push(TimelineEntry {
                source_id: format!("known-{i}"),
                day: "2026-01-01".into(),
                created_at: "2026-01-01T00:00:00Z".into(),
                token_count: 0,
                model: "test".into(),
                goal: "test".into(),
                message_count: 1,
                has_acceptance: false,
                has_contract: false,
            });
        }
        let groups = group_by_day(&entries);
        let unknown = groups.iter().find(|(d, _)| d == "(unknown date)").expect("unknown group exists");
        prop_assert_eq!(unknown.1.len(), empty_count, "all empty-day entries must land in the unknown group");
    }
}

// ── normalize_widths properties ─────────────────────────────────────────────

proptest! {
    /// Property: `normalize_widths` produces one width per input entry.
    #[test]
    fn normalize_widths_length_matches_input(
        entries in prop::collection::vec(entry_strategy(), 0..10),
    ) {
        let widths = normalize_widths(&entries);
        prop_assert_eq!(widths.len(), entries.len());
    }

    /// Property: every normalised width falls in `[MIN_PX, MAX_PX]`.
    #[test]
    fn normalize_widths_in_range(
        entries in prop::collection::vec(entry_strategy(), 0..10),
    ) {
        let widths = normalize_widths(&entries);
        for w in &widths {
            prop_assert!(*w >= MIN_PX, "width {} must be >= MIN_PX ({})", w, MIN_PX);
            prop_assert!(*w <= MAX_PX, "width {} must be <= MAX_PX ({})", w, MAX_PX);
        }
    }

    /// Property: empty input → empty output (every caller would have to
    /// draw nothing). An all-zero slice must collapse to all MIN_PX.
    #[test]
    fn normalize_widths_all_zero_returns_min(len in 1usize..8) {
        let entries: Vec<TimelineEntry> = (0..len)
            .map(|i| TimelineEntry {
                source_id: format!("e-{i}"),
                day: "2026-01-01".into(),
                created_at: "2026-01-01T00:00:00Z".into(),
                token_count: 0,
                model: "test".into(),
                goal: "test".into(),
                message_count: 1,
                has_acceptance: false,
                has_contract: false,
            })
            .collect();
        let widths = normalize_widths(&entries);
        for w in &widths {
            prop_assert_eq!(*w, MIN_PX, "all-zero slice must collapse to MIN_PX");
        }
    }

    /// Property: the entry with the max `token_count` always renders at
    /// `MAX_PX` (the bar scale is anchored at the maximum).
    #[test]
    fn normalize_widths_max_token_renders_max_px(
        // First entry has an arbitrary count. Rest may be heavier.
        heavy_tokens in 1u64..1_000_000,
        light_tokens in 0u64..1000,
        rest in 0usize..6,
    ) {
        let mut entries: Vec<TimelineEntry> = Vec::with_capacity(1 + rest);
        entries.push(TimelineEntry {
            source_id: "heavy".into(),
            day: "2026-01-01".into(),
            created_at: "2026-01-01T00:00:00Z".into(),
            token_count: heavy_tokens,
            model: "test".into(),
            goal: "test".into(),
            message_count: 1,
            has_acceptance: false,
            has_contract: false,
        });
        for i in 0..rest {
            entries.push(TimelineEntry {
                source_id: format!("light-{i}"),
                day: "2026-01-01".into(),
                created_at: "2026-01-01T00:00:00Z".into(),
                token_count: light_tokens,
                model: "test".into(),
                goal: "test".into(),
                message_count: 1,
                has_acceptance: false,
                has_contract: false,
            });
        }
        let widths = normalize_widths(&entries);
        prop_assert_eq!(entries.len(), widths.len());
        let max_tokens = entries.iter().map(|entry| entry.token_count).max().unwrap_or_default();
        for (entry, width) in entries.iter().zip(widths) {
            if entry.token_count == max_tokens {
                prop_assert_eq!(width, MAX_PX, "a maximum entry must render at MAX_PX");
            }
        }
    }
}

// ── model hue / color properties ───────────────────────────────────────────

proptest! {
    /// Property: `model_hue` is deterministic — same input, same output.
    #[test]
    fn model_hue_is_deterministic(model in "[a-zA-Z0-9._-]{0,32}") {
        prop_assert_eq!(model_hue(&model), model_hue(&model));
    }

    /// Property: `model_hue` lands in `[0, 359]` for any input.
    #[test]
    fn model_hue_in_range(model in "[a-zA-Z0-9._-]{0,32}") {
        let h = model_hue(&model);
        prop_assert!(h <= 359, "hue {} must be <= 359", h);
    }

    /// Property: `model_color` returns `hsl(<hue>, 60%, 55%)` and is
    /// deterministic.
    #[test]
    fn model_color_format_and_deterministic(model in "[a-zA-Z0-9._-]{0,32}") {
        let a = model_color(&model);
        let b = model_color(&model);
        prop_assert_eq!(&a, &b);
        let expected = format!("hsl({}, 60%, 55%)", model_hue(&model));
        prop_assert_eq!(a, expected);
    }
}

// ── TimelineEntry::from_bundle properties ───────────────────────────────────

proptest! {
    /// Property: `day` is the leading 10 chars of `created_at` when
    /// `created_at.len() >= 10`, else empty.
    #[test]
    fn from_bundle_day_is_leading_10_chars_or_empty(
        prefix in "[0-9TZ:.+-]{10,24}",
        suffix in "[0-9TZ:.+-]{0,10}",
    ) {
        let created_at = format!("{prefix}{suffix}");
        let cb = ContinuationBundle {
            source_id: "test".into(),
            bundles: vec![Bundle::new(
                BundleKind::Context,
                serde_json::json!({"created_at": created_at.clone()}),
            )],
        };
        let entry = TimelineEntry::from_bundle(&cb);
        let expected = if created_at.len() >= 10 { created_at[..10].to_owned() } else { String::new() };
        prop_assert_eq!(entry.day, expected);
    }

    /// Property: `goal` falls back to `"(no goal)"` when no Intent bundle
    /// carries a string `goal` body.
    #[test]
    fn from_bundle_goal_fallback(variant in 0u8..3) {
        let bundles: Vec<Bundle> = match variant {
            0 => Vec::new(),
            1 => vec![Bundle::new(BundleKind::Intent, serde_json::json!({"user_turn_count": 7}))],
            _ => vec![Bundle::new(
                BundleKind::Intent,
                serde_json::json!({"goal": 42}),
            )],
        };
        let cb = ContinuationBundle {
            source_id: "test".into(),
            bundles,
        };
        let entry = TimelineEntry::from_bundle(&cb);
        prop_assert_eq!(entry.goal, "(no goal)");
    }

    /// Property: `model` falls back to `"unknown"` when no Context bundle
    /// carries a string `model` body.
    #[test]
    fn from_bundle_model_fallback(variant in 0u8..3) {
        let bundles: Vec<Bundle> = match variant {
            0 => Vec::new(),
            1 => vec![Bundle::new(BundleKind::Context, serde_json::json!({"created_at": "2026-01-01"}))],
            _ => vec![Bundle::new(
                BundleKind::Context,
                serde_json::json!({"model": 42}),
            )],
        };
        let cb = ContinuationBundle {
            source_id: "test".into(),
            bundles,
        };
        let entry = TimelineEntry::from_bundle(&cb);
        prop_assert_eq!(entry.model, "unknown");
    }

    /// Property: `source_id` carries through from the continuation.
    #[test]
    fn from_bundle_source_id_carries_through(source_id in "[a-zA-Z0-9_-]{1,32}") {
        let cb = ContinuationBundle {
            source_id: source_id.clone(),
            bundles: Vec::new(),
        };
        let entry = TimelineEntry::from_bundle(&cb);
        prop_assert_eq!(entry.source_id, source_id);
    }

    /// Property: `has_acceptance` / `has_contract` reflect kind presence
    /// (any-of) and `message_count` equals the slice count.
    #[test]
    fn from_bundle_aggregation_matches_kinds(
        kinds in prop::collection::vec(
            prop::sample::select(vec![BundleKind::Intent, BundleKind::Acceptance, BundleKind::Contract, BundleKind::Context]),
            0..6,
        ),
    ) {
        let bundles: Vec<Bundle> = kinds
            .iter()
            .map(|k| Bundle::new(*k, serde_json::json!({})))
            .collect();
        let cb = ContinuationBundle {
            source_id: "test".into(),
            bundles: bundles.clone(),
        };
        let entry = TimelineEntry::from_bundle(&cb);
        prop_assert_eq!(entry.message_count, bundles.len());
        prop_assert_eq!(entry.has_acceptance, kinds.contains(&BundleKind::Acceptance));
        prop_assert_eq!(entry.has_contract, kinds.contains(&BundleKind::Contract));
    }

    /// Property: `token_count` falls back to 0 when no Intent bundle
    /// carries a numeric `user_turn_count`.
    #[test]
    fn from_bundle_token_count_zero_when_missing(cb in continuation_bundle_strategy()) {
        let entry = TimelineEntry::from_bundle(&cb);
        let intent_has_numeric = cb.bundles.iter().any(|b| {
            b.kind == BundleKind::Intent
                && b.body.get("user_turn_count").and_then(|v| v.as_u64()).is_some()
        });
        let expected = if intent_has_numeric {
            cb.bundles
                .iter()
                .find(|b| b.kind == BundleKind::Intent)
                .and_then(|b| b.body.get("user_turn_count"))
                .and_then(|v| v.as_u64())
                .unwrap_or(0)
        } else {
            0
        };
        prop_assert_eq!(entry.token_count, expected);
    }
}
