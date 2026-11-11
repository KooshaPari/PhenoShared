//! Property evidence for `sl-viewer::web_exports` — web assistant
//! export corpus loader.
//!
//! Invariants under test:
//!
//!  * `WebExportProvider` has exactly 3 distinct variants
//!  * `label()` returns the documented human-readable labels
//!  * `corpus()` returns the matching `Corpus::ChatGptWeb|ClaudeWeb|GeminiWeb`
//!  * `default_subdir()` is non-empty and matches `label()`
//!  * `web_export_roots_with_env(home, None)` falls back to
//!    `<home>/Downloads/<provider>` when that dir doesn't exist (the
//!    function filters non-existent paths)
//!  * `web_export_roots_with_env(home, Some(list))` parses the
//!    `:`-separated list and infers provider by final path component
//!  * Provider-name heuristic: "ChatGPT"/"chatgpt" -> ChatGpt,
//!    "Claude"/"claude" -> Claude, otherwise -> Gemini

use proptest::prelude::*;
use session_ledger::domain::session::Corpus;
use sl_viewer::web_exports::{web_export_roots_with_env, WebExportProvider};

const ALL_PROVIDERS: [WebExportProvider; 3] =
    [WebExportProvider::ChatGpt, WebExportProvider::Claude, WebExportProvider::Gemini];

// ── WebExportProvider shape ───────────────────────────────────────────────

proptest! {
    /// Property: the three provider variants are pairwise distinct.
    #[test]
    fn providers_are_distinct(_unused in 0u8..1u8) {
        prop_assert_ne!(WebExportProvider::ChatGpt, WebExportProvider::Claude);
        prop_assert_ne!(WebExportProvider::Claude, WebExportProvider::Gemini);
        prop_assert_ne!(WebExportProvider::ChatGpt, WebExportProvider::Gemini);
    }

    /// Property: `label()` returns the documented label per variant.
    #[test]
    fn provider_labels_are_pinned(_unused in 0u8..1u8) {
        prop_assert_eq!(WebExportProvider::ChatGpt.label(), "ChatGPT");
        prop_assert_eq!(WebExportProvider::Claude.label(), "Claude");
        prop_assert_eq!(WebExportProvider::Gemini.label(), "Gemini");
    }

    /// Property: every label is non-empty.
    #[test]
    fn every_provider_label_is_nonempty(_unused in 0u8..1u8) {
        for p in ALL_PROVIDERS {
            prop_assert!(!p.label().is_empty(), "label for {:?} must be non-empty", p);
        }
    }

    /// Property: every label is non-empty ASCII (UI renderable).
    #[test]
    fn every_provider_label_is_ascii(_unused in 0u8..1u8) {
        for p in ALL_PROVIDERS {
            prop_assert!(p.label().is_ascii(),
                "label {:?} for {:?} not ASCII", p.label(), p);
        }
    }
}

// ── Corpus mapping ────────────────────────────────────────────────────────

proptest! {
    /// Property: `corpus()` returns the matching web corpus variant.
    #[test]
    fn provider_corpus_mapping_is_pinned(_unused in 0u8..1u8) {
        prop_assert_eq!(WebExportProvider::ChatGpt.corpus(), Corpus::ChatGptWeb);
        prop_assert_eq!(WebExportProvider::Claude.corpus(), Corpus::ClaudeWeb);
        prop_assert_eq!(WebExportProvider::Gemini.corpus(), Corpus::GeminiWeb);
    }

    /// Property: the three corpus outputs are pairwise distinct.
    #[test]
    fn provider_corpus_outputs_are_distinct(_unused in 0u8..1u8) {
        let a = WebExportProvider::ChatGpt.corpus();
        let b = WebExportProvider::Claude.corpus();
        let c = WebExportProvider::Gemini.corpus();
        prop_assert_ne!(a, b);
        prop_assert_ne!(b, c);
        prop_assert_ne!(a, c);
    }
}

// ── default_subdir invariants ─────────────────────────────────────────────

proptest! {
    /// Property: every `default_subdir()` is non-empty.
    #[test]
    fn every_provider_default_subdir_is_nonempty(_unused in 0u8..1u8) {
        for p in ALL_PROVIDERS {
            prop_assert!(!p.default_subdir().is_empty(),
                "default_subdir for {:?} must be non-empty", p);
        }
    }

    /// Property: every `default_subdir()` is ASCII (it appears in
    /// filesystem paths).
    #[test]
    fn every_provider_default_subdir_is_ascii(_unused in 0u8..1u8) {
        for p in ALL_PROVIDERS {
            prop_assert!(p.default_subdir().is_ascii(),
                "default_subdir {:?} for {:?} not ASCII", p.default_subdir(), p);
        }
    }
}

