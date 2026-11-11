//! Property evidence for `sl-viewer::corpus_paths` — the on-disk
//! configuration for user-chosen custom corpus paths.
//!
//! Invariants under test:
//!
//!  * `CorpusPathConfig::empty()` returns a default config (no paths)
//!  * `CorpusPathConfig::default()` == `CorpusPathConfig::empty()`
//!  * `is_empty()` is consistent with `custom_paths.is_empty()`
//!  * Config derives (Clone + PartialEq + Debug + Default + Serialize + Deserialize)
//!  * `save_config_to` -> `load_config_from` is a pure round-trip
//!    (path is created, content matches)
//!  * `load_config_from` on a missing file returns Ok(empty config) per
//!    the documented "missing files yield empty" contract
//!  * `load_config_from` on invalid JSON returns Err (does not panic,
//!    does not silently swallow)
//!  * `save_config_to` creates missing parent directories

use proptest::prelude::*;
use sl_viewer::corpus_paths::{
    default_config_path, load_config_from, save_config_to, CorpusPathConfig,
};
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};

/// Global counter for unique temp paths per proptest case.
static CASE_COUNTER: AtomicUsize = AtomicUsize::new(0);

/// Generate a unique temp directory path per proptest case.
fn unique_temp_dir() -> PathBuf {
    let n = CASE_COUNTER.fetch_add(1, Ordering::SeqCst);
    let pid = std::process::id();
    std::env::temp_dir().join(format!("sl-viewer-corpus-paths-test-{}-{}", pid, n))
}

// ── CorpusPathConfig shape ────────────────────────────────────────────────

proptest! {
    /// Property: `CorpusPathConfig::empty()` equals `CorpusPathConfig::default()`.
    #[test]
    fn empty_equals_default(_unused in 0u8..1u8) {
        prop_assert_eq!(CorpusPathConfig::empty(), CorpusPathConfig::default());
    }

    /// Property: `CorpusPathConfig::empty()` reports `is_empty() == true`
    /// and has zero `custom_paths`.
    #[test]
    fn empty_is_empty(_unused in 0u8..1u8) {
        let cfg = CorpusPathConfig::empty();
        prop_assert!(cfg.is_empty());
        prop_assert_eq!(cfg.custom_paths.len(), 0);
    }

    /// Property: a config with paths is `is_empty() == false`.
    #[test]
    fn config_with_paths_is_not_empty(
        paths in prop::collection::vec(".*", 1..5).prop_map(|v| v.into_iter().map(PathBuf::from).collect()),
    ) {
        let cfg = CorpusPathConfig { custom_paths: paths };
        prop_assert!(!cfg.is_empty());
        prop_assert!(!cfg.custom_paths.is_empty());
    }

    /// Property: `is_empty()` agrees with `custom_paths.is_empty()` for
    /// any state.
    #[test]
    fn is_empty_matches_custom_paths(
        paths in prop::collection::vec(".*", 0..5).prop_map(|v| v.into_iter().map(PathBuf::from).collect()),
    ) {
        let cfg = CorpusPathConfig { custom_paths: paths };
        prop_assert_eq!(cfg.is_empty(), cfg.custom_paths.is_empty());
    }
}

// ── JSON round-trip ───────────────────────────────────────────────────────

proptest! {
    /// Property: a config with arbitrary custom paths serializes to JSON
    /// and deserializes back to itself.
    #[test]
    fn json_round_trip(
        paths in prop::collection::vec(".*", 0..5).prop_map(|v| v.into_iter().map(PathBuf::from).collect()),
    ) {
        let original = CorpusPathConfig { custom_paths: paths };
        let json = serde_json::to_string(&original).expect("serialize");
        let roundtrip: CorpusPathConfig = serde_json::from_str(&json).expect("deserialize");
        prop_assert_eq!(roundtrip, original);
    }

    /// Property: the serialized JSON contains the `custom_paths` field
    /// name (lowercase, snake-case) per the documented file format.
    #[test]
    fn json_uses_custom_paths_field_name(
        paths in prop::collection::vec(".*", 0..3).prop_map(|v| v.into_iter().map(PathBuf::from).collect()),
    ) {
        let cfg = CorpusPathConfig { custom_paths: paths };
        let json = serde_json::to_string(&cfg).expect("serialize");
        prop_assert!(json.contains("custom_paths"),
            "serialized JSON missing 'custom_paths' field: {}", json);
    }

    /// Property: an empty config serializes to a JSON object containing
    /// an empty `custom_paths` array (not just an empty object).
    #[test]
    fn empty_config_serializes_correctly(_unused in 0u8..1u8) {
        let cfg = CorpusPathConfig::empty();
        let json = serde_json::to_string(&cfg).expect("serialize empty");
        prop_assert!(json.contains("\"custom_paths\":[]"),
            "empty config JSON missing empty custom_paths array: {}", json);
    }
}

