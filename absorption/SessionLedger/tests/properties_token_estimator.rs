//! Property evidence for `session_ledger::distill::token_estimator`.
//!
//! Invariants under test:
//!
//!  * `CharCountTokenEstimator::estimate_text("")` returns 0
//!  * `estimate_text` rounds up to 4-character chunks
//!  * `estimate_text` counts Unicode characters (not UTF-8 bytes)
//!  * `estimate_text` and `estimate_json` agree on compact JSON
//!  * Default + Clone + Copy derives hold for `CharCountTokenEstimator`
//!  * `estimate_text` is monotonic (longer text never returns fewer tokens)
//!  * `estimate_text` is deterministic (same input -> same output)

use proptest::prelude::*;
use session_ledger::distill::token_estimator::{CharCountTokenEstimator, TokenEstimator};

// ── Basic invariants ─────────────────────────────────────────────────────

proptest! {
    /// Property: `estimate_text("")` returns 0 tokens.
    #[test]
    fn empty_text_costs_zero_tokens(_unused in 0u8..1u8) {
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(""), 0);
    }

    /// Property: `estimate_text` rounds up to 4-char chunks
    /// (ceil(chars / 4)).
    ///   1 char -> 1 token, 4 chars -> 1, 5 chars -> 2, 8 chars -> 2,
    ///   9 chars -> 3.
    #[test]
    fn estimate_text_rounds_up_to_4char_chunks(
        n in 0u32..500,
    ) {
        let text = "a".repeat(n as usize);
        let expected = n.saturating_add(3) / 4;
        let actual = CharCountTokenEstimator.estimate_text(&text);
        prop_assert_eq!(actual, expected,
            "n = {} chars, expected {} tokens, got {}", n, expected, actual);
    }

    /// Property: `estimate_text` is deterministic (same input -> same output).
    #[test]
    fn estimate_text_is_deterministic(
        text in ".*",
    ) {
        let a = CharCountTokenEstimator.estimate_text(&text);
        let b = CharCountTokenEstimator.estimate_text(&text);
        prop_assert_eq!(a, b, "estimate_text must be deterministic");
    }

    /// Property: `estimate_text` is monotonic — adding chars never
    /// decreases the token estimate.
    #[test]
    fn estimate_text_is_monotonic(
        prefix in ".*",
        suffix in ".*",
    ) {
        let p = CharCountTokenEstimator.estimate_text(&prefix);
        let s = CharCountTokenEstimator.estimate_text(&suffix);
        let combo = CharCountTokenEstimator.estimate_text(&format!("{prefix}{suffix}"));
        prop_assert!(combo >= p, "estimate_text must be monotonic: {p} > {combo} for prefix {prefix:?}");
        prop_assert!(combo >= s, "estimate_text must be monotonic: {s} > {combo} for suffix {suffix:?}");
    }
}

// ── Unicode handling ──────────────────────────────────────────────────────

proptest! {
    /// Property: `estimate_text` counts Unicode characters (not UTF-8 bytes).
    /// A 4-crab string is 4 chars but 16 UTF-8 bytes; the estimate must
    /// be 1 token (4 chars / 4), not 4 tokens (16 bytes / 4).
    #[test]
    fn unicode_4crab_costs_one_token(_unused in 0u8..1u8) {
        let crabs = "🦀🦀🦀🦀";
        prop_assert_eq!(crabs.len(), 16, "4 emoji should be 16 UTF-8 bytes");
        prop_assert_eq!(crabs.chars().count(), 4, "4 emoji should be 4 chars");
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(crabs), 1);
    }

    /// Property: `estimate_text` produces the same number for any
    /// string of `n` characters (regardless of what those chars are).
    /// We test by generating two strings of the same length and
    /// checking they cost the same.
    #[test]
    fn text_count_depends_on_char_count_only(
        text in ".*",
    ) {
        let n = text.chars().count();
        let text_of_same_length = "a".repeat(n);
        let expected = CharCountTokenEstimator.estimate_text(&text_of_same_length);
        let actual = CharCountTokenEstimator.estimate_text(&text);
        prop_assert_eq!(actual, expected,
            "estimate_text should be char-count-based");
    }
}

// ── JSON estimates ────────────────────────────────────────────────────────

proptest! {
    /// Property: `estimate_json` agrees with `estimate_text` on the
    /// compact JSON serialization.
    #[test]
    fn json_estimate_matches_compact_text(
        key in "[a-z]{3,15}",
        value in ".*",
    ) {
        let v = serde_json::json!({ &key: value });
        let json_estimate = CharCountTokenEstimator.estimate_json(&v);
        let text_estimate = CharCountTokenEstimator.estimate_text(&v.to_string());
        prop_assert_eq!(json_estimate, text_estimate);
    }

    /// Property: `estimate_json` is deterministic for the same input.
    #[test]
    fn json_estimate_is_deterministic(
        key in "[a-z]{3,12}",
        value in any::<i64>(),
    ) {
        let v = serde_json::json!({ &key: value });
        let a = CharCountTokenEstimator.estimate_json(&v);
        let b = CharCountTokenEstimator.estimate_json(&v);
        prop_assert_eq!(a, b);
    }

    /// Property: `estimate_json` for a null value costs at least 1
    /// token (the string "null" is 4 chars -> 1 token).
    #[test]
    fn json_null_costs_one_token(_unused in 0u8..1u8) {
        let v = serde_json::Value::Null;
        prop_assert_eq!(CharCountTokenEstimator.estimate_json(&v), 1);
    }

    /// Property: `estimate_json` for an empty array costs 1 token
    /// ("[]" is 2 chars -> ceil(2/4) = 1).
    #[test]
    fn json_empty_array_costs_one_token(_unused in 0u8..1u8) {
        let v = serde_json::json!([]);
        prop_assert_eq!(CharCountTokenEstimator.estimate_json(&v), 1);
    }
}

// ── Derives ───────────────────────────────────────────────────────────────

proptest! {
    /// Property: `CharCountTokenEstimator` derives (Default + Clone + Copy +
    /// Debug).
    #[test]
    fn char_count_estimator_derives_hold(_unused in 0u8..1u8) {
        let a = CharCountTokenEstimator; // Copy
        let b = Clone::clone(&a); // Clone
        let c: CharCountTokenEstimator = default_value();
        let debug = format!("{a:?}");
        prop_assert!(!debug.is_empty());
        // All three values should produce the same estimate for the
        // same input (defensive assertion).
        let text = "hello";
        let ea = a.estimate_text(text);
        let eb = b.estimate_text(text);
        let ec = c.estimate_text(text);
        prop_assert_eq!(ea, eb);
        prop_assert_eq!(eb, ec);
    }
}

fn default_value<T: Default>() -> T {
    T::default()
}

// ── Composite use via trait ───────────────────────────────────────────────

proptest! {
    /// Property: a trait-object dispatch via `&dyn TokenEstimator`
    /// exercises the same path as the concrete impl.
    #[test]
    fn trait_object_dispatch_matches_concrete(
        text in ".*",
    ) {
        let text = text.clone();
        let concrete = CharCountTokenEstimator.estimate_text(&text);
        let dyn_est: &dyn TokenEstimator = &CharCountTokenEstimator;
        let via_dyn = dyn_est.estimate_text(&text);
        prop_assert_eq!(concrete, via_dyn,
            "concrete vs trait-object dispatch must agree");
    }
}
