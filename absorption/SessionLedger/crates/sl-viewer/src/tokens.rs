//! Viewer design-token single source of truth (C09 L81.8).
//!
//! **CSS SSOT:** repo-root [`assets/tokens.css`](../../../assets/tokens.css)
//! (Lab-Coat `--lc-*` + viewer `--sl-*` aliases).
//!
//! **Rust mirror:** [`lab_coat`] constants below — consumed by
//! [`crate::theme::ThemeColors`] so Rust chrome does not invent ad-hoc hex.
//!
//! The viewer `<style>` block embeds [`TOKENS_CSS`] and must not re-declare
//! `--sl-accent` / Lab-Coat brand hexes inline.

/// Embedded Lab-Coat / viewer theme contract from `assets/tokens.css`.
pub const TOKENS_CSS: &str = include_str!("../../../assets/tokens.css");

/// Color-scheme only; semantic `--sl-*` tokens come from [`TOKENS_CSS`].
pub const VIEWER_COLOR_SCHEME: &str = r#"
:root { color-scheme: light; }
:root[data-theme="dark"] { color-scheme: dark; }
"#;

/// Lab-Coat hex constants mirrored from `assets/tokens.css`.
pub mod lab_coat {
    /// `--lc-lab-white`
    pub const LAB_WHITE: &str = "#f6f8fa";
    /// `--lc-slate`
    pub const SLATE: &str = "#1f2937";
    /// `--lc-cobalt` (light / solid fills)
    pub const COBALT: &str = "#2563eb";
    /// `--lc-cobalt-on-dark` (AA text/chrome on slate)
    pub const COBALT_ON_DARK: &str = "#93c5fd";
    /// `--lc-orange`
    pub const ORANGE: &str = "#f97316";
    /// `--lc-teal`
    pub const TEAL: &str = "#14b8a6";
    /// `--lc-teal-on-dark`
    pub const TEAL_ON_DARK: &str = "#2dd4bf";

    /// Viewer `--sl-bg` dark canvas (`:root[data-theme="dark"]`).
    pub const BG_DARK: &str = "#111827";
    /// Viewer `--sl-surface` light.
    pub const SURFACE_LIGHT: &str = "#ffffff";
    /// Viewer `--sl-border` light / dark.
    pub const BORDER_LIGHT: &str = "#d8dee8";
    pub const BORDER_DARK: &str = "#374151";
    /// Viewer `--sl-text` dark mode.
    pub const TEXT_DARK: &str = "#f3f4f6";
    /// Viewer `--sl-text-muted` light / dark.
    pub const TEXT_MUTED_LIGHT: &str = "#5c5f6e";
    pub const TEXT_MUTED_DARK: &str = "#b6bfcc";
    /// Viewer `--sl-danger` light / dark.
    pub const DANGER_LIGHT: &str = "#b91c1c";
    pub const DANGER_DARK: &str = "#f87171";
}

/// Key CSS custom properties that must exist in [`TOKENS_CSS`].
pub const REQUIRED_CSS_VARS: &[&str] = &[
    "--lc-lab-white",
    "--lc-slate",
    "--lc-cobalt",
    "--lc-cobalt-on-dark",
    "--lc-orange",
    "--lc-teal",
    "--lc-teal-on-dark",
    "--sl-bg",
    "--sl-surface",
    "--sl-accent",
    "--sl-accent-secondary",
    "--sl-accent-warning",
    "--sl-danger",
    "--sl-text",
    "--sl-text-muted",
    "--sl-space-md",
    "--sl-radius-md",
    "--sl-motion-fast",
];

#[cfg(test)]
mod tests {
    use super::lab_coat::*;
    use super::*;
    use crate::theme::ThemeColors;

    #[test]
    fn tokens_css_declares_required_vars() {
        for var in REQUIRED_CSS_VARS {
            assert!(TOKENS_CSS.contains(var), "assets/tokens.css missing required token {var}");
        }
    }

    #[test]
    fn lab_coat_hex_mirror_matches_tokens_css() {
        let pairs = [
            ("--lc-lab-white", LAB_WHITE),
            ("--lc-slate", SLATE),
            ("--lc-cobalt", COBALT),
            ("--lc-cobalt-on-dark", COBALT_ON_DARK),
            ("--lc-orange", ORANGE),
            ("--lc-teal", TEAL),
            ("--lc-teal-on-dark", TEAL_ON_DARK),
        ];
        for (var, hex) in pairs {
            assert!(TOKENS_CSS.contains(hex), "tokens.css missing hex {hex} for {var}");
            // Variable assignment line should mention both name and hex nearby.
            assert!(
                TOKENS_CSS.lines().any(|line| line.contains(var) && line.contains(hex)),
                "tokens.css does not assign {var} to {hex} on the same line"
            );
        }
    }

    #[test]
    fn theme_colors_consume_lab_coat_ssot() {
        let light = ThemeColors::light();
        assert_eq!(light.bg, LAB_WHITE);
        assert_eq!(light.surface, SURFACE_LIGHT);
        assert_eq!(light.text, SLATE);
        assert_eq!(light.accent, COBALT);
        assert_eq!(light.secondary, TEAL);
        assert_eq!(light.border, BORDER_LIGHT);
        assert_eq!(light.focus, COBALT);
        assert_eq!(light.danger, DANGER_LIGHT);
        assert_eq!(light.muted, TEXT_MUTED_LIGHT);

        let dark = ThemeColors::dark();
        assert_eq!(dark.bg, BG_DARK);
        assert_eq!(dark.surface, SLATE);
        assert_eq!(dark.text, TEXT_DARK);
        assert_eq!(dark.accent, COBALT_ON_DARK);
        assert_eq!(dark.secondary, TEAL_ON_DARK);
        assert_eq!(dark.border, BORDER_DARK);
        assert_eq!(dark.focus, COBALT_ON_DARK);
        assert_eq!(dark.danger, DANGER_DARK);
        assert_eq!(dark.muted, TEXT_MUTED_DARK);
    }

    #[test]
    fn no_legacy_purple_accent_in_token_ssot() {
        // Historical L81.8 gap: ThemeColors.dark().accent drifted to #7c3aed.
        assert!(
            !TOKENS_CSS.contains("#7c3aed"),
            "tokens.css must not reintroduce legacy purple accent"
        );
        assert_ne!(ThemeColors::dark().accent, "#7c3aed");
        assert_ne!(ThemeColors::light().accent, "#7c3aed");
    }

    #[test]
    fn app_chrome_embeds_tokens_css_not_ad_hoc_accent() {
        // app.rs must embed TOKENS_CSS and must not re-declare --sl-accent hexes.
        let app_src = include_str!("app.rs");
        assert!(app_src.contains("TOKENS_CSS"), "app.rs must embed crate::tokens::TOKENS_CSS");
        assert!(
            !app_src.contains("--sl-accent: #"),
            "app.rs must not re-declare --sl-accent with ad-hoc hex; use tokens.css"
        );
        assert!(
            !app_src.contains("--sl-bg: #"),
            "app.rs must not re-declare --sl-bg with ad-hoc hex; use tokens.css"
        );
        assert!(
            app_src.contains(".app {{ flex-direction: row; }}"),
            "desktop viewer must place navigation and detail panes side by side"
        );
    }
}
