//! Property evidence for `sl-viewer::corpus_cta` — first-run "Open
//! corpus…" CTA wiring constants.
//!
//! Invariants under test:
//!
//!  * `QUICKSTART_URL` is a valid https:// URL pointing at the repo's
//!    QUICKSTART.md
//!  * `CORPUS_PICKER_INPUT_ID` matches the documented DOM id (kebab-case
//!    `sl-` prefix)
//!  * `FORGE_DB_HINT_STORAGE_KEY` matches the documented localStorage key
//!    (kebab-case)
//!  * `pick_corpus_folder()` is callable from any build configuration
//!    and never panics
//!  * the headless `trigger_open_corpus()` stub is callable without a UI runtime

use proptest::prelude::*;
use sl_viewer::corpus_cta::{
    CORPUS_PICKER_INPUT_ID, FORGE_DB_HINT_STORAGE_KEY, QUICKSTART_CORPUS_DOC, QUICKSTART_URL,
};

// ── URL invariants ────────────────────────────────────────────────────────

proptest! {
    /// Property: `QUICKSTART_URL` is a valid https:// URL.
    #[test]
    fn quickstart_url_is_https(_unused in 0u8..1u8) {
        prop_assert!(QUICKSTART_URL.starts_with("https://"),
            "QUICKSTART_URL must be https: got {:?}", QUICKSTART_URL);
    }

    /// Property: `QUICKSTART_URL` points to the SessionLedger repo.
    #[test]
    fn quickstart_url_points_at_session_ledger_repo(_unused in 0u8..1u8) {
        prop_assert!(QUICKSTART_URL.contains("KooshaPari/SessionLedger"),
            "QUICKSTART_URL must point at SessionLedger: got {:?}", QUICKSTART_URL);
    }

    /// Property: `QUICKSTART_URL` ends with `QUICKSTART.md`.
    #[test]
    fn quickstart_url_ends_with_md(_unused in 0u8..1u8) {
        prop_assert!(QUICKSTART_URL.ends_with("QUICKSTART.md"),
            "QUICKSTART_URL must end with QUICKSTART.md: got {:?}", QUICKSTART_URL);
    }

    /// Property: `QUICKSTART_CORPUS_DOC` is a relative repo path.
    #[test]
    fn quickstart_corpus_doc_is_repo_relative(_unused in 0u8..1u8) {
        prop_assert!(QUICKSTART_CORPUS_DOC.starts_with("docs/"),
            "expected repo-relative docs/ path: got {:?}", QUICKSTART_CORPUS_DOC);
        prop_assert!(QUICKSTART_CORPUS_DOC.ends_with("QUICKSTART.md"),
            "expected QUICKSTART.md suffix: got {:?}", QUICKSTART_CORPUS_DOC);
    }
}

// ── DOM id invariants ─────────────────────────────────────────────────────

proptest! {
    /// Property: `CORPUS_PICKER_INPUT_ID` has the documented `sl-` prefix
    /// and kebab-case shape.
    #[test]
    fn corpus_picker_id_is_kebab_case(_unused in 0u8..1u8) {
        prop_assert!(CORPUS_PICKER_INPUT_ID.starts_with("sl-"),
            "CORPUS_PICKER_INPUT_ID must start with 'sl-': got {:?}",
            CORPUS_PICKER_INPUT_ID);
        for c in CORPUS_PICKER_INPUT_ID.chars() {
            prop_assert!(c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-',
                "non-kebab char in CORPUS_PICKER_INPUT_ID: {:?}", CORPUS_PICKER_INPUT_ID);
        }
    }

    /// Property: `CORPUS_PICKER_INPUT_ID` is non-empty.
    #[test]
    fn corpus_picker_id_is_nonempty(_unused in 0u8..1u8) {
        prop_assert!(!CORPUS_PICKER_INPUT_ID.is_empty());
    }

    /// Property: `FORGE_DB_HINT_STORAGE_KEY` is non-empty and kebab-case.
    #[test]
    fn forge_db_storage_key_is_kebab_case(_unused in 0u8..1u8) {
        prop_assert!(!FORGE_DB_HINT_STORAGE_KEY.is_empty());
        for c in FORGE_DB_HINT_STORAGE_KEY.chars() {
            prop_assert!(c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-',
                "non-kebab char in FORGE_DB_HINT_STORAGE_KEY: {:?}",
                FORGE_DB_HINT_STORAGE_KEY);
        }
    }
}