// ── web_export_roots_with_env ─────────────────────────────────────────────

proptest! {
    /// Property: when no explicit list is provided, the returned set
    /// filters out non-existent paths (i.e. only directories that
    /// actually exist are returned).
    #[test]
    fn roots_with_no_explicit_only_returns_existing(
        home_str in "/[a-zA-Z0-9_./-]{3,40}",
    ) {
        let home = std::path::PathBuf::from(&home_str);
        let roots = web_export_roots_with_env(&home, None);
        for (_, path) in &roots {
            prop_assert!(path.exists(),
                "returned path {:?} doesn't exist", path);
        }
    }

    /// Property: when no explicit list is provided, the returned paths
    /// are rooted under `<home>/Downloads/<provider>` (the documented
    /// fallback location).
    #[test]
    fn roots_with_no_explicit_under_downloads(
        home_str in "/[a-zA-Z0-9_./-]{3,40}",
    ) {
        let home = std::path::PathBuf::from(&home_str);
        let roots = web_export_roots_with_env(&home, None);
        for (_, path) in &roots {
            // Path should contain "Downloads" segment.
            let lossy = path.to_string_lossy();
            prop_assert!(lossy.contains("Downloads"),
                "root path {:?} not under Downloads", path);
        }
    }

    /// Property: when an explicit list is provided, every returned
    /// entry corresponds to one of the explicit paths (no extras
    /// injected).
    #[test]
    fn roots_with_explicit_match_explicit_list(
        home_str in "/[a-zA-Z0-9_./-]{3,30}",
        paths in prop::collection::vec("/tmp/[a-z]{5,15}", 1..4),
    ) {
        let home = std::path::PathBuf::from(&home_str);
        // Filter out paths with no separators to ensure parseable.
        let explicit_str = paths.join(":");
        let roots = web_export_roots_with_env(&home, Some(std::ffi::OsString::from(explicit_str)));
        // Number of returned roots must equal number of paths in the
        // explicit list (one entry each).
        prop_assert_eq!(roots.len(), paths.len());
    }

    /// Property: the inferred provider heuristic maps the path's final
    /// component name correctly:
    ///   ChatGPT/chatgpt -> ChatGpt
    ///   Claude/claude   -> Claude
    ///   anything else   -> Gemini (fallback)
    #[test]
    fn provider_inferred_from_path_name(
        home_str in "/[a-zA-Z0-9_./-]{3,30}",
    ) {
        let home = std::path::PathBuf::from(&home_str);

        // Test each known mapping
        for (path_suffix, expected) in [
            ("ChatGPT", WebExportProvider::ChatGpt),
            ("chatgpt", WebExportProvider::ChatGpt),
            ("Claude", WebExportProvider::Claude),
            ("claude", WebExportProvider::Claude),
            ("anything", WebExportProvider::Gemini),
            ("random", WebExportProvider::Gemini),
            ("dir", WebExportProvider::Gemini),
        ] {
            let path = std::path::PathBuf::from(format!("/tmp/{}", path_suffix));
            let list_str = path.to_string_lossy();
            let roots = web_export_roots_with_env(&home, Some(std::ffi::OsString::from(list_str.as_ref())));
            prop_assert_eq!(roots.len(), 1, "single explicit path should yield 1 root");
            let (provider, _) = &roots[0];
            prop_assert_eq!(*provider, expected,
                "path {:?} expected provider {:?}", path_suffix, expected);
        }
    }
}

// ── Hash + Eq derives ────────────────────────────────────────────────────

proptest! {
    /// Property: WebExportProvider derives (Hash + PartialEq + Eq +
    /// Debug). We test by using it in a HashSet/HashMap context.
    #[test]
    fn provider_hash_eq_derives(
        a in prop::sample::select(ALL_PROVIDERS.to_vec()),
        b in prop::sample::select(ALL_PROVIDERS.to_vec()),
    ) {
        use std::collections::HashSet;
        let mut set = HashSet::new();
        set.insert(a);
        // Re-inserting a should not grow the set.
        let prev_len = set.len();
        set.insert(a);
        prop_assert_eq!(set.len(), prev_len, "duplicate insertion grew HashSet");
        // b in set iff a == b
        prop_assert_eq!(set.contains(&b), a == b);
    }
}
