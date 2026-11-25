//! Property evidence for `session_ledger::distill::token_estimator::CharCountTokenEstimator`.
//!
//! The char-count token estimator is the bounded token-budget accountant for
//! the session-ledger distill pipeline. It is invoked every time the
//! distillation pass asks "how many tokens does this slice cost?" — for plain
//! text, for compact JSON, and via the [`TokenEstimator`] trait. If it
//! drifts — `estimate_text` stops rounding up at every 4-char boundary,
//! `estimate_json` no longer matches `serde_json::to_string`, or it starts
//! counting UTF-8 bytes instead of unicode scalar values — every downstream
//! consumer (token-budget slice, resume prompt, search index, memory writer)
//! either over- or under-counts its budget and the whole pipeline silently
//! degrades. This file pins the public API so the contract stays stable.

use proptest::prelude::*;
use serde_json::{json, Value};
use session_ledger::distill::token_estimator::CharCountTokenEstimator;
use session_ledger::TokenEstimator;

/// `CharCountTokenEstimator` must be constructible from `Default` and
/// freely copyable/cloneable — the pipeline spawns many short-lived
/// estimators without ceremony.
#[test]
fn estimator_default_construct_and_copy() {
    let a = <CharCountTokenEstimator as Default>::default();
    let b = a; // Copy via move.
    let c = Clone::clone(&a);
    // Both `a` and `b` are usable: Copy + Clone + Default are exercised.
    assert_eq!(a.estimate_text("abcd"), b.estimate_text("abcd"));
    assert_eq!(a.estimate_text("abcd"), c.estimate_text("abcd"));
}

// ── fixed boundary values (the (chars + 3) / 4 contract) ──────────────────

proptest! {
    /// `estimate_text("") == 0`: empty text costs zero tokens.
    #[test]
    fn empty_text_costs_zero_tokens(_dummy in 0_u8..1) {
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(""), 0);
    }

    /// Length-1 input returns 1 token: `(1 + 3) / 4 == 1`.
    #[test]
    fn length_one_returns_one(ch in 0x20_u8..0x7e) {
        let s = (ch as char).to_string();
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(&s), 1);
    }

    /// Length-4 input returns 1 token: `(4 + 3) / 4 == 1`. The exact
    /// 4-char boundary still rounds DOWN to one token.
    #[test]
    fn length_four_returns_one(s in "[a-z]{4}") {
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(&s), 1);
    }

    /// Length-5 input returns 2 tokens: `(5 + 3) / 4 == 2`.
    #[test]
    fn length_five_returns_two(s in "[a-z]{5}") {
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(&s), 2);
    }

    /// Length-8 input returns 2 tokens: `(8 + 3) / 4 == 2`. The second
    /// 4-char boundary.
    #[test]
    fn length_eight_returns_two(s in "[a-z]{8}") {
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(&s), 2);
    }

    /// Length-9 input returns 3 tokens: `(9 + 3) / 4 == 3`. The third
    /// 4-char boundary (boundary + 1).
    #[test]
    fn length_nine_returns_three(s in "[a-z]{9}") {
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(&s), 3);
    }
}

// ── round-up invariant ─────────────────────────────────────────────────────

proptest! {
    /// For every ASCII text: `estimate_text(text) == (chars + 3) / 4`,
    /// which is `ceil(chars / 4)`. The estimator always rounds UP at every
    /// 4-char boundary.
    #[test]
    fn estimate_text_is_ceil_div_by_four(s in "[a-z]{0,32}") {
        let chars = s.chars().count() as u32;
        let expected = chars.saturating_add(3) / 4;
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(&s), expected);
        // The invariant also bounds the result to `chars/4 + 1` for `chars > 0`.
        if chars > 0 {
            prop_assert!(CharCountTokenEstimator.estimate_text(&s) <= chars / 4 + 1);
        }
    }

    /// For any input, `estimate_text` never over-counts relative to the
    /// strict `ceil(chars/4)` shape: it lives in `[ceil(chars/4), ceil(chars/4)]`
    /// (i.e. exactly equal), but is bounded below by `chars / 4`.
    #[test]
    fn estimate_text_bounded_by_chars_div_four(s in "[a-z]{0,32}") {
        let chars = s.chars().count() as u32;
        let est = CharCountTokenEstimator.estimate_text(&s);
        // Never underestimate: at least chars/4.
        prop_assert!(est >= chars / 4);
        // Never overestimate by more than one token.
        if chars > 0 {
            prop_assert!(est <= chars.div_ceil(4));
        }
    }
}

