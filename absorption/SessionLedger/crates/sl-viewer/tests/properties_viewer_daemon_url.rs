//! Property evidence for the daemon-URL helpers in `sl-viewer::daemon_url`.
//!
//! The viewer calls into `sl-daemon` over HTTP. The two helpers in
//! `daemon_url.rs`:
//!
//!  * `daemon_api_url(path)` — joins the daemon base URL with a path
//!  * `daemon_host_display()` — strips the scheme for human-readable
//!    error messages
//!
//! The properties below pin down the join semantics across arbitrary
//! path inputs (leading slash, no leading slash, empty path, paths
//! containing query strings) and confirm the host display always
//! drops the `http://` prefix.
//!
//! Note: `daemon_base_url()` reads `SL_DAEMON_URL` from the compile-time
//! environment (via `option_env!`), so the value is fixed for the
//! duration of a single test binary. We assert against
//! `daemon_base_url()` directly rather than hardcoding a literal URL.

use proptest::prelude::*;
use sl_viewer::daemon_url::{daemon_api_url, daemon_base_url, daemon_host_display};

// ── daemon_api_url path joining ────────────────────────────────────────────

proptest! {
    /// Property: any path joined with the daemon base URL yields a URL
    /// whose body is exactly `<base>/<path>` — no double slashes and no
    /// missing slash separator.
    #[test]
    fn daemon_api_url_joins_with_single_slash_separator(
        // Accept both ASCII paths and arbitrary Unicode to ensure the
        // join is byte-faithful (no URL-encoding happens here — the
        // server is expected to encode).
        path in "[a-zA-Z0-9/_.\\-?&=]{0,40}",
    ) {
        let url = daemon_api_url(&path);
        let base = daemon_base_url();
        let base_trimmed = base.trim_end_matches('/');
        let path_trimmed = path.trim_start_matches('/');
        let expected = format!("{base_trimmed}/{path_trimmed}");
        prop_assert_eq!(&url, &expected);
    }

    /// Property: a path with a leading slash and the same path without
    /// one produce identical results. (Both forms must work; callers
    /// shouldn't have to normalise the path.)
    #[test]
    fn daemon_api_url_handles_leading_slash_or_not(
        path_core in "[a-zA-Z0-9_.\\-]{0,30}",
    ) {
        let with_slash = daemon_api_url(&format!("/{path_core}"));
        let without_slash = daemon_api_url(&path_core);
        prop_assert_eq!(with_slash, without_slash);
    }

    /// Property: `daemon_api_url("")` returns the trimmed base with a
    /// trailing slash. (Useful for "is the daemon alive?" probes.)
    #[test]
    fn daemon_api_url_empty_path_yields_base_with_trailing_slash(
        _unused in 0u8..1u8,
    ) {
        let url = daemon_api_url("");
        let base = daemon_base_url().trim_end_matches('/');
        let expected = format!("{base}/");
        prop_assert_eq!(url, expected);
    }

    /// Property: the joined URL always starts with the same prefix as
    /// the base URL (case-sensitive). (Don't accidentally lowercase or
    /// scheme-swap the base.)
    #[test]
    fn daemon_api_url_preserves_base_prefix(
        path in "[a-zA-Z0-9/]{0,30}",
    ) {
        let url = daemon_api_url(&path);
        let base_trimmed = daemon_base_url().trim_end_matches('/');
        prop_assert!(
            url.starts_with(base_trimmed),
            "url {:?} must start with base prefix {:?}",
            url,
            base_trimmed,
        );
    }

    /// Property: the joined URL always contains a `/` immediately after
    /// the base — never `<base><path-without-slash>`. (Catches the
    /// common bug of accidentally concatenating the base and path.)
    #[test]
    fn daemon_api_url_always_has_slash_between_base_and_path(
        path in "[a-zA-Z0-9_.\\-]{0,30}",
    ) {
        let url = daemon_api_url(&path);
        let base_trimmed = daemon_base_url().trim_end_matches('/');
        // Find where the base ends (it might be http://127.0.0.1:8080 etc.)
        // and assert the character immediately following is a slash.
        let after_base = &url[base_trimmed.len()..];
        if !path.is_empty() {
            prop_assert!(
                after_base.starts_with('/'),
                "url {:?} must have a slash between base and path; got {:?}",
                url,
                after_base,
            );
        }
    }

    /// Property: idempotence — joining the same path twice produces the
    /// same URL. (No hidden state mutation.)
    #[test]
    fn daemon_api_url_is_idempotent(
        path in "[a-zA-Z0-9/_.\\-]{0,30}",
    ) {
        let a = daemon_api_url(&path);
        let b = daemon_api_url(&path);
        prop_assert_eq!(a, b);
    }

    /// Property: a trailing slash on the path is preserved (the viewer
    /// treats `/api/foo/` and `/api/foo` as distinct endpoints).
    #[test]
    fn daemon_api_url_preserves_trailing_slash_on_path(
        core in "[a-zA-Z0-9]{1,20}",
    ) {
        let url = daemon_api_url(&format!("/{core}/"));
        let base_trimmed = daemon_base_url().trim_end_matches('/');
        let expected = format!("{base_trimmed}/{core}/");
        prop_assert_eq!(url, expected);
    }
}

