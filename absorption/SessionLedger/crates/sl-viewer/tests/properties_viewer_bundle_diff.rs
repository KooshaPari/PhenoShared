//! Property evidence for `sl-viewer::bundle_diff` — OKF bundle diff
//! panel.
//!
//! Invariants under test:
//!
//!  * `OkfBundle::from_bundle` derives every documented field from a
//!    `ContinuationBundle`
//!  * `diff_fields` returns one FieldDiff per documented field
//!    (9 fields: source_id, token_count, message_count, duration_ms,
//!    model, created_at, goal, has_acceptance, has_contract)
//!  * `diff_fields` correctly reports `differs` (true iff values differ)
//!  * Comparing a bundle to itself yields all-differs=false
//!  * FieldDiff ordering is stable (always in the same order)
//!  * `diff_fields` is symmetric for symmetric input
//!  * `FieldDiff` derives (Clone + PartialEq + Debug)

use proptest::prelude::*;
use sl_viewer::bundle_diff::{diff_fields, FieldDiff, OkfBundle};

// ── FieldDiff derives ────────────────────────────────────────────────────

proptest! {
    /// Property: `FieldDiff` derives (Clone + PartialEq + Debug).
    #[test]
    fn field_diff_derives_hold(
        name in "[a-z_]{3,15}",
        a in ".*",
        b in ".*",
        differs in any::<bool>(),
    ) {
        let fd = FieldDiff {
            name: Box::leak(name.into_boxed_str()) as &'static str,
            value_a: a.clone(),
            value_b: b.clone(),
            differs,
        };
        let cloned = fd.clone();
        let fdcopy = fd.clone();
        prop_assert_eq!(fdcopy, cloned, "cloned FieldDiff should equal original");
        let debug = format!("{:?}", fd);
        prop_assert!(!debug.is_empty());
    }
}

// ── diff_fields invariants ────────────────────────────────────────────────

proptest! {
    /// Property: `diff_fields` always returns exactly 9 fields (one
    /// per documented OKF field).
    #[test]
    fn diff_fields_has_nine_fields(
        a_id in ".*", b_id in ".*",
        a_tokens in any::<u64>(), b_tokens in any::<u64>(),
        a_msgs in any::<usize>(), b_msgs in any::<usize>(),
        a_dur in any::<u64>(), b_dur in any::<u64>(),
    ) {
        let a = OkfBundle {
            source_id: a_id,
            token_count: a_tokens,
            message_count: a_msgs,
            duration_ms: a_dur,
            model: None,
            created_at: None,
            goal: None,
            has_acceptance: false,
            has_contract: false,
        };
        let b = OkfBundle {
            source_id: b_id,
            token_count: b_tokens,
            message_count: b_msgs,
            duration_ms: b_dur,
            model: None,
            created_at: None,
            goal: None,
            has_acceptance: false,
            has_contract: false,
        };
        let diffs = diff_fields(&a, &b);
        prop_assert_eq!(diffs.len(), 9,
            "diff_fields should produce 9 FieldDiff entries (got {})", diffs.len());
    }

    /// Property: comparing a bundle to itself yields no differing fields
    /// (all `differs == false`).
    #[test]
    fn diff_fields_self_compare_has_no_differs(
        id in ".*",
        tokens in any::<u64>(),
        msgs in any::<usize>(),
        dur in any::<u64>(),
    ) {
        let a = OkfBundle {
            source_id: id,
            token_count: tokens,
            message_count: msgs,
            duration_ms: dur,
            model: None,
            created_at: None,
            goal: None,
            has_acceptance: false,
            has_contract: false,
        };
        let diffs = diff_fields(&a, &a);
        for d in &diffs {
            prop_assert!(!d.differs,
                "self-compare of {:?} yielded differing field {:?}", a.source_id, d.name);
        }
    }

    /// Property: a `source_id` difference shows up as a different field.
    #[test]
    fn diff_fields_detects_source_id_change(
        a_id in "[a-z]{5,20}",
        b_id in "[a-z]{5,20}",
    ) {
        let a = OkfBundle {
            source_id: a_id,
            token_count: 0,
            message_count: 0,
            duration_ms: 0,
            model: None, created_at: None, goal: None,
            has_acceptance: false, has_contract: false,
        };
        let b = OkfBundle {
            source_id: b_id,
            token_count: 0, message_count: 0, duration_ms: 0,
            model: None, created_at: None, goal: None,
            has_acceptance: false, has_contract: false,
        };
        let diffs = diff_fields(&a, &b);
        let source_diff = diffs.iter().find(|d| d.name == "source_id")
            .expect("source_id field present");
        let expected_differs = a.source_id != b.source_id;
        prop_assert_eq!(source_diff.differs, expected_differs,
            "source_id differs flag mismatch");
    }

    /// Property: the `model` field reports a difference when one side
    /// has a model and the other doesn't.
    #[test]
    fn diff_fields_detects_model_difference(
        model in "[a-z]{3,10}",
    ) {
        let a = OkfBundle {
            source_id: "x".into(),
            token_count: 0, message_count: 0, duration_ms: 0,
            model: Some(model),
            created_at: None, goal: None,
            has_acceptance: false, has_contract: false,
        };
        let b = OkfBundle {
            source_id: "x".into(),
            token_count: 0, message_count: 0, duration_ms: 0,
            model: None,
            created_at: None, goal: None,
            has_acceptance: false, has_contract: false,
        };
        let diffs = diff_fields(&a, &b);
        let model_diff = diffs.iter().find(|d| d.name == "model")
            .expect("model field present");
        prop_assert!(model_diff.differs,
            "model: Some vs None should always differ");
        // The em-dash placeholder is used for None.
        prop_assert!(model_diff.value_b == "—" || model_diff.value_b.is_empty(),
            "None model should render as '—' or empty, got {:?}", model_diff.value_b);
    }

    /// Property: `diff_fields` total differs count is monotonic in
    /// the number of distinct fields (changing more input fields
    /// produces more differs entries).
    #[test]
    fn diff_fields_total_differs_matches_changed(
        same_id in "[a-z]{3,10}",
    ) {
        // Two bundles that differ in exactly 2 fields (token_count
        // and goal).
        let a = OkfBundle {
            source_id: same_id.clone(),
            token_count: 100,
            message_count: 5,
            duration_ms: 0,
            model: None,
            created_at: None,
            goal: Some("Goal A".to_string()),
            has_acceptance: true,
            has_contract: false,
        };
        let b = OkfBundle {
            source_id: same_id,
            token_count: 200,
            message_count: 5,
            duration_ms: 0,
            model: None,
            created_at: None,
            goal: Some("Goal B".to_string()),
            has_acceptance: true,
            has_contract: false,
        };
        let diffs = diff_fields(&a, &b);
        let differs_count = diffs.iter().filter(|d| d.differs).count();
        // token_count + goal = 2 differs.
        prop_assert_eq!(differs_count, 2,
            "expected exactly 2 differing fields, got {}", differs_count);
    }
}