// ── unicode / emoji behaviour ──────────────────────────────────────────────

proptest! {
    /// The estimator counts unicode SCALAR VALUES (chars), not UTF-8 bytes.
    /// `🦀` is 4 bytes in UTF-8 but 1 char, so 4 of them cost 1 token:
    /// `(4 + 3) / 4 == 1`. Bytes would have given `((4*4)+3)/4 == 4`.
    #[test]
    fn emoji_counts_chars_not_bytes(_dummy in 0_u8..1) {
        let crabs = "\u{1f980}\u{1f980}\u{1f980}\u{1f980}";
        assert_eq!(crabs.len(), 16, "sanity: 4 crabs are 16 UTF-8 bytes");
        assert_eq!(crabs.chars().count(), 4, "sanity: 4 crabs are 4 chars");
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(crabs), 1);
    }

    /// `estimate_text` never panics on any unicode input: a wide mix of
    /// CJK, RTL Arabic, combining marks, and emoji is well-defined.
    #[test]
    fn unicode_never_panics(
        s in proptest::string::string_regex("[\\u{1f980}-\\u{1f9ff}\\u{0600}-\\u{06FF}\\u{4e00}-\\u{9fff}\\u{0300}-\\u{036f}\\u{1F1E6}-\\u{1F1FF}]{0,32}").unwrap()
    ) {
        // Just calling is the assertion: must not panic.
        let est = CharCountTokenEstimator.estimate_text(&s);
        let chars = s.chars().count() as u32;
        prop_assert_eq!(est, chars.saturating_add(3) / 4);
    }

    /// Two texts with identical char counts produce identical token
    /// counts even when their byte counts diverge wildly (ASCII vs CJK).
    /// This is the strongest evidence that the estimator operates on
    /// chars, not bytes.
    #[test]
    fn ascii_and_cjk_of_same_char_count_match(n in 1_usize..=16) {
        let ascii = "a".repeat(n);
        let cjk: String = "\u{4e00}".repeat(n);
        // Sanity: bytes diverge (1 vs 3 each), chars agree.
        prop_assert_eq!(ascii.chars().count(), cjk.chars().count());
        prop_assert_ne!(ascii.len(), cjk.len());
        prop_assert_eq!(
            CharCountTokenEstimator.estimate_text(&ascii),
            CharCountTokenEstimator.estimate_text(&cjk),
        );
    }
}

// ── linearity (within rounding) ────────────────────────────────────────────

proptest! {
    /// `estimate_text(s.repeat(n))` is exactly the ceiling-division on the
    /// total char count of the repeated string: `(chars(s) * n + 3) / 4`.
    /// For `chars(s) >= 4` this collapses to `n * (chars(s) + 3) / 4`
    /// (the rounding distributes), but for small `chars(s)` the per-call
    /// ceiling introduces a one-token "overhead" that disappears at the
    /// larger scale. We pin the exact contract on the repeated char count.
    #[test]
    fn estimate_text_repeat_follows_char_count_contract(
        body in "[a-z]{1,8}",
        n in 1_usize..=4,
    ) {
        let s = body.repeat(n);
        let chars_body = body.chars().count() as u32;
        let chars_total = chars_body * n as u32;
        let expected = chars_total.saturating_add(3) / 4;
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(&s), expected);
    }

    /// For "a" specifically, the documented sequence
    /// `n=1..=8 -> [1, 1, 1, 1, 2, 2, 2, 2]` holds.
    #[test]
    fn single_char_repeat_sequence(n in 1_usize..=8) {
        let s = "a".repeat(n);
        let expected = match n {
            1..=4 => 1,
            5..=8 => 2,
            _ => unreachable!("proptest strategy bounds this at 8"),
        };
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(&s), expected);
    }
}

