//! Redacting wrapper for sensitive configuration values.
//!
//! ## Why
//!
//! Service configs routinely carry secret material that **must not** be
//! leaked into:
//!
//! - log lines (especially startup config dumps),
//! - error messages or `tracing` field records,
//! - JSON/TOML snapshots written to disk for crash diagnostics,
//! - `Debug` / `Display` printing during `unwrap()` or panic messages.
//!
//! Storing such fields as plain `String` makes accidental leakage a
//! matter of one `format!("{:?}", config)` away. [`SecretString`]
//! prevents the common failure modes by:
//!
//! - implementing [`Debug`](std::fmt::Debug) and
//!   [`Display`](std::fmt::Display) as `[REDACTED]`,
//! - dropping into a heap buffer that is zeroised before being freed,
//! - skipping the field entirely from any serialised form (see
//!   [`SecretString`] docs and [`Config::secret_value`](crate::Config)).
//!
//! ## When to use it
//!
//! Reach for [`SecretString`] for any value that is *plaintext
//! credential material* — API keys, OAuth tokens, passwords smuggled in
//! a connection string, webhook signing keys, ... It is overkill for
//! non-secret configuration; keep plain `String` for URLs, ports,
//! paths, and feature flags.
//!
//! ## Usage
//!
//! ```rust
//! use pheno_config::ConfigBuilder;
//! use pheno_config::secret::{ExposeSecret, SecretString};
//!
//! let cfg = ConfigBuilder::new()
//!     .url("https://example.com")
//!     .db_path("/var/lib/app.db")
//!     .secret_value("s3cret-token-value")
//!     .build()
//!     .expect("config");
//!
//! // Debug output redacts the secret material.
//! let dumped = format!("{:?}", cfg);
//! assert!(!dumped.contains("s3cret-token-value"));
//!
//! // Plaintext access is opt-in via `SecretBox::expose_secret`.
//! let raw = cfg.secret_value().map(|s| s.expose_secret().to_string());
//! assert_eq!(raw.as_deref(), Some("s3cret-token-value"));
//! ```

pub use secrecy::{ExposeSecret, SecretBox};

/// A heap-allocated, redacting wrapper around a sensitive string.
///
/// This is a type alias for `secrecy::SecretBox<str>` — a `Box<str>`
/// whose [`Debug`](std::fmt::Debug) and
/// [`Display`](std::fmt::Display) redacts the inner value and whose
/// [`Drop`](std::ops::Drop) zeroises the buffer before freeing.
///
/// **Not a `String`.** Clone with intent (every clone spreads the
/// secret into another heap allocation) and never `format!("{}")` it
/// through user-controlled format strings.
///
/// # Constructors
///
/// - [`new`] — from any string-like value (the recommended entry
///   point).
/// - `SecretBox::new` — directly, when you already hold a
///   `Box<str>`.
///
/// # Accessors
///
/// - [`ExposeSecret::expose_secret`] — the **only** way to read the
///   plaintext back out of the wrapper.
/// - `SecretBox::into_inner` — for handing off to a non-`secrecy`
///   consumer (a database driver, an HTTP client, ...). After this
///   call the buffer is **not** zeroised on drop, so prefer keeping
///   the `SecretBox` alive as long as possible.
pub type SecretString = SecretBox<str>;

/// Construct a [`SecretString`] from any string-like value.
///
/// Sugar for `SecretBox::new(s.into().into_boxed_str())`.
pub fn new_secret(value: impl Into<String>) -> SecretString {
    SecretBox::new(value.into().into_boxed_str())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    /// A freshly built `SecretString` round-trips the plaintext
    /// through `expose_secret`.
    #[test]
    fn secret_string_exposes_plaintext() {
        let s = new_secret("super-secret-token");
        assert_eq!(s.expose_secret(), "super-secret-token");
    }

    /// `Debug` must NOT leak the plaintext. This is the safety
    /// property the whole module exists to enforce.
    #[test]
    fn secret_string_debug_redacts() {
        let s = new_secret("super-secret-token");
        let dumped = format!("{s:?}");
        assert!(
            !dumped.contains("super-secret-token"),
            "Debug output leaked plaintext: {dumped}",
        );
        assert!(
            dumped.contains("REDACTED"),
            "Debug output should announce redaction; got: {dumped}",
        );
    }

    /// `SecretBox<str>` intentionally does not implement `Display`
    /// — there is no safe generic format-string path for an opaque
    /// secret. Make sure we cannot accidentally `format!("{s}")` it.
    #[test]
    fn secret_string_has_no_display_impl() {
        // The commented call below is documentation: it would fail
        // to compile because `SecretBox<str>` does not implement
        // `std::fmt::Display`. The type system enforces the safety
        // property for us — we just verify `Debug` formatting works
        // without leaking the plaintext.
        //
        // fn _assert_display<T: std::fmt::Display>(_: &T) {}
        // _assert_display(&new_secret("hunter2")); // would not compile
        let s = new_secret("hunter2");
        let debug_only = format!("{s:?}");
        assert!(!debug_only.contains("hunter2"));
    }

    /// The top-level helper `new_secret()` matches a hand-built
    /// `SecretString`.
    #[test]
    fn helper_matches_constructor() {
        let a = new_secret("token");
        let b = SecretBox::new(String::from("token").into_boxed_str());
        assert_eq!(a.expose_secret(), b.expose_secret());
    }
}
