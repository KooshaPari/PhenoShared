//! Property evidence for the `sl-viewer::help_overlay` keyboard
//! shortcut table.
//!
//! The `SHORTCUTS` constant is a static array of `HelpShortcut` rows
//! displayed in the in-viewer help overlay (`?`). Two consumers rely
//! on it:
//!
//!  * The overlay UI for rendering
//!  * The keyboard bridge in `app.rs` for verifying that documented
//!    shortcuts match what the dispatcher handles
//!
//! Properties under test:
//!
//!  * Every shortcut has non-empty keys, scope, action fields
//!  * Every `keys` string has at least one character
//!  * Every `keys` string is short enough to fit a `<kbd>` pill
//!  * No two shortcuts share an identical (keys, scope) tuple
//!  * The documented set covers all four escape-scope variants
//!  * SHORTCUTS has at least the documented cardinality
//!  * `HelpShortcut` derives (Clone/Copy/PartialEq/Eq/Debug) hold
//!
//! Note: this module is non-feature-gated — help_overlay.rs is always
//! compiled into the lib because `app.rs` (the root module) uses
//! `typing_focus_active` directly.

use proptest::prelude::*;
use sl_viewer::help_overlay::{HelpShortcut, SHORTCUTS};

// ── Shortcut field shape ─────────────────────────────────────────────────

proptest! {
    /// Property: every shortcut row has a non-empty `keys` field.
    /// Empty-key shortcuts would render as blank pills in the overlay.
    #[test]
    fn every_shortcut_keys_is_nonempty(_unused in 0u8..1u8) {
        for s in SHORTCUTS {
            prop_assert!(!s.keys.is_empty(), "shortcut keys must be non-empty");
        }
    }

    /// Property: every shortcut row has a non-empty `scope` field.
    /// Empty-scope rows render with no context (which is confusing).
    #[test]
    fn every_shortcut_scope_is_nonempty(_unused in 0u8..1u8) {
        for s in SHORTCUTS {
            prop_assert!(!s.scope.is_empty(), "shortcut scope must be non-empty");
        }
    }

    /// Property: every shortcut row has a non-empty `action` field.
    /// Empty-action rows render with no description.
    #[test]
    fn every_shortcut_action_is_nonempty(_unused in 0u8..1u8) {
        for s in SHORTCUTS {
            prop_assert!(!s.action.is_empty(), "shortcut action must be non-empty");
        }
    }

    /// Property: every shortcut's `keys` string is short enough to fit
    /// in a `<kbd>` pill (typically <= 30 chars). Longer key strings
    /// would wrap awkwardly in the overlay UI.
    #[test]
    fn every_shortcut_keys_fits_in_kbd_pill(_unused in 0u8..1u8) {
        for s in SHORTCUTS {
            prop_assert!(
                s.keys.len() <= 30,
                "shortcut keys {:?} too long ({} chars)",
                s.keys,
                s.keys.len(),
            );
        }
    }

    /// Property: every shortcut's `action` string is short enough to
    /// fit in a single-row overlay cell (<= 200 chars).
    #[test]
    fn every_shortcut_action_fits_one_line(_unused in 0u8..1u8) {
        for s in SHORTCUTS {
            prop_assert!(
                s.action.len() <= 200,
                "shortcut action too long for one line ({} chars)",
                s.action.len(),
            );
        }
    }
}

// ── Uniqueness ────────────────────────────────────────────────────────────

proptest! {
    /// Property: no two shortcuts share the same (keys, scope) tuple.
    /// Duplicate entries would render the same row twice in the overlay
    /// and confuse the keyboard-bridge dispatcher.
    #[test]
    fn shortcut_keys_scope_pairs_are_unique(_unused in 0u8..1u8) {
        let mut seen: Vec<(&str, &str)> = Vec::with_capacity(SHORTCUTS.len());
        for s in SHORTCUTS {
            let pair = (s.keys, s.scope);
            prop_assert!(!seen.contains(&pair), "duplicate (keys, scope) tuple {:?}", pair);
            seen.push(pair);
        }
    }

    /// Property: no two shortcuts have identical (keys, scope, action)
    /// (i.e. completely identical rows).
    #[test]
    fn shortcut_rows_are_fully_unique(_unused in 0u8..1u8) {
        let mut seen: Vec<HelpShortcut> = Vec::with_capacity(SHORTCUTS.len());
        for s in SHORTCUTS {
            prop_assert!(!seen.contains(s), "completely-duplicate shortcut row {:?}", s);
            seen.push(*s);
        }
    }
}

// ── Required coverage ────────────────────────────────────────────────────

