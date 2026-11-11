//! Minimal in-tree PII / secret redaction helper (C02 L24).
//!
//! Hermetic string scrub for email addresses and common API-key / token
//! shapes. Std-only (no `regex` crate). Callers opt in — the ETL / HTTP API
//! do **not** auto-redact. This is **not** multi-tenant isolation.
//!
//! See `docs/ops/pii-redaction.md`.

/// Replacement for matched email addresses.
pub const REDACTED_EMAIL: &str = "[REDACTED_EMAIL]";

/// Replacement for matched API keys / bearer-style tokens.
pub const REDACTED_API_KEY: &str = "[REDACTED_API_KEY]";

/// Known API-key / token prefixes (case-sensitive where providers are).
const API_KEY_PREFIXES: &[&str] = &[
    "sk-",      // OpenAI-style secret keys
    "sk_live_", // Stripe live
    "sk_test_", // Stripe test
    "ghp_",     // GitHub PAT
    "gho_",     // GitHub OAuth
    "ghu_",     // GitHub user-to-server
    "ghs_",     // GitHub server-to-server
    "ghr_",     // GitHub refresh
    "AKIA",     // AWS access key id
    "xoxb-",    // Slack bot
    "xoxp-",    // Slack user
    "xoxa-",    // Slack app
    "xoxr-",    // Slack refresh
];

/// Redact emails and known API-key token shapes in `input`.
///
/// Order: API keys first (so key-shaped substrings are not partially
/// treated as emails), then emails.
#[must_use]
pub fn redact(input: &str) -> String {
    redact_emails(&redact_api_keys(input))
}

/// Replace email-shaped substrings with [`REDACTED_EMAIL`].
#[must_use]
pub fn redact_emails(input: &str) -> String {
    let mut out = String::with_capacity(input.len());
    let mut rest = input;
    while let Some((before, _matched, after)) = split_first_email(rest) {
        out.push_str(before);
        out.push_str(REDACTED_EMAIL);
        rest = after;
    }
    out.push_str(rest);
    out
}

/// Replace known API-key / token prefixes (plus following token body) with
/// [`REDACTED_API_KEY`].
#[must_use]
pub fn redact_api_keys(input: &str) -> String {
    let mut out = String::with_capacity(input.len());
    let mut rest = input;
    while let Some((before, _matched, after)) = split_first_api_key(rest) {
        out.push_str(before);
        out.push_str(REDACTED_API_KEY);
        rest = after;
    }
    out.push_str(rest);
    out
}

fn split_first_email(input: &str) -> Option<(&str, &str, &str)> {
    let bytes = input.as_bytes();
    let mut at = 0;
    while at < bytes.len() {
        if bytes[at] != b'@' {
            at += 1;
            continue;
        }
        if let (Some(local_start), Some(domain_end)) =
            (scan_local_back(bytes, at), scan_domain_forward(bytes, at + 1))
        {
            let before = &input[..local_start];
            let matched = &input[local_start..domain_end];
            let after = &input[domain_end..];
            return Some((before, matched, after));
        }
        at += 1;
    }
    None
}

fn split_first_api_key(input: &str) -> Option<(&str, &str, &str)> {
    let bytes = input.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        for prefix in API_KEY_PREFIXES {
            let pb = prefix.as_bytes();
            if i + pb.len() > bytes.len() || bytes[i..i + pb.len()] != *pb {
                continue;
            }
            // Avoid matching mid-token when the prior byte is token-shaped.
            if i > 0 && is_token_body(bytes[i - 1]) {
                continue;
            }
            let body_start = i + pb.len();
            let mut end = body_start;
            while end < bytes.len() && is_token_body(bytes[end]) {
                end += 1;
            }
            if end - body_start >= 8 {
                let before = &input[..i];
                let matched = &input[i..end];
                let after = &input[end..];
                return Some((before, matched, after));
            }
        }
        i += 1;
    }
    None
}

fn scan_local_back(bytes: &[u8], at: usize) -> Option<usize> {
    if at == 0 {
        return None;
    }
    let mut i = at;
    while i > 0 && is_email_local(bytes[i - 1]) {
        i -= 1;
    }
    if i == at {
        return None;
    }
    if bytes[i] == b'.' || bytes[at - 1] == b'.' {
        return None;
    }
    Some(i)
}

fn scan_domain_forward(bytes: &[u8], start: usize) -> Option<usize> {
    if start >= bytes.len() || !bytes[start].is_ascii_alphanumeric() {
        return None;
    }
    let mut i = start;
    let mut last_dot = None;
    while i < bytes.len() && is_email_domain(bytes[i]) {
        if bytes[i] == b'.' {
            if i == start || bytes[i - 1] == b'.' {
                return None;
            }
            last_dot = Some(i);
        }
        i += 1;
    }
    let last_dot = last_dot?;
    let tld = &bytes[last_dot + 1..i];
    if tld.len() < 2 || !tld.iter().all(u8::is_ascii_alphabetic) {
        return None;
    }
    Some(i)
}

fn is_email_local(b: u8) -> bool {
    b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'%' | b'+' | b'-')
}

fn is_email_domain(b: u8) -> bool {
    b.is_ascii_alphanumeric() || matches!(b, b'.' | b'-')
}

fn is_token_body(b: u8) -> bool {
    b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-')
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn redacts_email_in_prose() {
        let out = redact("contact alice@example.com please");
        assert_eq!(out, format!("contact {REDACTED_EMAIL} please"));
        assert!(!out.contains("alice@example.com"));
    }

    #[test]
    fn redacts_openai_style_key() {
        let key = "sk-abcdefghijklmnopqrstuvwxyz012345";
        let out = redact(&format!("token={key}"));
        assert_eq!(out, format!("token={REDACTED_API_KEY}"));
        assert!(!out.contains(key));
    }

    #[test]
    fn redacts_github_pat_and_aws_akia() {
        let ghp = "ghp_abcdefghijklmnopqrstuvwxyz0123456789";
        let akia = "AKIAIOSFODNN7EXAMPLE";
        let out = redact(&format!("a={ghp} b={akia}"));
        assert!(out.contains(REDACTED_API_KEY));
        assert!(!out.contains("ghp_"));
        assert!(!out.contains("AKIA"));
    }

    #[test]
    fn leaves_safe_text_alone() {
        assert_eq!(redact("hello world"), "hello world");
        assert_eq!(redact("user@"), "user@");
        assert_eq!(redact("sk-short"), "sk-short");
    }

    #[test]
    fn preserves_surrounding_unicode() {
        let out = redact("café alice@example.com ✓");
        assert_eq!(out, format!("café {REDACTED_EMAIL} ✓"));
    }

    #[test]
    fn redact_is_idempotent_on_placeholders() {
        let once = redact("mail me@host.org with sk-abcdefghijklmnopqrstuvwxyz012345");
        let twice = redact(&once);
        assert_eq!(once, twice);
    }
}
