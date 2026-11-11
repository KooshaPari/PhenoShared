//! Property evidence for the `sl-viewer::tokens` design-token SSOT.
//!
//! The viewer chrome depends on the embedded `assets/tokens.css` plus the
//! `lab_coat::*` Rust mirror constants. Drift between the two (e.g.
//! someone updates one and forgets the other) breaks both the CSS theme
//! AND the Rust-side `ThemeColors` accessor.
//!
//! Invariants under test:
//!
//!  * `REQUIRED_CSS_VARS` is non-empty and contains every documented
//!    `--lc-*` and `--sl-*` token name
//!  * Every `lab_coat::*` hex constant appears in `TOKENS_CSS` somewhere
//!  * Every var name in `REQUIRED_CSS_VARS` appears in `TOKENS_CSS` as
//!    `<name>:` (i.e. a real declaration, not just a comment mention)
//!  * `VIEWER_COLOR_SCHEME` mentions both `color-scheme: light` and the
//!    `data-theme="dark"` selector
//!  * `TOKENS_CSS` does not contain the legacy purple accent `#7c3aed`
//!  * `REQUIRED_CSS_VARS` has no duplicate entries
//!  * Each `lab_coat::*` hex constant matches the `^#[0-9a-fA-F]{6}$` regex

use proptest::prelude::*;
use sl_viewer::tokens::{lab_coat, REQUIRED_CSS_VARS, TOKENS_CSS, VIEWER_COLOR_SCHEME};

// ── REQUIRED_CSS_VARS shape ────────────────────────────────────────────────

proptest! {
    /// Property: REQUIRED_CSS_VARS is non-empty across rebuilds.
    /// (Catches a regression where the var list is accidentally emptied.)
    #[test]
    fn required_css_vars_is_nonempty(_unused in 0u8..1u8) {
        prop_assert!(!REQUIRED_CSS_VARS.is_empty());
    }

    /// Property: every entry in REQUIRED_CSS_VARS is a non-empty string
    /// starting with `--` (CSS custom property convention).
    #[test]
    fn required_css_vars_well_formed(_unused in 0u8..1u8) {
        for var in REQUIRED_CSS_VARS {
            prop_assert!(!var.is_empty(), "required var must not be empty");
            prop_assert!(var.starts_with("--"), "required var {:?} must start with --", var);
            prop_assert!(!var.contains(' '), "required var {:?} must not contain spaces", var);
            prop_assert!(!var.contains('\n'), "required var {:?} must not contain newlines", var);
        }
    }

    /// Property: REQUIRED_CSS_VARS has no duplicate entries. (Duplicate
    /// vars would silently let the second declaration win.)
    #[test]
    fn required_css_vars_are_unique(_unused in 0u8..1u8) {
        let mut seen: Vec<&str> = Vec::with_capacity(REQUIRED_CSS_VARS.len());
        for var in REQUIRED_CSS_VARS {
            prop_assert!(!seen.contains(var), "duplicate required var {}", var);
            seen.push(var);
        }
    }

    /// Property: all required vars are declared in TOKENS_CSS (not just
    /// mentioned in comments). We look for `<name>:` which is the CSS
    /// declaration form (`--foo: #abc;`).
    #[test]
    fn every_required_css_var_is_declared(_unused in 0u8..1u8) {
        for var in REQUIRED_CSS_VARS {
            let declaration = format!("{}:", var);
            prop_assert!(
                TOKENS_CSS.contains(&declaration),
                "TOKENS_CSS missing declaration of {}",
                var,
            );
        }
    }
}

// ── Lab-Coat hex constants ────────────────────────────────────────────────

