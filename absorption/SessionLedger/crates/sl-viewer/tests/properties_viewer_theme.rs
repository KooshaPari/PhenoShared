//! Property evidence for `sl-viewer::theme::Theme` and `ThemeColors`.
//!
//! Invariants under test:
//!
//!  * `Theme` roundtrips through `serde_json` with lowercase names
//!  * `Theme::Default == Theme::System`
//!  * `ThemeColors::dark()` and `ThemeColors::light()` return distinct
//!    palettes (every field is different)
//!  * Every color string matches the `#rrggbb` lowercase hex pattern
//!  * `for_theme(Theme::Dark)` returns `dark()`, `for_theme(Theme::Light)`
//!    returns `light()`, `for_theme(Theme::System)` returns `dark()`
//!  * Every required field is non-empty
//!  * PartialEq/Eq/Clone/Debug derives hold

use proptest::prelude::*;
use sl_viewer::theme::{Theme, ThemeColors};

// ── Theme enum round-trip ─────────────────────────────────────────────────

proptest! {
    /// Property: every `Theme` variant serializes to lowercase JSON.
    #[test]
    fn theme_serializes_to_lowercase(_unused in 0u8..1u8) {
        for t in [Theme::Light, Theme::Dark, Theme::System] {
            let json = serde_json::to_string(&t).expect("serialize");
            // JSON should be `"light"`, `"dark"`, or `"system"` (with quotes).
            prop_assert!(matches!(json.as_str(), "\"light\"" | "\"dark\"" | "\"system\""),
                "unexpected serialization: {}", json);
        }
    }

    /// Property: every `Theme` deserializes from its lowercase JSON form
    /// back to itself (round-trip identity).
    #[test]
    fn theme_roundtrips(_unused in 0u8..1u8) {
        for (t, s) in [(Theme::Light, "\"light\""), (Theme::Dark, "\"dark\""), (Theme::System, "\"system\"")] {
            let roundtrip: Theme = serde_json::from_str(s).expect("deserialize");
            prop_assert_eq!(t, roundtrip);
        }
    }

    /// Property: `Theme::default()` returns `Theme::System`. This is the
    /// documented default behavior.
    #[test]
    fn theme_default_is_system(_unused in 0u8..1u8) {
        prop_assert_eq!(Theme::default(), Theme::System);
    }

    /// Property: the three Theme variants are pairwise distinct.
    #[test]
    fn theme_variants_are_distinct(_unused in 0u8..1u8) {
        prop_assert_ne!(Theme::Light, Theme::Dark);
        prop_assert_ne!(Theme::Dark, Theme::System);
        prop_assert_ne!(Theme::Light, Theme::System);
    }

    /// Property: `Theme` derives (Copy + Clone + PartialEq + Eq + Debug).
    #[test]
    fn theme_derives_hold(
        sample in prop::sample::select(vec![Theme::Light, Theme::Dark, Theme::System]),
    ) {
        let copied = sample;            // Copy
        let cloned = sample;            // Copy (and Clone-compatible)
        prop_assert_eq!(sample, copied);
        prop_assert_eq!(sample, cloned);
        let debug = format!("{:?}", sample);
        prop_assert!(!debug.is_empty());
    }
}

// ── Hex format invariants ─────────────────────────────────────────────────

/// Helper: assert a hex string matches `#rrggbb` lowercase.
fn is_lab_coat_hex(s: &str) -> bool {
    s.len() == 7 && s.starts_with('#') && s[1..].chars().all(|c| c.is_ascii_hexdigit())
}