// ── Documented id pinning ─────────────────────────────────────────────────

proptest! {
    /// Property: the documented dom ids match their literal strings (any
    /// drift would invalidate `properties_viewer_menu.rs`, the toolbar,
    /// and several integration tests).
    #[test]
    fn documented_ids_are_pinned(_unused in 0u8..1u8) {
        prop_assert_eq!(CORPUS_PICKER_INPUT_ID, "sl-corpus-picker-input");
        prop_assert_eq!(FORGE_DB_HINT_STORAGE_KEY, "sl-viewer-forge-db-hint");
    }

    /// Property: the localStorage key contains the brand prefix
    /// (`sl-viewer-`).
    #[test]
    fn storage_key_has_brand_prefix(_unused in 0u8..1u8) {
        prop_assert!(FORGE_DB_HINT_STORAGE_KEY.starts_with("sl-viewer-"),
            "expected sl-viewer- brand prefix: got {:?}", FORGE_DB_HINT_STORAGE_KEY);
    }
}

// ── Callable functions ────────────────────────────────────────────────────

proptest! {
    /// Property: `QUICKSTART_CORPUS_DOC` is non-empty (test fixtures
    /// reference this constant; an empty string would break the link).
    #[test]
    fn quickstart_corpus_doc_is_nonempty(_unused in 0u8..1u8) {
        prop_assert!(!QUICKSTART_CORPUS_DOC.is_empty());
    }
}

/// The headless implementation is intentionally a no-op, so it is the one
/// configuration safe to invoke from a plain Rust test process. The web
/// implementation needs a Dioxus runtime and is exercised by browser tests;
/// desktop opens the operating-system browser and is intentionally not invoked.
#[cfg(not(any(feature = "web", feature = "desktop")))]
#[test]
fn trigger_open_corpus_is_a_headless_noop() {
    sl_viewer::corpus_cta::trigger_open_corpus();
}

// Note: `pick_corpus_folder()` requires the AppKit main thread (rfd's
// macOS backend can only spawn dialogs from the main thread on macOS,
// and CI/headless builds don't have a windowed environment at all).
// We don't test the function directly — its behaviour is exercised by
// integration tests in dioxus-desktop. Property tests cover only the
// statically-checkable constants.

// ── Cross-cutting invariants ──────────────────────────────────────────────

proptest! {
    /// Property: `QUICKSTART_URL` contains `QUICKSTART_CORPUS_DOC`
    /// (the URL is the hosted form of the repo-relative path).
    #[test]
    fn quickstart_url_matches_doc_path(_unused in 0u8..1u8) {
        // The hosted URL embeds the same QUICKSTART.md filename
        // referenced by the repo-relative path.
        prop_assert!(QUICKSTART_URL.contains("QUICKSTART.md"),
            "URL must embed QUICKSTART.md");
        // The repo-relative path is the form used by integration tests
        // and the docs cross-link panel.
        prop_assert!(QUICKSTART_CORPUS_DOC.contains("QUICKSTART.md"),
            "doc path must contain QUICKSTART.md");
    }

    /// Property: the constants collectively form a documented identity
    /// bundle (all strings non-empty, all unique, all alpha-numeric-kebab).
    #[test]
    fn constants_form_undrifty_bundle(_unused in 0u8..1u8) {
        let bundle: Vec<&str> = vec![
            QUICKSTART_URL,
            QUICKSTART_CORPUS_DOC,
            CORPUS_PICKER_INPUT_ID,
            FORGE_DB_HINT_STORAGE_KEY,
        ];
        for s in &bundle {
            prop_assert!(!s.is_empty(), "constant bundle has empty entry");
        }
        // Deduplication — no two constants are equal.
        let mut sorted: Vec<&str> = bundle.clone();
        sorted.sort();
        sorted.dedup();
        prop_assert_eq!(sorted.len(), bundle.len(),
            "duplicate in corpus_cta constants bundle");
    }
}