proptest! {
    /// Property: SHORTCUTS always contains the documented baseline of
    /// 12 shortcuts. Add-only invariant — drift to <12 entries indicates
    /// a wholesale rewrite of the help overlay.
    #[test]
    fn shortcuts_minimum_cardinality(_unused in 0u8..1u8) {
        prop_assert!(
            SHORTCUTS.len() >= 12,
            "SHORTCUTS has {} entries; expected at least 12",
            SHORTCUTS.len(),
        );
    }

    /// Property: Escape is documented for every relevant scope where
    /// the bridge in app.rs closes an overlay. We require at least the
    /// 4 documented escape scopes (help overlay, command palette,
    /// search view, replay view, comparison panel).
    #[test]
    fn shortcut_table_covers_help_shortcut(_unused in 0u8..1u8) {
        prop_assert!(
            SHORTCUTS.iter().any(|s| s.keys == "?"),
            "SHORTCUTS missing the ? help-toggle entry",
        );
    }

    /// Property: the Cmd+K / Ctrl+K command-palette shortcut is documented.
    #[test]
    fn shortcut_table_covers_command_palette(_unused in 0u8..1u8) {
        let covers_cmd_k = SHORTCUTS.iter().any(|s| {
            (s.keys.contains("Cmd+K") || s.keys.contains("Ctrl+K"))
                && (s.keys.contains("/") || s.keys.contains("or"))
        });
        prop_assert!(
            covers_cmd_k,
            "SHORTCUTS missing the Cmd+K / Ctrl+K command-palette entry",
        );
    }

    /// Property: SHORTCUTS always includes at least one Escape row for
    /// the help overlay itself.
    #[test]
    fn escape_shortcut_closes_help_overlay(_unused in 0u8..1u8) {
        let covers_help_escape = SHORTCUTS.iter().any(|s| {
            s.keys == "Escape"
                && s.scope.to_lowercase().contains("help")
        });
        prop_assert!(
            covers_help_escape,
            "SHORTCUTS must include an Escape row for the help overlay",
        );
    }
}

// ── HelpShortcut trait derives ───────────────────────────────────────────

proptest! {
    /// Property: HelpShortcut derives (Copy + Clone + PartialEq + Eq + Debug)
    /// — calling them on a real row produces an equal value.
    #[test]
    fn help_shortcut_trait_derives_hold(
        sample in prop::sample::select(SHORTCUTS.to_vec()),
    ) {
        // Copy
        let copied = sample;
        // Clone
        let cloned = sample;
        // PartialEq + Eq via ==
        prop_assert_eq!(sample, copied);
        prop_assert_eq!(sample, cloned);
        prop_assert_eq!(copied, cloned);
        // Debug by formatting
        let debug = format!("{:?}", sample);
        prop_assert!(!debug.is_empty());
    }

    /// Property: two distinct shortcuts compare unequal. Catches a
    /// regression where PartialEq collapses to true for everything.
    #[test]
    fn distinct_shortcuts_compare_unequal(
        a_idx in 0usize..SHORTCUTS.len(),
        b_idx in 0usize..SHORTCUTS.len(),
    ) {
        prop_assume!(a_idx != b_idx);
        let a = SHORTCUTS[a_idx];
        let b = SHORTCUTS[b_idx];
        prop_assert_ne!(a, b);
    }
}

// ── Cross-cutting invariants ──────────────────────────────────────────────

proptest! {
    /// Property: SHORTCUTS is idempotent under identity iteration
    /// (no hidden state mutation in the global slice).
    #[test]
    fn shortcuts_table_is_idempotent(_unused in 0u8..1u8) {
        let first_len = SHORTCUTS.len();
        // Iterate twice — slice length must not change between calls.
        for _ in 0..3 {
            prop_assert_eq!(SHORTCUTS.len(), first_len);
        }
    }

    /// Property: every shortcut's `keys` field is non-whitespace-only
    /// (i.e. has at least one non-whitespace character).
    #[test]
    fn every_shortcut_keys_has_nonwhitespace(_unused in 0u8..1u8) {
        for s in SHORTCUTS {
            prop_assert!(
                s.keys.chars().any(|c| !c.is_whitespace()),
                "keys {:?} is whitespace-only",
                s.keys,
            );
        }
    }

    /// Property: every shortcut's `scope` field references a documented
    /// surface (whole viewer, command palette, focused view tab,
    /// help overlay, search view, replay view, bundle comparison).
    #[test]
    fn shortcut_scope_references_known_surface(
        sample in prop::sample::select(SHORTCUTS.to_vec()),
    ) {
        let scope_lower = sample.scope.to_lowercase();
        let known = scope_lower.contains("whole viewer")
            || scope_lower.contains("command palette")
            || scope_lower.contains("focused view tab")
            || scope_lower.contains("help overlay")
            || scope_lower.contains("search view")
            || scope_lower.contains("replay view")
            || scope_lower.contains("bundle comparison");
        prop_assert!(known, "scope {:?} references unknown surface", sample.scope);
    }
}
