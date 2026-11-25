//! Property evidence for `sl-viewer::settings` — persistence of user
//! preferences (FR-VIEWER-SETTINGS-1).
//!
//! Invariants under test:
//!
//!  * `DefaultTab` has 9 variants, all distinct
//!  * `DefaultTab::ALL` is the documented canonical ordering
//!  * Every `label()`, `tab_id()`, `value_attr()` returns a non-empty value
//!  * `value_attr()` matches the documented kebab-case strings
//!  * `tab_id()` always has the `tab-` prefix
//!  * `Settings::default()` returns (Theme::System, DefaultTab::Bundles)
//!  * `Settings::save_to_path` -> `load_from_path` is a round-trip identity
//!  * `load_from_path` on a missing file returns defaults silently
//!  * `load_from_path` on corrupt JSON returns defaults silently
//!  * `load_from_path` with partial JSON fills missing fields with defaults
//!  * `save_to_path` creates parent directories
//!  * Every `DefaultTab` variant serializes to lowercase kebab-case JSON

use proptest::prelude::*;
use sl_viewer::settings::{DefaultTab, Settings};
use sl_viewer::theme::Theme;
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};

/// Global counter for unique per-case temp paths.
static CASE_COUNTER: AtomicUsize = AtomicUsize::new(0);

/// Generate a unique temp directory for each proptest case.
fn unique_temp_dir() -> PathBuf {
    let n = CASE_COUNTER.fetch_add(1, Ordering::SeqCst);
    let pid = std::process::id();
    std::env::temp_dir().join(format!("sl-viewer-settings-test-{}-{}", pid, n))
}

// ── DefaultTab enum shape ────────────────────────────────────────────────

const ALL_TABS: [DefaultTab; 9] = [
    DefaultTab::Bundles,
    DefaultTab::History,
    DefaultTab::Unfinished,
    DefaultTab::Memory,
    DefaultTab::LiveFeed,
    DefaultTab::Search,
    DefaultTab::Timeline,
    DefaultTab::Replay,
    DefaultTab::Corpus,
];

proptest! {
    /// Property: `DefaultTab::ALL` has exactly 9 entries.
    #[test]
    fn default_tab_all_cardinality_is_nine(_unused in 0u8..1u8) {
        prop_assert_eq!(DefaultTab::ALL.len(), 9);
    }

    /// Property: `DefaultTab::ALL` matches the static local array of
    /// 9 variants (i.e. we haven't drifted away from the canonical order).
    #[test]
    fn default_tab_all_matches_canonical(_unused in 0u8..1u8) {
        prop_assert_eq!(DefaultTab::ALL.to_vec(), ALL_TABS.to_vec());
    }

    /// Property: every `DefaultTab` variant is distinct.
    #[test]
    fn default_tab_variants_are_distinct(_unused in 0u8..1u8) {
        let mut seen: Vec<DefaultTab> = Vec::with_capacity(ALL_TABS.len());
        for t in ALL_TABS {
            prop_assert!(!seen.contains(&t),
                "duplicate DefaultTab variant in canonical list: {:?}", t);
            seen.push(t);
        }
    }

    /// Property: `DefaultTab::default()` returns `Bundles`.
    #[test]
    fn default_tab_default_is_bundles(_unused in 0u8..1u8) {
        prop_assert_eq!(DefaultTab::default(), DefaultTab::Bundles);
    }
}

// ── DefaultTab per-variant invariants ─────────────────────────────────────