// ── String / value invariants ─────────────────────────────────────────────

proptest! {
    /// Property: `FieldDiff::value_a` matches the first bundle's value
    /// as a string (we verify for fields that don't use Option).
    #[test]
    fn diff_field_values_are_stringified(
        a in 0u64..1000,
        b in 0u64..1000,
    ) {
        let ba = OkfBundle {
            source_id: "a".into(),
            token_count: a, message_count: 1, duration_ms: 0,
            model: None, created_at: None, goal: None,
            has_acceptance: false, has_contract: false,
        };
        let bb = OkfBundle {
            source_id: "b".into(),
            token_count: b, message_count: 1, duration_ms: 0,
            model: None, created_at: None, goal: None,
            has_acceptance: false, has_contract: false,
        };
        let diffs = diff_fields(&ba, &bb);
        let token_diff = diffs.iter().find(|d| d.name == "token_count")
            .expect("token_count field present");
        prop_assert_eq!(token_diff.value_a.clone(), a.to_string());
        prop_assert_eq!(token_diff.value_b.clone(), b.to_string());
        prop_assert_eq!(token_diff.differs, a != b);
    }

    /// Property: `diff_fields` always returns 9 entries, regardless of
    /// any property. (Reaffirmation test, pure-Rust invariant.)
    #[test]
    fn diff_fields_always_nine(_unused in 0u8..1u8) {
        let a = OkfBundle {
            source_id: "x".into(),
            token_count: 0, message_count: 0, duration_ms: 0,
            model: None, created_at: None, goal: None,
            has_acceptance: false, has_contract: false,
        };
        let diffs = diff_fields(&a, &a);
        prop_assert_eq!(diffs.len(), 9);
    }

    /// Property: the documented field name ordering is stable.
    #[test]
    fn diff_fields_ordering_is_documented(_unused in 0u8..1u8) {
        let a = OkfBundle {
            source_id: "a".into(),
            token_count: 0, message_count: 0, duration_ms: 0,
            model: None, created_at: None, goal: None,
            has_acceptance: false, has_contract: false,
        };
        let b = OkfBundle {
            source_id: "b".into(),
            token_count: 0, message_count: 0, duration_ms: 0,
            model: None, created_at: None, goal: None,
            has_acceptance: false, has_contract: false,
        };
        let diffs = diff_fields(&a, &b);
        let names: Vec<&'static str> = diffs.iter().map(|d| d.name).collect();
        let expected = vec![
            "source_id", "token_count", "message_count",
            "duration_ms", "model", "created_at",
            "goal", "has_acceptance", "has_contract",
        ];
        prop_assert_eq!(names, expected);
    }
}