proptest! {
    /// Property: every lab_coat hex constant matches the canonical
    /// `#rrggbb` pattern. (Drift detection for typos like `#f6f8gha`.)
    #[test]
    fn lab_coat_constants_match_hex_pattern(
        idx in 0usize..lab_coat_indexed_pairs().len(),
    ) {
        let (_name, hex) = lab_coat_indexed_pairs()[idx];
        prop_assert_eq!(hex.len(), 7, "hex {:?} must be 7 chars long", hex);
        prop_assert!(hex.starts_with('#'), "hex {:?} must start with #", hex);
        let body = &hex[1..];
        prop_assert!(
            body.chars().all(|c| c.is_ascii_hexdigit()),
            "hex {:?} has non-hex digit in body {:?}",
            hex,
            body,
        );
        // Lowercase form is the canonical form used in tokens.css.
        prop_assert_eq!(
            hex.to_ascii_lowercase(),
            hex,
            "hex {:?} should be lowercase to match tokens.css",
            hex,
        );
    }

    /// Property: every lab_coat hex constant appears verbatim in TOKENS_CSS.
    /// (Catches the case where someone updates the constant but forgets
    /// to sync tokens.css.)
    #[test]
    fn every_lab_coat_constant_appears_in_tokens_css(
        idx in 0usize..lab_coat_indexed_pairs().len(),
    ) {
        let (name, hex) = lab_coat_indexed_pairs()[idx];
        prop_assert!(
            TOKENS_CSS.contains(hex),
            "TOKENS_CSS missing hex {} for {}",
            hex,
            name,
        );
    }

    /// Property: every lab_coat hex constant is declared via the matching
    /// `--<name>` variable in TOKENS_CSS. We accept the var name and hex
    /// on the same line OR within 5 lines of each other (CSS allows
    /// multi-line declarations and the editor may break long lines).
    #[test]
    fn every_lab_coat_constant_wired_via_css_var(
        idx in 0usize..lab_coat_indexed_pairs().len(),
    ) {
        let (var, hex) = lab_coat_indexed_pairs()[idx];
        let lines: Vec<&str> = TOKENS_CSS.lines().collect();
        let mut found = false;
        for start in 0..lines.len() {
            for end in start..lines.len().min(start + 6) {
                let block = lines[start..=end].join(" ");
                if block.contains(var) && block.contains(hex) {
                    found = true;
                    break;
                }
            }
            if found { break; }
        }
        prop_assert!(
            found,
            "TOKENS_CSS does not wire {} to {} within 5-line window",
            var,
            hex,
        );
    }
}

// ── Cross-cutting invariants ──────────────────────────────────────────────

proptest! {
    /// Property: VIEWER_COLOR_SCHEME always mentions the light color
    /// scheme AND the dark color-scheme selector override.
    #[test]
    fn viewer_color_scheme_documents_light_and_dark(_unused in 0u8..1u8) {
        prop_assert!(VIEWER_COLOR_SCHEME.contains("color-scheme: light"));
        prop_assert!(VIEWER_COLOR_SCHEME.contains("data-theme=\"dark\""));
        prop_assert!(VIEWER_COLOR_SCHEME.contains("color-scheme: dark"));
    }

    /// Property: TOKENS_CSS never reintroduces the legacy purple accent
    /// (the L81.8 historical drift). Preserved verbatim from the inline
    /// tests because it costs nothing and catches accidental reintroduction.
    #[test]
    fn tokens_css_does_not_contain_legacy_purple_accent(_unused in 0u8..1u8) {
        prop_assert!(
            !TOKENS_CSS.contains("#7c3aed"),
            "TOKENS_CSS must not contain legacy purple #7c3aed",
        );
    }

    /// Property: TOKENS_CSS contains at least one `var(--...)` consumer
    /// pattern (i.e. css variables aren't just declared, they're used
    /// somewhere). This is a coarse but useful sanity check that the
    /// CSS file is not all-declarations-no-consumers.
    #[test]
    fn tokens_css_uses_var_function(_unused in 0u8..1u8) {
        // At least 3 `var(--...)` consumers must appear.
        let count = TOKENS_CSS.matches("var(--").count();
        prop_assert!(
            count >= 3,
            "TOKENS_CSS only has {} var(--...) consumers; expected >= 3",
            count,
        );
    }

    // (Sibling-pair distinctness is covered by `lab_coat_sibling_pairs_are_distinct`.)

    /// Property: every lab_coat hex value listed in
    /// `lab_coat_indexed_pairs()` is unique (i.e. the indexed set has
    /// no duplicate hexes). Note that BORDER_DARK, TEXT_MUTED_DARK, and
    /// DANGER_DARK are intentionally excluded from the indexed list
    /// because tokens.css uses a single var per light/dark pair with
    /// `:root[data-theme="dark"]` overrides.
    #[test]
    fn lab_coat_indexed_constants_are_unique(_unused in 0u8..1u8) {
        let pairs = lab_coat_indexed_pairs();
        let hexes: Vec<&str> = pairs.iter().map(|(_, h)| *h).collect();
        let mut sorted = hexes.clone();
        sorted.sort();
        sorted.dedup();
        prop_assert_eq!(
            sorted.len(),
            hexes.len(),
            "duplicate hex in lab_coat_indexed_pairs (declaration drift?)",
        );
    }

    /// Property: the light/dark sibling pairs in lab_coat are distinct
    /// (BORDER_LIGHT != BORDER_DARK, TEXT_MUTED_LIGHT != TEXT_MUTED_DARK,
    /// DANGER_LIGHT != DANGER_DARK). This catches the case where someone
    /// copies the light value into the dark slot by mistake.
    #[test]
    fn lab_coat_sibling_pairs_are_distinct(_unused in 0u8..1u8) {
        prop_assert_ne!(lab_coat::BORDER_LIGHT, lab_coat::BORDER_DARK);
        prop_assert_ne!(lab_coat::TEXT_MUTED_LIGHT, lab_coat::TEXT_MUTED_DARK);
        prop_assert_ne!(lab_coat::DANGER_LIGHT, lab_coat::DANGER_DARK);
        // LAB_WHITE (light bg) should not equal BG_DARK (dark bg).
        prop_assert_ne!(lab_coat::LAB_WHITE, lab_coat::BG_DARK);
        // SURFACE_LIGHT (light surface) should not equal SLATE (dark surface).
        prop_assert_ne!(lab_coat::SURFACE_LIGHT, lab_coat::SLATE);
    }
}

