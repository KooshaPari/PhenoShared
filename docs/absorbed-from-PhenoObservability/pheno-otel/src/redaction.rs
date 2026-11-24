//! Deterministic PII redaction for telemetry payloads.
//!
//! The G2 deterministic-redaction fixture requires that the same input
//! yields byte-identical redacted output across runs, with no internal
//! randomness, no map iteration order affecting output, and no
//! platform-dependent formatting.
//!
//! Redaction strategy:
//!   1. Exact-match replacements for high-risk tokens (Bearer tokens,
//!      API keys, JWT-like strings). Deterministic ordering by rule
//!      declaration.
//!   2. Regex-driven detection for generic credential / email / IPv4
//!      patterns. Patterns are scanned left-to-right with stable
//!      replacement semantics.
//!   3. The result is always emitted in a stable order: the input string
//!      walked left-to-right, with redacted spans substituted in place.
//!
//! Determinism guarantees (all required by G2):
//!   * Same input → same output bytes
//!   * No allocation order dependence (`HashMap` not used in emit path)
//!   * No thread-local state
//!   * No platform-specific paths (regex uses the `regex` crate which
//!     has well-defined UTF-8 semantics)

use regex::Regex;
use std::sync::OnceLock;

/// The standard redaction token substituted in place of any matched
/// sensitive span. Fixed so that fixtures can assert against it
/// byte-for-byte.
pub const REDACTED: &str = "<REDACTED>";

/// Single exact-match redaction rule (substring → token).
#[derive(Debug, Clone)]
pub struct ExactRule {
    /// Substring to detect (case-insensitive matching).
    pub needle: &'static str,
    /// Replacement token (defaults to [`REDACTED`]).
    pub replacement: &'static str,
}

/// Single regex-driven redaction rule. The compiled [`Regex`] is cached
/// behind a [`OnceLock`] for performance.
#[derive(Debug, Clone)]
pub struct PatternRule {
    pub pattern: &'static str,
    pub replacement: &'static str,
    cell: OnceLock<Regex>,
}

impl PatternRule {
    /// Construct a new pattern rule. The regex is compiled lazily on
    /// first use (and any compile failure is treated as a config bug
    /// that surfaces at redaction time, not at construction).
    pub const fn new(pattern: &'static str, replacement: &'static str) -> Self {
        Self {
            pattern,
            replacement,
            cell: OnceLock::new(),
        }
    }

    fn compiled(&self) -> Result<&Regex, RedactionError> {
        if let Some(rx) = self.cell.get() {
            return Ok(rx);
        }
        let rx = Regex::new(self.pattern).map_err(|e| RedactionError::BadPattern {
            pattern: self.pattern,
            message: e.to_string(),
        })?;
        // If another thread raced us, prefer the cached compiled regex.
        let _ = self.cell.set(rx);
        Ok(self
            .cell
            .get()
            .expect("cell set above; reentrant only if regex ctor recurses"))
    }
}

/// Errors raised by [`Redactor`] operations.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RedactionError {
    /// A pattern rule failed to compile.
    BadPattern {
        pattern: &'static str,
        message: String,
    },
}

/// Deterministic redaction engine.
///
/// Construct with a static set of rules; the same input passed through
/// two engines with identical rule sets always yields identical output.
#[derive(Debug, Clone, Default)]
pub struct Redactor {
    exact: Vec<ExactRule>,
    pattern: Vec<PatternRule>,
}

impl Redactor {
    /// Construct a new empty redactor.
    pub fn new() -> Self {
        Self::default()
    }

    /// Append an exact-match rule. Rules are applied in the order they
    /// are added (left-to-right within the input).
    pub fn with_exact(mut self, rule: ExactRule) -> Self {
        self.exact.push(rule);
        self
    }

    /// Append a regex-driven rule. Compilation happens lazily on first
    /// [`Redactor::redact`] call.
    pub fn with_pattern(mut self, rule: PatternRule) -> Self {
        self.pattern.push(rule);
        self
    }

    /// Redact the input deterministically.
    ///
    /// Strategy:
    ///   1. Apply exact-match substitutions left-to-right.
    ///   2. Apply regex-driven substitutions in declaration order,
    ///      re-scanning the (already partially-redacted) string from the
    ///      start each time so that earlier redactions don't shadow
    ///      later ones in the same span.
    ///   3. No state is retained between calls; `Redactor` is `Sync`.
    pub fn redact(&self, input: &str) -> Result<String, RedactionError> {
        let mut out = input.to_string();
        for rule in &self.exact {
            out = replace_ignore_ascii_case(&out, rule.needle, rule.replacement);
        }
        for rule in &self.pattern {
            let rx = rule.compiled()?;
            // Re-replace_all from the beginning of the current string so
            // that an earlier exact-match redaction doesn't hide a
            // later pattern match nested inside it (or vice versa).
            out = rx.replace_all(&out, rule.replacement).into_owned();
        }
        Ok(out)
    }
}

