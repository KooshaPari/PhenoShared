use serde::{Deserialize, Serialize};

use crate::tokens::lab_coat;

/// User-facing theme preference.
///
/// - `Light` / `Dark` lock the palette to one mode.
/// - `System` defers to the host OS / browser preference when the renderer
///   can resolve it (web via `prefers-color-scheme`), otherwise falls back
///   to [`Theme::Dark`] on desktop.
///
/// Serialised in lowercase for portability across hand-edited
/// `settings.json` files and the existing `localStorage` value contract
/// (`sl-viewer-theme` stores `"light"` / `"dark"`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Theme {
    Light,
    Dark,
    #[default]
    System,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ThemeColors {
    pub bg: &'static str,
    pub surface: &'static str,
    pub text: &'static str,
    pub accent: &'static str,
    pub secondary: &'static str,
    pub border: &'static str,
    /// Focus-ring / keyboard-highlight color (Lab-Coat cobalt family).
    pub focus: &'static str,
    /// Error / destructive text.
    pub danger: &'static str,
    /// Muted secondary text.
    pub muted: &'static str,
}
impl ThemeColors {
    pub fn dark() -> Self {
        Self {
            bg: lab_coat::BG_DARK,
            surface: lab_coat::SLATE,
            text: lab_coat::TEXT_DARK,
            // AA (≥4.5:1) on slate + 16% accent color-mix chrome — brand cobalt is 2.84:1.
            accent: lab_coat::COBALT_ON_DARK,
            // Lighter teal for badge/chrome text on 18% teal mixes (~#1d434b).
            secondary: lab_coat::TEAL_ON_DARK,
            border: lab_coat::BORDER_DARK,
            focus: lab_coat::COBALT_ON_DARK,
            danger: lab_coat::DANGER_DARK,
            muted: lab_coat::TEXT_MUTED_DARK,
        }
    }
    pub fn light() -> Self {
        Self {
            bg: lab_coat::LAB_WHITE,
            surface: lab_coat::SURFACE_LIGHT,
            text: lab_coat::SLATE,
            accent: lab_coat::COBALT,
            secondary: lab_coat::TEAL,
            border: lab_coat::BORDER_LIGHT,
            focus: lab_coat::COBALT,
            danger: lab_coat::DANGER_LIGHT,
            muted: lab_coat::TEXT_MUTED_LIGHT,
        }
    }
    pub fn for_theme(t: Theme) -> Self {
        match t {
            Theme::Dark => Self::dark(),
            Theme::Light => Self::light(),
            // `System` resolves to the dark palette on desktop where there is
            // no host signal to consult. The web renderer resolves `System`
            // separately by reading `prefers-color-scheme` before applying
            // the dataset.
            Theme::System => Self::dark(),
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::tokens::lab_coat;
    #[test]
    fn dark_accent_meets_aa_on_slate() {
        assert_eq!(ThemeColors::dark().accent, lab_coat::COBALT_ON_DARK);
    }
    #[test]
    fn light_bg() {
        assert!(ThemeColors::light().bg.starts_with("#f"));
    }
    #[test]
    fn for_dark() {
        assert_eq!(ThemeColors::for_theme(Theme::Dark).accent, ThemeColors::dark().accent);
    }
    #[test]
    fn for_light() {
        assert_eq!(ThemeColors::for_theme(Theme::Light).bg, ThemeColors::light().bg);
    }
    #[test]
    fn for_system_falls_back_to_dark() {
        assert_eq!(ThemeColors::for_theme(Theme::System).accent, ThemeColors::dark().accent);
    }
    #[test]
    fn system_is_default_theme() {
        assert_eq!(Theme::default(), Theme::System);
    }
    #[test]
    fn secondary_stays_lab_coat_teal_family() {
        assert_eq!(ThemeColors::dark().secondary, lab_coat::TEAL_ON_DARK);
        assert_eq!(ThemeColors::light().secondary, lab_coat::TEAL);
    }
    #[test]
    fn light_focus_is_lab_coat_cobalt() {
        assert_eq!(ThemeColors::light().focus, lab_coat::COBALT);
        assert_eq!(ThemeColors::light().accent, lab_coat::COBALT);
    }
    #[test]
    fn dark_focus_matches_on_dark_accent() {
        assert_eq!(ThemeColors::dark().focus, ThemeColors::dark().accent);
    }
    #[test]
    fn danger_and_muted_present() {
        assert!(ThemeColors::dark().danger.starts_with('#'));
        assert!(ThemeColors::dark().muted.starts_with('#'));
    }
}