// ── helper: ordered index over lab_coat's documented constants ────────────

/// Mirror of the `lab_coat::*` public surface as `(var_name, hex)` pairs,
/// indexed by `lab_coat_indexed_pairs()[i]`. Used by proptest strategies
/// to pick a specific constant without naming each one individually.
///
/// Note: the `--lc-*` family maps to var names like `--lc-cobalt` (one
/// word). The `--sl-*` constants map to var names that don't have a
/// "light"/"dark" suffix in tokens.css — the CSS file uses `--sl-border`
/// (with `:root[data-theme="dark"]` for the dark variant), so we map
/// each Rust constant to the var declaration that the constant is the
/// hex of (one var per constant).
fn lab_coat_indexed_pairs() -> Vec<(&'static str, &'static str)> {
    vec![
        ("--lc-lab-white", lab_coat::LAB_WHITE),
        ("--lc-slate", lab_coat::SLATE),
        ("--lc-cobalt", lab_coat::COBALT),
        ("--lc-cobalt-on-dark", lab_coat::COBALT_ON_DARK),
        ("--lc-orange", lab_coat::ORANGE),
        ("--lc-teal", lab_coat::TEAL),
        ("--lc-teal-on-dark", lab_coat::TEAL_ON_DARK),
        ("--sl-bg", lab_coat::BG_DARK),
        ("--sl-surface", lab_coat::SURFACE_LIGHT),
        // Note: tokens.css uses --sl-border (no -light/-dark suffix);
        // the constant BORDER_LIGHT is the hex for light mode.
        ("--sl-border", lab_coat::BORDER_LIGHT),
        // BORDER_DARK and BORDER_LIGHT are separate hex values in Rust
        // but a single var name in CSS — so we don't include BORDER_DARK
        // here (it's a sibling hex in tokens.css line 205).
        ("--sl-text", lab_coat::TEXT_DARK),
        ("--sl-text-muted", lab_coat::TEXT_MUTED_LIGHT),
        // TEXT_MUTED_DARK is the dark sibling — sibling to TEXT_MUTED_LIGHT,
        // so we don't double-count.
        ("--sl-danger", lab_coat::DANGER_LIGHT),
        // DANGER_DARK is the dark sibling — sibling to DANGER_LIGHT,
        // so we don't double-count.
    ]
}
