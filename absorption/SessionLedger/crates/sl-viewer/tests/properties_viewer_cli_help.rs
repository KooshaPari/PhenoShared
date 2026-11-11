//! Property evidence for the `sl-viewer::cli_help` text helpers.
//!
//! Two helpers produce the `sl-viewer --help` and `sl-viewer --version`
//! output:
//!
//!  * `help_text()` — multi-section manual with USAGE, ENVIRONMENT,
//!    IN-VIEWER, DOCS sections
//!  * `version_text()` — package version, daemon URL, docs cross-link
//!
//! Both rely on env vars (`CARGO_PKG_VERSION`, optional `SL_DAEMON_URL`)
//! and constants (HELP_HEADING, DEFAULT_DAEMON_BASE). Their contracts:
//!
//!  * `help_text()` always mentions every documented env var
//!    (SL_DAEMON_URL, FORGE_DB, SL_VIEWER_DEMO)
//!  * `help_text()` always cross-links the docs folder
//!  * `version_text()` always includes the package version, the word
//!    `daemon:`, and the help-doc link
//!  * Both helpers are deterministic (same env = same output)
//!  * Both helpers can be called many times without state mutation
//!  * `HELP_HEADING` mentions `sl-viewer` and `SessionLedger`
//!  * Idempotence holds across many calls

use proptest::prelude::*;
use sl_viewer::cli_help::{help_text, version_text, HELP_HEADING};

// ── help_text invariants ──────────────────────────────────────────────────

proptest! {
    /// Property: every documented environment variable must appear in
    /// `help_text()` output. Regression-safe even across documentation
    /// drift: the test still asserts the three names we promised.
    #[test]
    fn help_text_documents_all_env_vars(_unused in 0u8..1u8) {
        let help = help_text();
        prop_assert!(help.contains("SL_DAEMON_URL"));
        prop_assert!(help.contains("FORGE_DB"));
        prop_assert!(help.contains("SL_VIEWER_DEMO"));
    }

    /// Property: the help text always cross-links the documentation set
    /// (in-viewer shortcuts, CLI SSOT, first-run quickstart).
    #[test]
    fn help_text_links_all_documented_docs(_unused in 0u8..1u8) {
        let help = help_text();
        prop_assert!(help.contains("sl-viewer-help.md"), "missing CLI help doc link");
        prop_assert!(help.contains("QUICKSTART.md"), "missing QUICKSTART doc link");
        prop_assert!(help.contains("DOCS:"), "missing DOCS section header");
    }

    /// Property: the help text always carries the standard section
    /// headers (USAGE, ENVIRONMENT, IN-VIEWER, DOCS).
    #[test]
    fn help_text_includes_section_headers(_unused in 0u8..1u8) {
        let help = help_text();
        for header in ["USAGE:", "ENVIRONMENT:", "IN-VIEWER:", "DOCS:"] {
            prop_assert!(help.contains(header), "help text missing {:?} section", header);
        }
    }

    /// Property: the help text mentions the documentation toggle
    /// (`?` for help overlay) and the command-palette shortcut (`Cmd+K`).
    #[test]
    fn help_text_mentions_keyboard_shortcuts(_unused in 0u8..1u8) {
        let help = help_text();
        prop_assert!(help.contains("?"), "help text must mention ? help-toggle shortcut");
        prop_assert!(
            help.contains("Cmd") || help.contains("Ctrl"),
            "help text must mention Cmd/Ctrl keyboard shortcut",
        );
        prop_assert!(help.contains("K"), "help text must mention K palette key");
    }

    /// Property: `help_text()` always begins with `HELP_HEADING` so
    /// `sl-viewer --help` shows the product name on the first line.
    #[test]
    fn help_text_starts_with_help_heading(_unused in 0u8..1u8) {
        let help = help_text();
        prop_assert!(
            help.starts_with(HELP_HEADING),
            "help text must start with HELP_HEADING; got {:?}",
            help.lines().next().unwrap_or(""),
        );
    }

    /// Property: `help_text()` is idempotent — calling it twice yields
    /// the same string. (No hidden state.)
    #[test]
    fn help_text_is_idempotent(_unused in 0u8..1u8) {
        let a = help_text();
        let b = help_text();
        prop_assert_eq!(a, b);
    }

    /// Property: `help_text()` non-empty across rebuilds.
    #[test]
    fn help_text_is_nonempty(_unused in 0u8..1u8) {
        prop_assert!(!help_text().is_empty());
    }

    /// Property: `help_text()` always mentions the default daemon URL
    /// literal (so users see the off-by-default endpoint without env vars).
    #[test]
    fn help_text_includes_default_daemon_url(_unused in 0u8..1u8) {
        let help = help_text();
        prop_assert!(
            help.contains("127.0.0.1") && help.contains("8080"),
            "help text must include the default daemon URL (127.0.0.1:8080)",
        );
    }
}

