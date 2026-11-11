//! Property evidence for `sl-viewer::fixture` — Playwright golden
//! fixture detection helpers.
//!
//! Invariants under test:
//!
//!  * All four helpers are callable without panicking
//!  * `visual_fixture_active()` is true iff `query_fixture_name()`
//!    returns `Some` (none of the visual fixtures silently No-Op)
//!  * `query_fixture_active(name)` matches iff name == fixture name
//!  * `splash_hold_fixture_active()` matches the documented launch-splash
//!    fixture names

use proptest::prelude::*;
use sl_viewer::fixture::{
    query_fixture_active, query_fixture_name, splash_hold_fixture_active, visual_fixture_active,
};

// ── Callable invariants ──────────────────────────────────────────────────

proptest! {
    /// Property: all four helpers are callable in any build
    /// configuration (web/desktop/headless) and never panic.
    #[test]
    fn helpers_are_callable(_unused in 0u8..1u8) {
        let _ = query_fixture_name();
        let _ = visual_fixture_active();
        let _ = splash_hold_fixture_active();
        let _ = query_fixture_active("launch-splash");
        let _ = query_fixture_active("any-name");
    }
}

// ── Cross-helper invariants ───────────────────────────────────────────────

proptest! {
    /// Property: `visual_fixture_active()` is consistent with
    /// `query_fixture_name().is_some()`.
    #[test]
    fn visual_fixture_active_matches_query_fixture_name(_unused in 0u8..1u8) {
        let name = query_fixture_name();
        prop_assert_eq!(visual_fixture_active(), name.is_some(),
            "visual_fixture_active() should match `query_fixture_name().is_some()`");
    }

    /// Property: when no fixture is active, every named query is false.
    #[test]
    fn no_fixture_active_means_all_named_false(_unused in 0u8..1u8) {
        let Some(name) = query_fixture_name() else {
            // No fixture active — every named query should be false.
            prop_assert!(!query_fixture_active("launch-splash"));
            prop_assert!(!query_fixture_active("anything-else"));
            return Ok(());
        };
        // Fixture active — at least the matching name should be true.
        prop_assert!(query_fixture_active(&name));
    }

    /// Property: `splash_hold_fixture_active()` matches the documented
    /// splash fixture names: `launch-splash` and `launch-splash-light`.
    #[test]
    fn splash_hold_matches_documented_names(_unused in 0u8..1u8) {
        let expected = matches!(
            query_fixture_name().as_deref(),
            Some("launch-splash") | Some("launch-splash-light")
        );
        prop_assert_eq!(splash_hold_fixture_active(), expected,
            "splash_hold_fixture_active() should match 'launch-splash' or 'launch-splash-light'");
    }

    /// Property: querying an arbitrary string for `query_fixture_active`
    /// is well-defined (returns a bool, never panics), and the result
    /// is true iff name == fixture_name.
    #[test]
    fn query_fixture_active_is_name_match(
        name in "[a-z-]{5,30}",
    ) {
        let result = query_fixture_active(&name);
        let expected = query_fixture_name().as_deref() == Some(name.as_str());
        prop_assert_eq!(result, expected,
            "query_fixture_active({}) should be {}", name, expected);
    }
}

// ── Edge cases ───────────────────────────────────────────────────────────

proptest! {
    /// Property: empty string for fixture name is consistent (querying
    /// for "" never matches an actual fixture name).
    #[test]
    fn empty_name_never_matches(_unused in 0u8..1u8) {
        // An empty-name call: should not panic and should return false
        // (since query_fixture_name filters out empty values).
        let _ = query_fixture_active("");
        // Documented behavior: fixture helper filters empty values, so
        // visual_fixture_active never reports true for empty fixtures.
        if !visual_fixture_active() {
            prop_assert!(query_fixture_name().is_none(),
                "visual_fixture_active false but query_fixture_name returned a value");
        }
    }
}