// ── monotonicity w.r.t. prefix ─────────────────────────────────────────────

proptest! {
    /// `estimate_text(text) >= estimate_text(prefix)` for every
    /// non-empty prefix. The estimator must never be anti-monotonic — a
    /// shorter text must not cost more tokens than a longer text that
    /// contains it.
    #[test]
    fn estimate_text_monotonic_for_prefixes(s in "[a-z]{1,16}") {
        // Try every non-empty prefix length.
        for k in 1..=s.len() {
            let prefix = &s[..k];
            let est_full = CharCountTokenEstimator.estimate_text(&s);
            let est_pre = CharCountTokenEstimator.estimate_text(prefix);
            prop_assert!(est_full >= est_pre);
        }
    }
}

// ── JSON path ──────────────────────────────────────────────────────────────

proptest! {
    /// `estimate_json(&Value::Null) == estimate_text("null") == 1`.
    /// JSON serialisation is compact (no whitespace).
    #[test]
    fn estimate_json_null_equals_text_null(_dummy in 0_u8..1) {
        let v = Value::Null;
        prop_assert_eq!(
            CharCountTokenEstimator.estimate_json(&v),
            CharCountTokenEstimator.estimate_text("null"),
        );
        prop_assert_eq!(CharCountTokenEstimator.estimate_json(&v), 1);
    }

    /// `estimate_json({"key":"value"}) == estimate_text(r#"{"key":"value"}"#)`.
    /// The JSON path defaults to `estimate_text(&value.to_string())`, so
    /// `serde_json::to_string` (compact form) drives the token count.
    #[test]
    fn estimate_json_object_equals_compact_text(_dummy in 0_u8..1) {
        let v = json!({"key": "value"});
        let serialized = v.to_string();
        prop_assert_eq!(serialized.clone(), r#"{"key":"value"}"#);
        prop_assert_eq!(
            CharCountTokenEstimator.estimate_json(&v),
            CharCountTokenEstimator.estimate_text(&serialized),
        );
    }

    /// `estimate_json` always matches `estimate_text(&value.to_string())`,
    /// i.e. it uses compact serialisation (no whitespace, no pretty
    /// printing). We verify across arbitrary JSON shapes.
    #[test]
    fn estimate_json_uses_compact_serialization(
        // A small, bounded JSON value (nested objects + arrays + scalars).
        seed in 0_u32..64,
    ) {
        // Build a deterministic JSON shape from the seed so the test
        // doesn't depend on `proptest`'s value strategy for `serde_json::Value`.
        let v: Value = json!({
            "i": seed,
            "name": format!("item-{seed}"),
            "tags": [seed, seed.wrapping_add(1), seed.wrapping_mul(2)],
            "nested": {
                "a": seed % 4 == 0,
                "b": null,
            },
        });
        let serialized = v.to_string();
        // No whitespace in the compact form.
        prop_assert!(!serialized.contains("  "));
        prop_assert_eq!(
            CharCountTokenEstimator.estimate_json(&v),
            CharCountTokenEstimator.estimate_text(&serialized),
        );
    }

    /// `estimate_json` is total over a wide variety of JSON shapes:
    /// Null, Bool, Number, String, Array, Object — all return a finite
    /// non-zero token count (except Null, which is 4 chars → 1 token).
    #[test]
    fn estimate_json_is_total_and_finite(_dummy in 0_u8..1) {
        let cases: Vec<(&str, Value)> = vec![
            ("null", Value::Null),
            ("true", Value::Bool(true)),
            ("42", json!(42)),
            ("\"hi\"", json!("hi")),
            ("[]", json!([])),
            ("[1,2,3]", json!([1, 2, 3])),
            ("{}", json!({})),
        ];
        for (_label, v) in cases {
            let est = CharCountTokenEstimator.estimate_json(&v);
            // Must match the compact text form.
            let ser = v.to_string();
            prop_assert_eq!(
                est,
                CharCountTokenEstimator.estimate_text(&ser),
            );
        }
    }
}

// ── trait default impl consistency ────────────────────────────────────────

/// A dummy estimator that overrides `estimate_text` and relies on the
/// trait's default `estimate_json`. We confirm that the trait path
/// `self.estimate_text(&value.to_string())` is what `CharCountTokenEstimator`
/// actually does.
struct IdentityEstimator;

impl TokenEstimator for IdentityEstimator {
    fn estimate_text(&self, text: &str) -> u32 {
        text.len() as u32 // deliberately NOT the char-count estimator.
    }
}

proptest! {
    /// When a struct overrides `estimate_text` but uses the trait's default
    /// `estimate_json`, `estimate_json` returns `estimate_text(&v.to_string())`
    /// — confirming the trait default delegates to `estimate_text` rather
    /// than introducing a parallel implementation.
    #[test]
    fn trait_default_estimate_json_delegates_to_estimate_text(
        seed in 0_u32..256,
    ) {
        let v: Value = json!({
            "k": seed,
            "label": format!("l-{seed}"),
        });
        let est = IdentityEstimator;
        let expected = est.estimate_text(&v.to_string());
        prop_assert_eq!(est.estimate_json(&v), expected);
    }

    /// `CharCountTokenEstimator` and the `TokenEstimator` trait default
    /// path agree: the struct uses the trait default (does NOT override
    /// `estimate_json`), so calling `estimate_json` directly must equal
    /// `estimate_text(&value.to_string())` for any input.
    #[test]
    fn char_count_estimator_matches_trait_default_for_json(
        seed in 0_u32..256,
    ) {
        let v: Value = json!({
            "k": seed,
            "label": format!("l-{seed}"),
            "items": [seed, seed.wrapping_add(1)],
        });
        prop_assert_eq!(
            CharCountTokenEstimator.estimate_json(&v),
            CharCountTokenEstimator.estimate_text(&v.to_string()),
        );
    }
}

// ── deterministic, never panics, total ────────────────────────────────────

proptest! {
    /// `estimate_text` is deterministic: two calls on the same input
    /// return the same value. Required for the token-budget slice to be
    /// reproducible across re-distillations.
    #[test]
    fn estimate_text_is_deterministic(s in "[\\u{1f980}\\u{4e00}a-z]{0,32}") {
        let a = CharCountTokenEstimator.estimate_text(&s);
        let b = CharCountTokenEstimator.estimate_text(&s);
        let c = CharCountTokenEstimator.estimate_text(&s);
        prop_assert_eq!(a, b);
        prop_assert_eq!(b, c);
    }

    /// `estimate_text` returns a finite `u32` (never panics, never
    /// overflows): this is the type-system guarantee, but we exercise it
    /// explicitly with the maximum-length char string the strategy can
    /// produce.
    #[test]
    fn estimate_text_is_finite(s in "[a]{0,4096}") {
        let est = CharCountTokenEstimator.estimate_text(&s);
        let expected =
            (u32::try_from(s.chars().count()).expect("generated string fits u32").saturating_add(3))
                / 4;
        prop_assert_eq!(est, expected);
    }

    /// Sanity sweep across a wide distribution of lengths: every length
    /// in `[0, 64]` matches `(chars + 3) / 4`. This is the most direct
    /// property test for the documented ceiling-division contract.
    #[test]
    fn ceiling_division_contract_sweep(length in 0_usize..=64) {
        let s = "a".repeat(length);
        let chars = s.chars().count() as u32;
        let expected = chars.saturating_add(3) / 4;
        prop_assert_eq!(CharCountTokenEstimator.estimate_text(&s), expected);
    }
}