// ── version_text invariants ───────────────────────────────────────────────

proptest! {
    /// Property: `version_text()` always includes the package version
    /// baked into the binary (`env!("CARGO_PKG_VERSION")`).
    #[test]
    fn version_text_includes_package_version(_unused in 0u8..1u8) {
        let version = version_text();
        prop_assert!(version.contains(env!("CARGO_PKG_VERSION")));
    }

    /// Property: `version_text()` always carries the literal
    /// `daemon:` marker followed by the resolved daemon base URL.
    #[test]
    fn version_text_marks_daemon_url(_unused in 0u8..1u8) {
        let version = version_text();
        prop_assert!(version.contains("daemon:"));
        prop_assert!(
            version.contains("http://") || version.contains("https://"),
            "version text must include a URL scheme",
        );
    }

    /// Property: `version_text()` always cross-links the help doc.
    #[test]
    fn version_text_links_help_doc(_unused in 0u8..1u8) {
        let version = version_text();
        prop_assert!(version.contains("sl-viewer-help.md"));
        prop_assert!(version.contains("help:"));
    }

    /// Property: `version_text()` always starts with the binary name.
    #[test]
    fn version_text_starts_with_binary_name(_unused in 0u8..1u8) {
        let version = version_text();
        let first_line = version.lines().next().unwrap_or("");
        prop_assert!(first_line.starts_with("sl-viewer"));
    }

    /// Property: `version_text()` is idempotent.
    #[test]
    fn version_text_is_idempotent(_unused in 0u8..1u8) {
        let a = version_text();
        let b = version_text();
        prop_assert_eq!(a, b);
    }

    /// Property: `version_text()` non-empty across rebuilds.
    #[test]
    fn version_text_is_nonempty(_unused in 0u8..1u8) {
        prop_assert!(!version_text().is_empty());
    }

    /// Property: `version_text()` always identifies the binary as
    /// part of SessionLedger (so support diagnostics can map it to
    /// the right workspace).
    #[test]
    fn version_text_identifies_session_ledger(_unused in 0u8..1u8) {
        let version = version_text();
        prop_assert!(version.contains("SessionLedger"));
    }

    /// Property: `version_text()` includes the resolved daemon base URL
    /// exactly as `daemon_base_url()` returns it.
    #[test]
    fn version_text_daemon_matches_daemon_base_url(_unused in 0u8..1u8) {
        let version = version_text();
        let base = sl_viewer::daemon_url::daemon_base_url();
        prop_assert!(
            version.contains(base),
            "version text must include daemon base URL {:?}",
            base,
        );
    }
}

// ── HELP_HEADING invariants ───────────────────────────────────────────────

proptest! {
    /// Property: HELP_HEADING mentions the binary name and the workspace
    /// name (used as the first line of `--help` and `--version`).
    #[test]
    fn help_heading_names_product_and_workspace(_unused in 0u8..1u8) {
        prop_assert!(HELP_HEADING.contains("sl-viewer"));
        prop_assert!(HELP_HEADING.contains("SessionLedger"));
    }

    /// Property: HELP_HEADING is non-empty.
    #[test]
    fn help_heading_is_nonempty(_unused in 0u8..1u8) {
        prop_assert!(!HELP_HEADING.is_empty());
    }

    /// Property: HELP_HEADING is short enough to fit a terminal first
    /// line (longer than ~80 chars looks bad on small screens).
    #[test]
    fn help_heading_fits_terminal_first_line(_unused in 0u8..1u8) {
        prop_assert!(
            HELP_HEADING.len() <= 80,
            "HELP_HEADING too long for terminal first line ({} chars): {:?}",
            HELP_HEADING.len(),
            HELP_HEADING,
        );
    }
}

// ── Cross-cutting invariants ──────────────────────────────────────────────

proptest! {
    /// Property: `help_text` and `version_text` both reference the
    /// same help-doc cross-link (`sl-viewer-help.md`).
    #[test]
    fn help_and_version_share_doc_link(_unused in 0u8..1u8) {
        let help = help_text();
        let version = version_text();
        prop_assert!(help.contains("sl-viewer-help.md"));
        prop_assert!(version.contains("sl-viewer-help.md"));
    }

    /// Property: `help_text` always has more content than `version_text`
    /// (i.e. the help is not as terse as --version).
    #[test]
    fn help_is_longer_than_version(_unused in 0u8..1u8) {
        prop_assert!(help_text().len() > version_text().len());
    }

    /// Property: HELP_HEADING appears as a substring in `help_text`.
    #[test]
    fn help_heading_appears_in_help_text(_unused in 0u8..1u8) {
        prop_assert!(help_text().contains(HELP_HEADING));
    }
}