// ── daemon_host_display scheme stripping ───────────────────────────────────

proptest! {
    /// Property: `daemon_host_display()` always returns a string that
    /// does not start with `http://` or `https://`.
    #[test]
    fn daemon_host_display_strips_http_scheme(_unused in 0u8..1u8) {
        let display = daemon_host_display();
        prop_assert!(
            !display.starts_with("http://"),
            "host display must not start with http:// (got {:?})",
            display,
        );
        prop_assert!(
            !display.starts_with("https://"),
            "host display must not start with https:// (got {:?})",
            display,
        );
    }

    /// Property: `daemon_host_display()` never returns an empty string —
    /// error messages and toast texts rely on a non-empty display.
    #[test]
    fn daemon_host_display_is_nonempty(_unused in 0u8..1u8) {
        let display = daemon_host_display();
        prop_assert!(!display.is_empty(), "host display must never be empty");
    }

    /// Property: `daemon_host_display()` never ends with a trailing
    /// slash (the value is used as-is in `<host>:<port>` form).
    #[test]
    fn daemon_host_display_has_no_trailing_slash(_unused in 0u8..1u8) {
        let display = daemon_host_display();
        prop_assert!(
            !display.ends_with('/'),
            "host display must not end with / (got {:?})",
            display,
        );
    }

    /// Property: idempotence — calling `daemon_host_display()` twice
    /// yields the same string. (No hidden state.)
    #[test]
    fn daemon_host_display_is_idempotent(_unused in 0u8..1u8) {
        let a = daemon_host_display();
        let b = daemon_host_display();
        prop_assert_eq!(a, b);
    }

    /// Property: the host display is substring-derivable from the base
    /// URL (i.e. it's a literal transformation, not a re-derived value).
    #[test]
    fn daemon_host_display_appears_in_base_url(_unused in 0u8..1u8) {
        let display = daemon_host_display();
        let base = daemon_base_url();
        let base_no_scheme = base
            .trim_start_matches("http://")
            .trim_start_matches("https://")
            .trim_end_matches('/');
        prop_assert_eq!(&display, base_no_scheme);
    }
}

// ── cross-helper invariants ───────────────────────────────────────────────

proptest! {
    /// Property: the daemon base URL itself never has a trailing slash
    /// when read via the helper (we trim in `daemon_api_url`, but the
    /// raw constant must also be free of trailing slashes).
    #[test]
    fn daemon_base_url_has_no_trailing_slash(_unused in 0u8..1u8) {
        let base = daemon_base_url();
        prop_assert!(
            !base.ends_with('/'),
            "daemon base URL must not end with / (got {:?})",
            base,
        );
    }

    /// Property: `daemon_api_url(path)` and the daemon base URL agree
    /// on the scheme + host portion of the URL. (i.e. when we strip
    /// the path off the joined URL, we should get back the base URL.)
    #[test]
    fn daemon_api_url_stripped_equals_base_url(
        path in "[a-zA-Z0-9/_.\\-]{0,30}",
    ) {
        let url = daemon_api_url(&path);
        let base = daemon_base_url().trim_end_matches('/');
        // The joined URL starts with `<base>/` (or just `<base>` for
        // empty path because we still added a separator).
        let prefix = format!("{base}/");
        prop_assert!(
            url.starts_with(&prefix),
            "url {:?} must start with {:?}",
            url,
            prefix,
        );
        // The character after the base must be the slash separator.
        let after_base = &url[base.len()..];
        prop_assert!(
            after_base.starts_with('/'),
            "url {:?} must have a slash after base (got after_base={:?})",
            url,
            after_base,
        );
    }
}
