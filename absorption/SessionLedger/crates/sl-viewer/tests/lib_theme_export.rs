// SPDX-License-Identifier: MIT
//! Integration test for the sl-viewer `pub mod theme;` wiring (PR #55 follow-up).
//!
//! Confirms that `sl_viewer::theme::{Theme, ThemeColors}` is reachable
//! from outside the crate — i.e. that `pub mod theme;` was added to
//! `crates/sl-viewer/src/lib.rs`. Without this, downstream consumers
//! (Dioxus desktop/web entry points, sl-eval iframe embed) cannot
//! resolve the Lab-Coat palette tokens.

use sl_viewer::theme::{Theme, ThemeColors};

#[test]
fn theme_module_is_publy_exported() {
    // Reachability check: if `pub mod theme;` regresses, this test
    // fails to compile (E0432: unresolved import `sl_viewer::theme`).
    let _dark = Theme::Dark;
    let _light = Theme::Light;
}

#[test]
fn for_theme_returns_distinct_palettes() {
    let dark = ThemeColors::for_theme(Theme::Dark);
    let light = ThemeColors::for_theme(Theme::Light);
    assert_ne!(dark.bg, light.bg, "dark vs light bg must differ");
    assert_ne!(dark.text, light.text);
}

#[test]
fn lab_coat_palette_lock_in_step4b() {
    // Regression guard: PR #54 swapped amber #f59e0b → #f97316 across
    // the Lab-Coat family. The new darker orange must NOT be present
    // anywhere in this crate's public palette. Pins the lab-coat decision.
    let dark = ThemeColors::for_theme(Theme::Dark);
    let light = ThemeColors::for_theme(Theme::Light);
    for field in ["bg", "surface", "text", "accent", "secondary", "border"] {
        let d = match field {
            "bg" => dark.bg,
            "surface" => dark.surface,
            "text" => dark.text,
            "accent" => dark.accent,
            "secondary" => dark.secondary,
            "border" => dark.border,
            _ => unreachable!(),
        };
        let l = match field {
            "bg" => light.bg,
            "surface" => light.surface,
            "text" => light.text,
            "accent" => light.accent,
            "secondary" => light.secondary,
            "border" => light.border,
            _ => unreachable!(),
        };
        assert_ne!(d.to_ascii_lowercase(), "#f59e0b", "dark.{} regressed to amber #f59e0b", field);
        assert_ne!(l.to_ascii_lowercase(), "#f59e0b", "light.{} regressed to amber #f59e0b", field);
    }
}
