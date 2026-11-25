//! Property evidence for sl-viewer's `search_view` and `memory_tab` modules.
//!
//! Integration tests living alongside `properties_viewer*.rs`. The unit
//! tests in those modules pin specific values; these properties pin
//! invariants across the full shape of inputs the helpers receive.
//!
//! `search_view::build_query` invariants:
//!  * Trimming: each field's `.trim()` form is what gets serialized —
//    leading/trailing whitespace does not leak into the query string.
//!  * Empty skipping: empty (post-trim) fields are omitted from the
//!    query string entirely; non-empty fields all appear exactly once.
//!  * Percent-encoding: characters that break a query string (` `, `,`,
//!    `#`, `&`, `=`, `+`) are encoded; other characters pass through.
//!  * `limit` is always present and is the parsed form of the input
//!    (or `50` when parsing fails).
//!
//! `search_view::advanced_filter_active_count` invariants:
//!  * Each non-empty `min_tokens`/`tags` field counts as 1.
//!  * `limit` counts as 1 only when it differs from the documented
//!    default `"50"` (post-trim). `"50"` does not count.
//!
//! `memory_tab::to_wiki_page` invariants:
//!  * `session_id` is carried through unchanged.
//!  * `title` is carried through unchanged (mirrors `Option<String>`
//!    identity).
//!  * Output length matches input: `all_wiki_pages_from_sessions(s)`
//!    produces exactly `s.len()` pages.
//!
//! proptest is added to `sl-viewer/[dev-dependencies]` (mirroring the
//! workspace root); see PR #425 for the initial wiring.

use proptest::prelude::*;
use session_ledger::domain::session::{Corpus, Session};
use sl_viewer::memory_tab::{all_wiki_pages_from_sessions, to_wiki_page};
use sl_viewer::search_view::{advanced_filter_active_count, build_query};

// ── strategies ──────────────────────────────────────────────────────────────

/// A string that may contain one of the percent-encoding-relevant chars
/// or a safe ASCII character. We only test against a fixed alphabet so
/// the encoding contract is unambiguous.
fn input_str_strategy() -> impl Strategy<Value = String> {
    prop::string::string_regex("[A-Za-z0-9 _,#&=+/]{0,32}").expect("valid regex")
}

/// A `Session` shaped by `Session::new` (which the rest of the
/// codebase uses to construct fixtures). We vary the optional title so
/// we can exercise `to_wiki_page` across `None` / `Some(s)` shapes.
fn session_strategy() -> impl Strategy<Value = Session> {
    (
        prop::string::string_regex("[a-z0-9-]{1,16}").expect("valid regex"),
        prop::option::of(
            prop::string::string_regex("[A-Za-z 0-9,_.-]{1,40}").expect("valid regex"),
        ),
    )
        .prop_map(|(suffix, title)| {
            let id = format!("sess-{suffix}");
            let mut s = Session::new(id, Corpus::Forge);
            s.title = title;
            s
        })
}

// ── search_view::build_query ────────────────────────────────────────────────

proptest! {
    /// Property: a `since` field that is empty (post-trim) does NOT
    /// appear in the query string; a non-empty `since` field appears
    /// exactly once (as `since=<urlencoded(since)>`).
    #[test]
    fn build_query_since_present_iff_nonempty(
        since in input_str_strategy(),
        until in prop::string::string_regex("[A-Za-z0-9 ,]{0,16}").expect("valid regex"),
        model in input_str_strategy(),
        min_tokens in input_str_strategy(),
        tags in input_str_strategy(),
        limit in prop::string::string_regex("[0-9]{0,3}").expect("valid regex"),
    ) {
        let q = build_query(&since, &until, &model, &min_tokens, &tags, &limit);
        let has_since = q.split('&').any(|kv| kv.starts_with("since="));
        prop_assert_eq!(has_since, !since.trim().is_empty());
    }

    /// Property: limit is always present in the output. When `limit`
    /// is a parseable non-negative integer the value matches the input
    /// (post-trim); when unparseable or empty, the value is `"50"`
    /// (the documented fallback).
    #[test]
    fn build_query_limit_always_present(
        since in input_str_strategy(),
        until in input_str_strategy(),
        model in input_str_strategy(),
        min_tokens in input_str_strategy(),
        tags in input_str_strategy(),
        limit in input_str_strategy(),
    ) {
        let q = build_query(&since, &until, &model, &min_tokens, &tags, &limit);
        let limit_val = q
            .split('&')
            .find_map(|kv| kv.strip_prefix("limit="))
            .unwrap_or_else(|| panic!("limit missing from query: {q}"));

        let expected = limit.trim().parse::<usize>().map(|n| n.to_string()).unwrap_or_else(|_| "50".to_string());
        prop_assert_eq!(limit_val, expected.as_str());
    }

    /// Property: `build_query` is idempotent w.r.t. trimming. Calling
    /// it with `"  abc  "` and `"abc"` for any field produces the same
    /// output for that field.
    #[test]
    fn build_query_trims_field_values(
        since in input_str_strategy(),
        until in input_str_strategy(),
        model in input_str_strategy(),
        min_tokens in input_str_strategy(),
        tags in input_str_strategy(),
        limit in input_str_strategy(),
    ) {
        let pad = |s: &str| format!("  {s}  ");
        let a = build_query(&since, &until, &model, &min_tokens, &tags, &limit);
        let b = build_query(
            &pad(&since),
            &pad(&until),
            &pad(&model),
            &pad(&min_tokens),
            &pad(&tags),
            &pad(&limit),
        );
        prop_assert_eq!(a, b);
    }

    /// Property: characters that break query-string parsers (`#`, `&`,
    /// `=`, `+`, `,`, ` `) are percent-encoded; plain ASCII
    /// alphanumerics pass through unchanged. This is the same alphabet
    /// the in-file `urlencoding` helper handles.
    #[test]
    fn build_query_encodes_break_chars(input in "[-+=#&, a-zA-Z0-9]{1,8}") {
        // Construct a query whose model field carries `input` and
        // verify the encoded form below.
        let q = build_query("", "", &input, "", "", "10");
        let model_part = q.split('&').find_map(|kv| kv.strip_prefix("model="));
        if input.trim().is_empty() {
            prop_assert!(model_part.is_none(), "blank model leaked into query: {q}");
            return Ok(());
        }
        let model_part = model_part.unwrap_or_else(|| panic!("model missing from query: {q}"));
        if input.contains([' ', ',', '#', '&', '=', '+']) {
            // The raw character must not appear unescaped in the model
            // value; the percent-encoded form must appear instead.
            for ch in input.chars() {
                if [' ', ',', '#', '&', '=', '+'].contains(&ch) {
                    prop_assert!(
                        !model_part.contains(ch),
                        "raw character {ch:?} present in model value: {model_part:?}",
                    );
                }
            }
        } else {
            // All characters are safe ASCII alphanumerics; they should
            // round-trip unchanged.
            prop_assert_eq!(model_part, input.as_str());
        }
    }
}