proptest! {
    /// Property: every variant's `label()` is non-empty.
    #[test]
    fn every_default_tab_has_nonempty_label(_unused in 0u8..1u8) {
        for t in ALL_TABS {
            prop_assert!(!t.label().is_empty(),
                "label for {:?} must be non-empty", t);
        }
    }

    /// Property: every variant's `label()` is at most 30 chars (UI bound).
    #[test]
    fn every_default_tab_label_fits_select_option(_unused in 0u8..1u8) {
        for t in ALL_TABS {
            prop_assert!(t.label().len() <= 30,
                "label {:?} too long for select option", t.label());
        }
    }

    /// Property: every variant's `tab_id()` starts with the `tab-` prefix.
    #[test]
    fn every_default_tab_id_has_tab_prefix(_unused in 0u8..1u8) {
        for t in ALL_TABS {
            prop_assert!(t.tab_id().starts_with("tab-"),
                "tab_id {:?} for {:?} must start with 'tab-'",
                t.tab_id(), t);
        }
    }

    /// Property: every variant's `tab_id()` matches the documented
    /// runtime tab IDs in app.rs (stabilization contract).
    #[test]
    fn default_tab_ids_are_pinned(_unused in 0u8..1u8) {
        prop_assert_eq!(DefaultTab::Bundles.tab_id(),    "tab-bundles");
        prop_assert_eq!(DefaultTab::History.tab_id(),    "tab-history");
        prop_assert_eq!(DefaultTab::Unfinished.tab_id(), "tab-unfinished");
        prop_assert_eq!(DefaultTab::Memory.tab_id(),     "tab-memory");
        prop_assert_eq!(DefaultTab::LiveFeed.tab_id(),   "tab-live-feed");
        prop_assert_eq!(DefaultTab::Search.tab_id(),     "tab-search");
        prop_assert_eq!(DefaultTab::Timeline.tab_id(),   "tab-timeline");
        prop_assert_eq!(DefaultTab::Replay.tab_id(),     "tab-replay");
        prop_assert_eq!(DefaultTab::Corpus.tab_id(),     "tab-corpus");
    }

    /// Property: every variant's `value_attr()` is non-empty kebab-case.
    #[test]
    fn every_default_tab_value_attr_is_nonempty(_unused in 0u8..1u8) {
        for t in ALL_TABS {
            let v = t.value_attr();
            prop_assert!(!v.is_empty(),
                "value_attr for {:?} must be non-empty", t);
            for c in v.chars() {
                prop_assert!(c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-',
                    "value_attr {:?} for {:?} has non-kebab char", v, t);
            }
        }
    }

    /// Property: documented value_attr strings are pinned.
    #[test]
    fn default_tab_value_attrs_are_pinned(_unused in 0u8..1u8) {
        prop_assert_eq!(DefaultTab::Bundles.value_attr(), "bundles");
        prop_assert_eq!(DefaultTab::Corpus.value_attr(), "corpus");
        prop_assert_eq!(DefaultTab::LiveFeed.value_attr(), "live-feed");
        prop_assert_eq!(DefaultTab::Memory.value_attr(), "memory");
    }
}

// ── DefaultTab JSON serialization ────────────────────────────────────────

proptest! {
    /// Property: every DefaultTab variant roundtrips through JSON.
    #[test]
    fn default_tab_serializes_to_lowercase_kebab(
        sample in prop::sample::select(ALL_TABS.to_vec()),
    ) {
        let json = serde_json::to_string(&sample).expect("serialize");
        // Should be quoted kebab-case, e.g. `"live-feed"`.
        let inner = json.trim_matches('"');
        prop_assert!(matches!(inner, "bundles" | "history" | "unfinished" | "memory" | "live-feed" | "search" | "timeline" | "replay" | "corpus"),
            "expected kebab-case token, got {:?}", inner);
        let back: DefaultTab = serde_json::from_str(&json).expect("deserialize");
        prop_assert_eq!(back, sample);
    }

    /// Property: every DefaultTab variant's value_attr() equals the JSON
    /// representation stripped of quotes.
    #[test]
    fn default_tab_value_attr_matches_json_inner(_unused in 0u8..1u8) {
        for t in ALL_TABS {
            let json = serde_json::to_string(&t).expect("serialize");
            let inner = json.trim_matches('"');
            prop_assert_eq!(t.value_attr(), inner,
                "{:?} value_attr should match JSON inner", t);
        }
    }
}

// ── Settings shape ────────────────────────────────────────────────────────

proptest! {
    /// Property: `Settings::default()` is `(Theme::System, DefaultTab::Bundles)`.
    #[test]
    fn settings_default_matches_documented(_unused in 0u8..1u8) {
        let s = Settings::default();
        prop_assert_eq!(s.theme, Theme::System);
        prop_assert_eq!(s.default_tab, DefaultTab::Bundles);
    }

    /// Property: Settings derives (Copy + Clone + Default + PartialEq + Eq + Debug).
    #[test]
    fn settings_derives_hold(
        sample in prop::sample::select(vec![
            Settings { theme: Theme::Light, default_tab: DefaultTab::Bundles },
            Settings { theme: Theme::Dark,  default_tab: DefaultTab::Search },
            Settings { theme: Theme::System, default_tab: DefaultTab::Replay },
        ]),
    ) {
        let copied = sample;                  // Copy
        let cloned = sample;                  // Copy (and Clone-compatible)
        prop_assert_eq!(sample, copied);
        prop_assert_eq!(sample, cloned);
        let debug = format!("{:?}", sample);
        prop_assert!(!debug.is_empty());
    }
}