/// ASCII-case-insensitive substring replacement. Returns a new `String`.
/// Used by the exact-match path so `Authorization: Bearer xxx` is matched
/// regardless of capitalisation in the input.
fn replace_ignore_ascii_case(input: &str, needle: &str, replacement: &str) -> String {
    if needle.is_empty() {
        return input.to_string();
    }
    let hay_lower = input.to_ascii_lowercase();
    let needle_lower = needle.to_ascii_lowercase();
    let mut out = String::with_capacity(input.len());
    let mut i = 0;
    while let Some(rel) = hay_lower[i..].find(&needle_lower) {
        out.push_str(&input[i..i + rel]);
        out.push_str(replacement);
        i += rel + needle_lower.len();
    }
    out.push_str(&input[i..]);
    out
}

/// Canonical redactor preconfigured with the rules PhenoObservability
/// applies to every emitted telemetry payload. Consumers may extend this
/// (e.g. with an internal project token) by adding their own rules.
pub fn default_redactor() -> Redactor {
    Redactor::new()
        // 1. HTTP authentication headers
        .with_exact(ExactRule {
            needle: "Authorization",
            replacement: REDACTED,
        })
        // 1a. RFC 6750 Bearer tokens — any token after `Bearer ` (not just JWTs)
        .with_pattern(PatternRule::new(r"(?i)Bearer [A-Za-z0-9._\-]+", REDACTED))
        .with_exact(ExactRule {
            needle: "x-api-key",
            replacement: REDACTED,
        })
        .with_exact(ExactRule {
            needle: "X-API-Key",
            replacement: REDACTED,
        })
        // 2. JWTs (three base64url segments separated by dots)
        .with_pattern(PatternRule::new(
            r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+",
            REDACTED,
        ))
        // 3. AWS-style access keys
        .with_pattern(PatternRule::new(r"AKIA[0-9A-Z]{16}", REDACTED))
        // 4. Email addresses (very simple; not RFC-perfect, but stable)
        .with_pattern(PatternRule::new(
            r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
            REDACTED,
        ))
        // 5. IPv4 addresses
        .with_pattern(PatternRule::new(
            r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
            REDACTED,
        ))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rid() -> Redactor {
        default_redactor()
    }

    #[test]
    fn bearer_token_is_redacted() {
        let out = rid().redact("Authorization: Bearer abc.def.ghi").unwrap();
        assert!(!out.contains("abc.def.ghi"), "leaked JWT: {out}");
        assert!(out.contains("<REDACTED>"));
    }

    #[test]
    fn email_is_redacted() {
        let out = rid()
            .redact("contact alice@example.com for details")
            .unwrap();
        assert!(!out.contains("alice@example.com"), "leaked email: {out}");
        assert!(out.contains("<REDACTED>"));
    }

    #[test]
    fn ipv4_is_redacted() {
        let out = rid().redact("client connected from 10.0.0.42").unwrap();
        assert!(!out.contains("10.0.0.42"), "leaked ipv4: {out}");
        assert!(out.contains("<REDACTED>"));
    }

    #[test]
    fn aws_access_key_redacted() {
        let out = rid()
            .redact("aws_access_key_id=AKIAIOSFODNN7EXAMPLE")
            .unwrap();
        assert!(
            !out.contains("AKIAIOSFODNN7EXAMPLE"),
            "leaked aws key: {out}"
        );
        assert!(out.contains("<REDACTED>"));
    }

    #[test]
    fn case_insensitive_header_match() {
        let out = rid().redact("authorization: token=abc").unwrap();
        // Either redaction token or matched header is acceptable, but the
        // literal "authorization:" must not survive verbatim.
        assert!(
            !out.to_ascii_lowercase().contains("authorization:"),
            "header name leaked: {out}"
        );
    }

    #[test]
    fn output_is_byte_deterministic_across_runs() {
        // Determinism anchor: 1000 calls with the same input yield
        // identical bytes, every run.
        let inputs = [
            "Authorization: Bearer abc.def.ghi contact alice@example.com 10.0.0.42",
            "AKIAIOSFODNN7EXAMPLE with IPv4 192.168.1.1",
            "no secrets here, just text",
        ];
        let r = rid();
        let firsts: Vec<String> = inputs.iter().map(|s| r.redact(s).unwrap()).collect();
        for _ in 0..1000 {
            for (i, s) in inputs.iter().enumerate() {
                let out = r.redact(s).unwrap();
                assert_eq!(out, firsts[i], "input #{i} drift");
            }
        }
    }

    #[test]
    fn empty_needle_does_not_loop() {
        // Defensive: a misconfigured exact rule with empty needle must
        // not infinite-loop.
        let r = Redactor::new().with_exact(ExactRule {
            needle: "",
            replacement: REDACTED,
        });
        let out = r.redact("hello world").unwrap();
        assert_eq!(out, "hello world");
    }
}
