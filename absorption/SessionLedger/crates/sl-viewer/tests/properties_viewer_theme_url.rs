//! Property evidence for sl-viewer's `theme` and `daemon_url` modules.
//!
//! These tests live in `crates/sl-viewer/tests/` (integration tests) and
//! complement the per-module `#[cfg(test)] mod tests` unit suites that
//! already exist in `src/theme.rs` and `src/daemon_url.rs`. The unit tests
//! pin specific values; the property tests below pin invariants over the
//! full shape of the inputs the modules can receive.
//!
//! `theme` invariants:
//!  * `Theme` JSON round-trip preserves the variant.
//!  * `Theme::default()` is always `System`.
//!  * `ThemeColors::for_theme` is deterministic and total (every variant
//!    yields the same palette as the corresponding `dark()`/`light()`
//!    constructor; `System` falls back to dark, per the design comment).
//!
//! `daemon_url` invariants:
//!  * `daemon_api_url(path)` always yields `<base>/<path>` with exactly
//!    one slash between them, regardless of leading/trailing slashes on
//!    the path argument.
//!  * `daemon_api_url` is idempotent w.r.t. leading slash stripping:
//!    `"foo"` and `"/foo"` produce the same URL.
//!  * `daemon_host_display()` never starts with `http://` or `https://`
//!    and never ends with `/`.
//!
//! proptest is added to `sl-viewer/[dev-dependencies]` (mirroring the
//! workspace root); see PR #425 for the initial wiring.

use proptest::prelude::*;
use sl_viewer::theme::{Theme, ThemeColors};

// ── theme: JSON round-trip + default ────────────────────────────────────────

proptest! {
    /// Property: `Theme` serializes to lowercase JSON and round-trips
    /// back to the same variant. Catches drift in `#[serde(rename_all)]`
    /// or a future addition of a variant whose serde name doesn't match
    /// the lowercase contract documented on the type.
    #[test]
    fn theme_json_round_trip_preserves_variant(theme in prop::sample::select(vec![
        Theme::Light,
        Theme::Dark,
        Theme::System,
    ])) {
        let json = serde_json::to_string(&theme).expect("serialize Theme");
        // Lowercase contract (hand-edited settings.json portability).
        let expected = format!("\"{theme:?}\"").to_lowercase();
        prop_assert_eq!(json.clone(), expected);
        let restored: Theme = serde_json::from_str(&json).expect("deserialize Theme");
        prop_assert_eq!(restored, theme);
    }

    /// Property: `Theme::default()` is always `System`, regardless of
    /// any future variant additions (a regression guard for the
    /// `#[default]` attribute).
    #[test]
    fn theme_default_is_system(_seed in 0u32..1000) {
        prop_assert_eq!(Theme::default(), Theme::System);
    }

    /// Property: `ThemeColors::for_theme` is total and deterministic:
    ///   - `for_theme(Light)` always equals `light()`,
    ///   - `for_theme(Dark)`  always equals `dark()`,
    ///   - `for_theme(System)` always equals `dark()` (design contract).
    ///
    /// This is a tautology on the current impl; it exists so a future
    /// refactor that, say, makes `System` resolve to `light()` cannot
    /// land without the property test catching the contract drift.
    #[test]
    fn theme_colors_for_theme_matches_constructor(theme in prop::sample::select(vec![
        Theme::Light,
        Theme::Dark,
        Theme::System,
    ])) {
        let expected = match theme {
            Theme::Light => ThemeColors::light(),
            Theme::Dark => ThemeColors::dark(),
            // System → dark fallback (no host signal on desktop).
            Theme::System => ThemeColors::dark(),
        };
        prop_assert_eq!(ThemeColors::for_theme(theme), expected);
    }
}

// ── daemon_url: API URL construction invariants ─────────────────────────────

fn api_path_strategy() -> impl Strategy<Value = String> {
    // ASCII-visible, path-shaped (no spaces, no schemes), arbitrary depth
    // up to 4 segments. Bounded so the property runs quickly.
    prop::collection::vec("[a-z0-9_-]{1,16}", 1..5).prop_map(|segs| segs.join("/"))
}

fn path_with_flanking_slashes_strategy() -> impl Strategy<Value = String> {
    (
        0..3usize, // leading slash count
        0..3usize, // trailing slash count
        api_path_strategy(),
    )
        .prop_map(|(lead, trail, body)| {
            format!("{}{}{}", "/".repeat(lead), body, "/".repeat(trail),)
        })
}

proptest! {
    /// Property: `daemon_api_url(path)` is exactly `<base>/<path-without-
    /// leading-slash>`. The base has no trailing slash (trimmed by the
    /// impl), and exactly one slash separates them. Trailing slashes on
    /// `path` are preserved verbatim (the impl only strips leading).
    #[test]
    fn daemon_api_url_is_base_slash_path_with_leading_stripped(
        path in path_with_flanking_slashes_strategy(),
    ) {
        let url = sl_viewer::daemon_url::daemon_api_url(&path);

        let base = sl_viewer::daemon_url::daemon_base_url();
        let base_no_slash = base.trim_end_matches('/');
        let body = path.trim_start_matches('/');

        prop_assert_eq!(
            url,
            format!("{base_no_slash}/{body}"),
        );
    }

    /// Property: `daemon_api_url` is idempotent w.r.t. leading slash
    /// stripping — `"api/x"` and `"/api/x"` produce the same URL.
    #[test]
    fn daemon_api_url_strips_leading_slash(body in api_path_strategy()) {
        let with_slash = sl_viewer::daemon_url::daemon_api_url(&format!("/{body}"));
        let without_slash = sl_viewer::daemon_url::daemon_api_url(&body);
        prop_assert_eq!(with_slash, without_slash);
    }

    /// Property: `daemon_host_display()` never carries an `http(s)://`
    /// scheme and never ends with a trailing slash.
    #[test]
    fn daemon_host_display_strips_scheme_and_trailing_slash(
        _seed in 0u32..16,
    ) {
        let display = sl_viewer::daemon_url::daemon_host_display();
        prop_assert!(
            !display.starts_with("http://"),
            "host display {display} must not start with http://",
        );
        prop_assert!(
            !display.starts_with("https://"),
            "host display {display} must not start with https://",
        );
        prop_assert!(
            !display.ends_with('/'),
            "host display {display} must not end with /",
        );
        // And it must be non-empty — a stripped display of just `""`
        // would be a contract violation.
        prop_assert!(!display.is_empty(), "host display must not be empty");
    }
}
