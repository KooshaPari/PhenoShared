//! Property evidence for `sl-viewer::menu` id constants and naming.
//!
//! Menu item ids follow the `sl-viewer.<group>.<action>` taxonomy. The
//! app's main muda event handler in `app.rs` dispatches by matching
//! `event.id().0.as_str()` against these constants — a typo or rename
//! in any of them silently breaks the menu wiring (the menu event would
//! fire but no DOM control would react).
//!
//! Invariants under test:
//!
//!  * Every id starts with `sl-viewer.` (the documented prefix)
//!  * No two ids are identical
//!  * The id family (`app`/`file`/`edit`/`view`/`help`) matches the
//!    documented taxonomy
//!  * Ids are non-empty ASCII
//!  * The full set of documented ids covers the menu cardinality (10 ids
//!    in total: 2 app + 2 file + 1 edit + 3 view + 1 help + 1 hidden).
//!
//! Note: this module is compiled only when the `desktop` feature is on,
//! so the property tests are also gated on `#[cfg(feature = "desktop")]`.
//! Without the feature, the menu module — and the test — does not exist.

#![cfg(feature = "desktop")]

use proptest::prelude::*;
use sl_viewer::menu::{
    ID_APP_ABOUT, ID_APP_SETTINGS, ID_EDIT_FIND, ID_FILE_RELOAD_DISCOVERY, ID_FILE_SETTINGS,
    ID_HELP_TOGGLE, ID_VIEW_COMMAND_PALETTE, ID_VIEW_RELOAD, ID_VIEW_TOGGLE_THEME,
};

/// All documented menu ids as a `&[&'static str]` for proptest sampling.
const ALL_IDS: &[&str] = &[
    ID_APP_ABOUT,
    ID_APP_SETTINGS,
    ID_FILE_RELOAD_DISCOVERY,
    ID_FILE_SETTINGS,
    ID_EDIT_FIND,
    ID_VIEW_RELOAD,
    ID_VIEW_TOGGLE_THEME,
    ID_VIEW_COMMAND_PALETTE,
    ID_HELP_TOGGLE,
];

// ── id prefix ─────────────────────────────────────────────────────────────

proptest! {
    /// Property: every documented menu id starts with the `sl-viewer.`
    /// prefix. Catches a typo like `s-viewer.file.reload-discovery`.
    #[test]
    fn every_menu_id_has_sl_viewer_prefix(_unused in 0u8..1u8) {
        for id in ALL_IDS {
            prop_assert!(
                id.starts_with("sl-viewer."),
                "menu id {:?} must start with 'sl-viewer.'",
                id,
            );
        }
    }

    /// Property: every menu id is non-empty.
    #[test]
    fn every_menu_id_is_nonempty(_unused in 0u8..1u8) {
        for id in ALL_IDS {
            prop_assert!(!id.is_empty(), "menu id must be non-empty");
        }
    }

    /// Property: every menu id is ASCII (the muda wire format expects
    /// UTF-8 but using non-ASCII in id strings would cause subtle cross-
    /// platform encoding issues).
    #[test]
    fn every_menu_id_is_ascii(_unused in 0u8..1u8) {
        for id in ALL_IDS {
            prop_assert!(
                id.is_ascii(),
                "menu id {:?} must be ASCII",
                id,
            );
        }
    }

    /// Property: every menu id is strictly kebab-case after the
    /// `sl-viewer.` prefix (lowercase letters, digits, dashes, dots).
    #[test]
    fn every_menu_id_is_kebab_case(_unused in 0u8..1u8) {
        for id in ALL_IDS {
            let suffix = id.trim_start_matches("sl-viewer.");
            prop_assert!(!suffix.is_empty(), "id {:?} has no suffix after prefix", id);
            for c in suffix.chars() {
                prop_assert!(
                    c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-' || c == '.',
                    "menu id {:?} has non-kebab char {:?}",
                    id,
                    c,
                );
            }
        }
    }
}

// ── uniqueness ───────────────────────────────────────────────────────────

proptest! {
    /// Property: no two documented menu ids are identical. (Duplicate ids
    /// would make muda dispatch ambiguous at runtime.)
    #[test]
    fn menu_ids_are_unique(_unused in 0u8..1u8) {
        let mut seen: Vec<&str> = Vec::with_capacity(ALL_IDS.len());
        for id in ALL_IDS {
            prop_assert!(!seen.contains(id), "duplicate menu id {:?}", id);
            seen.push(id);
        }
    }
}

// ── taxonomy ─────────────────────────────────────────────────────────────