// ── Settings JSON serialization ───────────────────────────────────────────

proptest! {
    /// Property: settings serialize with snake_case field names.
    #[test]
    fn settings_json_uses_snake_case(
        theme in prop::sample::select(vec![Theme::Light, Theme::Dark, Theme::System]),
        tab in prop::sample::select(ALL_TABS.to_vec()),
    ) {
        let s = Settings { theme, default_tab: tab };
        let json = serde_json::to_string(&s).expect("serialize");
        prop_assert!(json.starts_with('{'), "expected JSON object, got {}", json);
        // snake_case for both fields.
        prop_assert!(json.contains("\"theme\""), "missing theme field: {}", json);
        prop_assert!(json.contains("\"default_tab\""), "missing default_tab field: {}", json);
    }

    /// Property: settings JSON round-trip is identity.
    #[test]
    fn settings_json_round_trips(
        theme in prop::sample::select(vec![Theme::Light, Theme::Dark, Theme::System]),
        tab in prop::sample::select(ALL_TABS.to_vec()),
    ) {
        let original = Settings { theme, default_tab: tab };
        let json = serde_json::to_string(&original).expect("serialize");
        let back: Settings = serde_json::from_str(&json).expect("deserialize");
        prop_assert_eq!(back, original);
    }
}

// ── Settings filesystem persistence ───────────────────────────────────────

proptest! {
    /// Property: save_to_path then load_from_path is a round-trip identity.
    #[test]
    fn settings_save_load_round_trip(
        theme in prop::sample::select(vec![Theme::Light, Theme::Dark, Theme::System]),
        tab in prop::sample::select(ALL_TABS.to_vec()),
    ) {
        let dir = unique_temp_dir();
        let path = dir.join("settings.json");
        let original = Settings { theme, default_tab: tab };
        original.save_to_path(&path).expect("save");
        let restored = Settings::load_from_path(&path);
        prop_assert_eq!(restored, original,
            "saved settings did not match loaded");
    }

    /// Property: load_from_path on a missing file returns defaults silently.
    #[test]
    fn settings_missing_file_yields_default(
        _unused in 0u8..1u8,
    ) {
        let dir = unique_temp_dir();
        let path = dir.join("does-not-exist.json");
        let s = Settings::load_from_path(&path);
        prop_assert_eq!(s, Settings::default());
    }

    /// Property: load_from_path on corrupt JSON returns defaults silently.
    #[test]
    fn settings_corrupt_json_yields_default(
        junk in "[^a-zA-Z0-9 \\n]{0,40}",
    ) {
        let dir = unique_temp_dir();
        std::fs::create_dir_all(&dir).expect("mkdir");
        let path = dir.join("settings.json");
        std::fs::write(&path, &junk).expect("write junk");
        let s = Settings::load_from_path(&path);
        prop_assert_eq!(s, Settings::default(),
            "corrupt JSON should yield default, got {:?}", s);
    }

    /// Property: load_from_path with partial JSON (e.g. only theme)
    /// fills missing fields with their own defaults.
    #[test]
    fn settings_partial_json_fills_missing(
        theme in prop::sample::select(vec![Theme::Light, Theme::Dark, Theme::System]),
    ) {
        let dir = unique_temp_dir();
        std::fs::create_dir_all(&dir).expect("mkdir");
        let path = dir.join("settings.json");
        let json_str = match theme {
            Theme::Light => r#"{"theme":"light"}"#,
            Theme::Dark  => r#"{"theme":"dark"}"#,
            Theme::System => r#"{"theme":"system"}"#,
        };
        std::fs::write(&path, json_str).expect("write partial");
        let s = Settings::load_from_path(&path);
        prop_assert_eq!(s.theme, theme);
        prop_assert_eq!(s.default_tab, DefaultTab::default());
    }

    /// Property: save_to_path creates missing parent directories.
    #[test]
    fn settings_save_creates_parents(
        theme in prop::sample::select(vec![Theme::Light, Theme::Dark, Theme::System]),
    ) {
        let dir = unique_temp_dir();
        let path = dir.join("a").join("b").join("c").join("settings.json");
        let s = Settings { theme, default_tab: DefaultTab::Bundles };
        s.save_to_path(&path).expect("save nested");
        prop_assert!(path.exists(), "settings.json should exist");
    }
}