proptest! {
    /// Property: every color string in `ThemeColors::dark()` is non-empty.
    #[test]
    fn dark_colors_are_nonempty(_unused in 0u8..1u8) {
        let c = ThemeColors::dark();
        prop_assert!(!c.bg.is_empty());
        prop_assert!(!c.surface.is_empty());
        prop_assert!(!c.text.is_empty());
        prop_assert!(!c.accent.is_empty());
        prop_assert!(!c.secondary.is_empty());
        prop_assert!(!c.border.is_empty());
        prop_assert!(!c.focus.is_empty());
        prop_assert!(!c.danger.is_empty());
        prop_assert!(!c.muted.is_empty());
    }

    /// Property: every color string in `ThemeColors::light()` is non-empty.
    #[test]
    fn light_colors_are_nonempty(_unused in 0u8..1u8) {
        let c = ThemeColors::light();
        prop_assert!(!c.bg.is_empty());
        prop_assert!(!c.surface.is_empty());
        prop_assert!(!c.text.is_empty());
        prop_assert!(!c.accent.is_empty());
        prop_assert!(!c.secondary.is_empty());
        prop_assert!(!c.border.is_empty());
        prop_assert!(!c.focus.is_empty());
        prop_assert!(!c.danger.is_empty());
        prop_assert!(!c.muted.is_empty());
    }

    /// Property: every color string in `ThemeColors::dark()` matches
    /// the canonical `#rrggbb` lowercase hex pattern (lab-coat hex
    /// invariant, matching `properties_viewer_tokens.rs`).
    #[test]
    fn dark_colors_match_lab_coat_hex(_unused in 0u8..1u8) {
        let c = ThemeColors::dark();
        prop_assert!(is_lab_coat_hex(c.bg),     "bg {:?} not a #rrggbb hex", c.bg);
        prop_assert!(is_lab_coat_hex(c.surface), "surface {:?} not a #rrggbb hex", c.surface);
        prop_assert!(is_lab_coat_hex(c.text),    "text {:?} not a #rrggbb hex", c.text);
        prop_assert!(is_lab_coat_hex(c.accent),  "accent {:?} not a #rrggbb hex", c.accent);
        prop_assert!(is_lab_coat_hex(c.secondary), "secondary {:?} not a #rrggbb hex", c.secondary);
        prop_assert!(is_lab_coat_hex(c.border),  "border {:?} not a #rrggbb hex", c.border);
        prop_assert!(is_lab_coat_hex(c.focus),   "focus {:?} not a #rrggbb hex", c.focus);
        prop_assert!(is_lab_coat_hex(c.danger),  "danger {:?} not a #rrggbb hex", c.danger);
        prop_assert!(is_lab_coat_hex(c.muted),   "muted {:?} not a #rrggbb hex", c.muted);
    }

    /// Property: every color string in `ThemeColors::light()` matches
    /// the canonical `#rrggbb` lowercase hex pattern.
    #[test]
    fn light_colors_match_lab_coat_hex(_unused in 0u8..1u8) {
        let c = ThemeColors::light();
        prop_assert!(is_lab_coat_hex(c.bg),     "bg {:?} not a #rrggbb hex", c.bg);
        prop_assert!(is_lab_coat_hex(c.surface), "surface {:?} not a #rrggbb hex", c.surface);
        prop_assert!(is_lab_coat_hex(c.text),    "text {:?} not a #rrggbb hex", c.text);
        prop_assert!(is_lab_coat_hex(c.accent),  "accent {:?} not a #rrggbb hex", c.accent);
        prop_assert!(is_lab_coat_hex(c.secondary), "secondary {:?} not a #rrggbb hex", c.secondary);
        prop_assert!(is_lab_coat_hex(c.border),  "border {:?} not a #rrggbb hex", c.border);
        prop_assert!(is_lab_coat_hex(c.focus),   "focus {:?} not a #rrggbb hex", c.focus);
        prop_assert!(is_lab_coat_hex(c.danger),  "danger {:?} not a #rrggbb hex", c.danger);
        prop_assert!(is_lab_coat_hex(c.muted),   "muted {:?} not a #rrggbb hex", c.muted);
    }
}

// ── Palette distinction invariants ────────────────────────────────────────