// ── File IO round-trip ─────────────────────────────────────────────────────

proptest! {
    /// Property: saving a config and reading it back yields an equal
    /// config — the on-disk round-trip preserves all fields.
    #[test]
    fn save_then_load_round_trip(
        dir in temp_dir_with_seed(),
        paths in prop::collection::vec(".*", 0..5).prop_map(|v| v.into_iter().map(PathBuf::from).collect()),
    ) {
        let original = CorpusPathConfig { custom_paths: paths };
        let path = dir.join("corpus_paths.json");
        save_config_to(&original, &path).expect("save");
        let restored = load_config_from(&path).expect("load");
        prop_assert_eq!(restored, original);
    }

    /// Property: `save_config_to` creates the parent directory if it
    /// doesn't exist (nested-write invariant).
    #[test]
    fn save_creates_parent_directories(
        dir in temp_dir_with_seed(),
        paths in prop::collection::vec(".*", 0..3).prop_map(|v| v.into_iter().map(PathBuf::from).collect()),
    ) {
        let nested = dir.join("a").join("b").join("c").join("corpus_paths.json");
        let cfg = CorpusPathConfig { custom_paths: paths };
        save_config_to(&cfg, &nested).expect("save nested");
        prop_assert!(nested.exists(), "save did not create nested file");
    }
}

// ── Error behavior ────────────────────────────────────────────────────────

proptest! {
    /// Property: `load_config_from` on a non-existent file returns
    /// `Ok(CorpusPathConfig::default())` (not an error) — first launch
    /// on a new machine is never supposed to fail.
    #[test]
    fn missing_file_yields_empty_config(
        dir in temp_dir_with_seed(),
    ) {
        std::fs::create_dir_all(&dir).expect("mkdir");
        let path = dir.join("does-not-exist.json");
        let result = load_config_from(&path);
        prop_assert!(result.is_ok(), "missing file should yield Ok, got {:?}", result);
        let cfg = result.unwrap();
        prop_assert!(cfg.is_empty());
        prop_assert_eq!(cfg.custom_paths.len(), 0);
    }

    /// Property: `load_config_from` on invalid JSON returns Err.
    #[test]
    fn invalid_json_yields_error(
        dir in temp_dir_with_seed(),
        junk in "[^a-zA-Z0-9 \\s]{1,30}",
    ) {
        std::fs::create_dir_all(&dir).expect("mkdir");
        let path = dir.join("corpus_paths.json");
        std::fs::write(&path, &junk).expect("write junk");
        let result = load_config_from(&path);
        prop_assert!(result.is_err(),
            "invalid JSON must surface as Err (got {:?})", result);
    }
}

// ── default_config_path ───────────────────────────────────────────────────

proptest! {
    /// Property: `default_config_path()` returns `Some` on this
    /// platform (every CI host has a config dir), and that path
    /// includes "SessionLedger".
    #[test]
    fn default_config_path_resolves_on_this_platform(_unused in 0u8..1u8) {
        let path = default_config_path();
        prop_assert!(path.is_some(),
            "default_config_path should resolve to Some() on this platform");
        let p = path.unwrap();
        let path_str = p.to_string_lossy().to_string();
        prop_assert!(path_str.contains("SessionLedger"),
            "default_config_path {:?} should include 'SessionLedger'", p);
    }

    /// Property: `default_config_path()` is idempotent — calling it
    /// twice in succession yields equal values.
    #[test]
    fn default_config_path_is_deterministic(_unused in 0u8..1u8) {
        let a = default_config_path();
        let b = default_config_path();
        prop_assert_eq!(a, b);
    }
}

// ── Derives ───────────────────────────────────────────────────────────────

proptest! {
    /// Property: CorpusPathConfig derives (Clone + PartialEq + Debug).
    #[test]
    fn corpus_path_config_derives_hold(
        paths in prop::collection::vec(".*", 0..3).prop_map(|v| v.into_iter().map(PathBuf::from).collect()),
    ) {
        let cfg = CorpusPathConfig { custom_paths: paths };
        let cloned = cfg.clone();                         // Clone
        let cf = cfg.clone();
        prop_assert_eq!(cf, cloned);                      // PartialEq + Eq (via clone)
        let debug = format!("{:?}", cfg);                // Debug
        prop_assert!(!debug.is_empty());
    }
}

// Helper: generate a unique temporary directory for each proptest case.
fn temp_dir_with_seed() -> BoxedStrategy<PathBuf> {
    Just(unique_temp_dir()).boxed()
}