proptest! {
    /// Property: every menu id maps to a documented family. The family
    /// is the second component of `sl-viewer.<family>.<action>`.
    #[test]
    fn menu_ids_use_documented_families(
        sample in prop::sample::select(ALL_IDS.to_vec()),
    ) {
        let trimmed = sample.trim_start_matches("sl-viewer.");
        let family = trimmed.split('.').next().unwrap_or("");
        prop_assert!(
            matches!(
                family,
                "app" | "file" | "edit" | "view" | "window" | "help",
            ),
            "menu id {:?} has unknown family {:?}",
            sample,
            family,
        );
    }

    /// Property: each documented family has exactly the right number of
    /// ids (cardinality) — guards against accidental additions / removals.
    #[test]
    fn menu_families_have_expected_cardinality(_unused in 0u8..1u8) {
        let count = |family: &str| -> usize {
            ALL_IDS.iter().filter(|id| id.trim_start_matches("sl-viewer.").starts_with(family)).count()
        };
        prop_assert_eq!(count("app"), 2, "app menu: expected 2 ids");
        prop_assert_eq!(count("file"), 2, "file menu: expected 2 ids");
        prop_assert_eq!(count("edit"), 1, "edit menu: expected 1 id (rest are predefined)");
        prop_assert_eq!(count("view"), 3, "view menu: expected 3 ids");
        prop_assert_eq!(count("help"), 1, "help menu: expected 1 id");
    }

    /// Property: the documented total number of menu ids is 9 (2+2+1+3+1).
    /// Catches silent additions or removals.
    #[test]
    fn menu_total_cardinality_is_documented(_unused in 0u8..1u8) {
        prop_assert_eq!(ALL_IDS.len(), 9, "menu ids should be 9 (2 app + 2 file + 1 edit + 3 view + 1 help)");
    }
}

// ── specific id invariants ───────────────────────────────────────────────

proptest! {
    /// Property: the app menu About id always contains 'about'.
    #[test]
    fn app_about_id_includes_about(_unused in 0u8..1u8) {
        prop_assert!(ID_APP_ABOUT.contains("about"));
        prop_assert!(ID_APP_ABOUT.starts_with("sl-viewer.app."));
    }

    /// Property: the app menu Settings id is distinct from the File
    /// Settings id (different code paths but same label).
    #[test]
    fn app_settings_and_file_settings_ids_are_distinct(_unused in 0u8..1u8) {
        prop_assert_ne!(ID_APP_SETTINGS, ID_FILE_SETTINGS);
        prop_assert!(ID_APP_SETTINGS.starts_with("sl-viewer.app.settings"));
        prop_assert!(ID_FILE_SETTINGS.starts_with("sl-viewer.file.settings"));
    }

    /// Property: the command-palette id matches what the keyboard shortcut
    /// bridge in `app.rs` expects (the accelerator `Cmd+K` / `Ctrl+K`).
    #[test]
    fn command_palette_id_is_stable(_unused in 0u8..1u8) {
        prop_assert_eq!(ID_VIEW_COMMAND_PALETTE, "sl-viewer.view.command-palette");
    }

    /// Property: the help toggle id matches what `?` / Shift+Slash
    /// dispatches in `app.rs`.
    #[test]
    fn help_toggle_id_is_stable(_unused in 0u8..1u8) {
        prop_assert_eq!(ID_HELP_TOGGLE, "sl-viewer.help.toggle");
    }

    /// Property: theme toggle id is wired under view (where the toggle
    /// theme menu item is registered).
    #[test]
    fn theme_toggle_id_is_view_scoped(_unused in 0u8..1u8) {
        prop_assert!(ID_VIEW_TOGGLE_THEME.starts_with("sl-viewer.view."));
        prop_assert!(ID_VIEW_TOGGLE_THEME.contains("theme"));
    }

    /// Property: discover-reload id is wired under file.
    #[test]
    fn file_reload_discovery_id_is_stable(_unused in 0u8..1u8) {
        prop_assert_eq!(ID_FILE_RELOAD_DISCOVERY, "sl-viewer.file.reload-discovery");
    }

    /// Property: find id is wired under edit.
    #[test]
    fn edit_find_id_is_stable(_unused in 0u8..1u8) {
        prop_assert_eq!(ID_EDIT_FIND, "sl-viewer.edit.find");
    }

    /// Property: view reload id matches the Cmd+R accelerator.
    #[test]
    fn view_reload_id_is_stable(_unused in 0u8..1u8) {
        prop_assert_eq!(ID_VIEW_RELOAD, "sl-viewer.view.reload");
    }
}

// ── muda round-trip safety ────────────────────────────────────────────────

proptest! {
    /// Property: every menu id, when parsed as `&str`, matches the
    /// taxonomy by length (since no id is allowed to be empty and all
    /// have the same prefix).
    #[test]
    fn every_id_has_minimum_length(_unused in 0u8..1u8) {
        for id in ALL_IDS {
            prop_assert!(
                id.len() >= "sl-viewer.x.y".len(),
                "menu id {:?} is too short",
                id,
            );
        }
    }
}

// Note: `build_menu()` itself requires the macOS main thread (muda's
// NSMenu only initializes on AppKit main thread). We can't exercise it
// from a proptest runner (which uses worker threads); the integration
// tests in dioxus-desktop exercise the path end-to-end.