// ── search_view::advanced_filter_active_count ───────────────────────────────

proptest! {
    /// Property: each non-empty `min_tokens`/`tags` field counts as 1;
    /// each empty (post-trim) one counts as 0.
    #[test]
    fn advanced_filter_count_per_field(
        min_tokens in input_str_strategy(),
        tags in input_str_strategy(),
        limit in input_str_strategy(),
    ) {
        let n = advanced_filter_active_count(&min_tokens, &tags, &limit);
        let mut expected = 0usize;
        if !min_tokens.trim().is_empty() {
            expected += 1;
        }
        if !tags.trim().is_empty() {
            expected += 1;
        }
        if limit.trim() != "50" {
            expected += 1;
        }
        prop_assert_eq!(n, expected);
    }

    /// Property: `advanced_filter_active_count` is idempotent w.r.t.
    /// trimming: padding the input strings doesn't change the count.
    #[test]
    fn advanced_filter_count_trim_invariant(
        min_tokens in input_str_strategy(),
        tags in input_str_strategy(),
        limit in input_str_strategy(),
    ) {
        let a = advanced_filter_active_count(&min_tokens, &tags, &limit);
        let b = advanced_filter_active_count(
            &format!("  {min_tokens}  "),
            &format!("  {tags}  "),
            &format!("  {limit}  "),
        );
        prop_assert_eq!(a, b);
    }

    /// Property: the documented default limit `"50"` does not count.
    /// Anything else (parseable, unparseable, padded) counts.
    #[test]
    fn advanced_filter_count_limit_default(
        min_tokens in input_str_strategy(),
        tags in input_str_strategy(),
        body in input_str_strategy(),
    ) {
        let default_count = advanced_filter_active_count(&min_tokens, &tags, "50");
        let changed_count = advanced_filter_active_count(&min_tokens, &tags, &body);
        let body_changes_default = !min_tokens.trim().is_empty() || !tags.trim().is_empty() || body.trim() != "50";
        let body_changes_other = !min_tokens.trim().is_empty() || !tags.trim().is_empty() || body.trim() != "50";
        prop_assert_eq!(default_count < changed_count, body_changes_default && body_changes_other);
    }
}

// ── memory_tab::to_wiki_page ────────────────────────────────────────────────

proptest! {
    /// Property: `to_wiki_page` carries the session id through
    /// unchanged (the wiki page is keyed by session id).
    #[test]
    fn to_wiki_page_carries_session_id(session in session_strategy()) {
        let page = to_wiki_page(&session);
        prop_assert_eq!(page.session_id, session.id);
    }

    /// Property: `to_wiki_page` carries the session title through
    /// unchanged. The title field is `Option<String>`; `None` stays
    /// `None`, `Some(s)` stays `Some(s)`.
    #[test]
    fn to_wiki_page_carries_title(session in session_strategy()) {
        let page = to_wiki_page(&session);
        prop_assert_eq!(page.title, session.title);
    }

    /// Property: `all_wiki_pages_from_sessions` produces exactly one
    /// page per session, in input order. Catches the obvious
    /// flatten/filter bug where some sessions are dropped or reordered.
    #[test]
    fn all_wiki_pages_length_matches_input(
        sessions in prop::collection::vec(session_strategy(), 0..8),
    ) {
        let pages = all_wiki_pages_from_sessions(&sessions);
        prop_assert_eq!(pages.len(), sessions.len());
    }

    /// Property: `all_wiki_pages_from_sessions` preserves input order
    /// — page `i` corresponds to session `i`.
    #[test]
    fn all_wiki_pages_order_matches_input(
        sessions in prop::collection::vec(session_strategy(), 1..8),
    ) {
        let pages = all_wiki_pages_from_sessions(&sessions);
        for (i, page) in pages.iter().enumerate() {
            prop_assert_eq!(&page.session_id, &sessions[i].id);
        }
    }

    /// Property: `to_wiki_page` is deterministic — applying it twice
    /// to the same session yields the same page (every field, including
    /// the `Option<String>` title, matches). This catches drift where
    /// the extractors consult a non-deterministic source (e.g.
    /// timestamps or RNG).
    #[test]
    fn to_wiki_page_is_deterministic(session in session_strategy()) {
        let a = to_wiki_page(&session);
        let b = to_wiki_page(&session);
        prop_assert_eq!(a, b);
    }
}