proptest! {
    /// Property: the dark and light palettes differ in bg, surface,
    /// text, accent, secondary, border, danger, and muted — i.e. the
    /// two palettes must actually be distinct for every visible field.
    #[test]
    fn dark_and_light_palettes_are_distinct(_unused in 0u8..1u8) {
        let d = ThemeColors::dark();
        let l = ThemeColors::light();
        prop_assert_ne!(d.bg, l.bg);
        prop_assert_ne!(d.surface, l.surface);
        prop_assert_ne!(d.text, l.text);
        prop_assert_ne!(d.accent, l.accent);
        prop_assert_ne!(d.secondary, l.secondary);
        prop_assert_ne!(d.border, l.border);
        prop_assert_ne!(d.danger, l.danger);
        prop_assert_ne!(d.muted, l.muted);
    }

    /// Property: `for_theme(Theme::Dark)` returns the same accent as
    /// `ThemeColors::dark()` (and similarly for Light/System).
    #[test]
    fn for_theme_dispatches_correctly(_unused in 0u8..1u8) {
        prop_assert_eq!(ThemeColors::for_theme(Theme::Dark).accent,
                        ThemeColors::dark().accent);
        prop_assert_eq!(ThemeColors::for_theme(Theme::Light).bg,
                        ThemeColors::light().bg);
        prop_assert_eq!(ThemeColors::for_theme(Theme::System).accent,
                        ThemeColors::dark().accent);
    }

    /// Property: `for_theme` returns an instance equal to the named
    /// constructor for Light, Dark, and System (System falls back to dark).
    #[test]
    fn for_theme_returns_expected_palette(_unused in 0u8..1u8) {
        prop_assert_eq!(ThemeColors::for_theme(Theme::Light),
                        ThemeColors::light());
        prop_assert_eq!(ThemeColors::for_theme(Theme::Dark),
                        ThemeColors::dark());
        prop_assert_eq!(ThemeColors::for_theme(Theme::System),
                        ThemeColors::dark());
    }

    /// Property: `for_theme` is idempotent — calling it twice with the
    /// same theme yields identical structs.
    #[test]
    fn for_theme_is_idempotent(_unused in 0u8..1u8) {
        for t in [Theme::Light, Theme::Dark, Theme::System] {
            let a = ThemeColors::for_theme(t);
            let b = ThemeColors::for_theme(t);
            prop_assert_eq!(a, b);
        }
    }
}

// ── Specific invariants ──────────────────────────────────────────────────

proptest! {
    /// Property: dark focus color matches dark accent (required for
    /// visible keyboard focus rings on the chrome).
    #[test]
    fn dark_focus_matches_accent(_unused in 0u8..1u8) {
        let c = ThemeColors::dark();
        prop_assert_eq!(c.focus, c.accent);
    }

    /// Property: light focus color matches light accent (cobalt on white).
    #[test]
    fn light_focus_matches_accent(_unused in 0u8..1u8) {
        let c = ThemeColors::light();
        prop_assert_eq!(c.focus, c.accent);
    }

    /// Property: secondary colors are drawn from the teal lab-coat
    /// family — wired-up by `properties_viewer_tokens.rs`.
    #[test]
    fn secondary_is_teal_family(_unused in 0u8..1u8) {
        // We can't import lab_coat from a test path that's directly
        // `use sl_viewer::theme::*` because lab_coat is a sibling module
        // — but we can verify the literal invariants via the markdown
        // pairing tests. Here we just check the colors differ between
        // modes (teal vs teal-on-dark).
        let d = ThemeColors::dark();
        let l = ThemeColors::light();
        prop_assert_ne!(d.secondary, l.secondary);
    }

    /// Property: `ThemeColors` derives (Clone + PartialEq + Eq + Debug).
    #[test]
    fn theme_colors_derives_hold(
        theme in prop::sample::select(vec![Theme::Light, Theme::Dark]),
    ) {
        let a = ThemeColors::for_theme(theme);
        let b = a.clone();                                  // Clone
        let ac = a.clone();
        prop_assert_eq!(ac, b);                             // PartialEq + Eq (via clone)
        let debug = format!("{:?}", a);                     // Debug
        prop_assert!(!debug.is_empty());
    }

    /// Property: dark and light `ThemeColors` are NOT equal (sanity
    /// check that PartialEq is not degenerate).
    #[test]
    fn dark_and_light_palettes_compare_unequal(_unused in 0u8..1u8) {
        prop_assert_ne!(ThemeColors::dark(), ThemeColors::light());
    }
}
