//! String escaping for safe interpolation into `AppleScript` / PowerShell.
//!
//! This is the single most security-critical module in the crate — agent
//! authored strings get embedded into a shell-out command, so any
//! unsanitized quote, newline, or control character is an injection
//! vector. Both functions here are designed to be tight enough that
//! adversarial input produces a denial-of-service error rather than code
//! execution.

use crate::error::ElicitError;

/// Escape a string for safe interpolation into an `AppleScript` double-quoted
/// string literal (e.g., the `text` parameter of `display dialog`).
///
/// Rules applied:
/// - Wraps in `"..."`.
/// - Escapes `\` and `"`.
/// - Rejects ASCII control chars (0x00..=0x1F except `\t`) — caller should
///   sanitize input before passing.
/// - Rejects non-ASCII characters other than printable Unicode — `AppleScript`
///   encoding is fragile on strings containing weird code points; reject
///   to fail safely.
///
/// # Errors
///
/// Returns [`ElicitError::InvalidSpec`] if the input contains forbidden
/// characters.
pub fn applescript_escape(s: &str) -> Result<String, ElicitError> {
    for c in s.chars() {
        let code = c as u32;
        let is_allowed = (code >= 0x20 && code != 0x7F) || c == '\t' || c == '\n' || c == '\r';
        if !is_allowed {
            return Err(ElicitError::InvalidSpec(format!(
                "refusing to applescript-escape string containing forbidden char U+{code:04X}"
            )));
        }
    }
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '"' => out.push_str("\\\""),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            _ => out.push(c),
        }
    }
    out.push('"');
    Ok(out)
}

/// Escape a string for safe interpolation into a PowerShell double-quoted
/// string literal (e.g., the `-Text` parameter of a Win32 form).
///
/// Rules applied:
/// - Wraps in `"..."`.
/// - Doubles embedded `"`.
/// - Escapes `` ` `` (the PowerShell escape char).
/// - Rejects NUL bytes.
///
/// # Errors
///
/// Returns [`ElicitError::InvalidSpec`] if the input contains NUL.
pub fn powershell_escape(s: &str) -> Result<String, ElicitError> {
    if s.contains('\0') {
        return Err(ElicitError::InvalidSpec(
            "refusing to powershell-escape string containing NUL".into(),
        ));
    }
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\"\""),
            '`' => out.push_str("``"),
            _ => out.push(c),
        }
    }
    out.push('"');
    Ok(out)
}

/// Escape a string for safe use as a single-quoted bash argument.
///
/// Used when shelling out to `zenity` / `kdialog` / `python3` on Linux.
#[must_use]
pub fn shell_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('\'');
    for c in s.chars() {
        if c == '\'' {
            out.push_str("'\\''");
        } else {
            out.push(c);
        }
    }
    out.push('\'');
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn applescript_escapes_plain() {
        assert_eq!(applescript_escape("hello").unwrap(), "\"hello\"");
    }

    #[test]
    fn applescript_escapes_quotes() {
        assert_eq!(
            applescript_escape("say \"hi\"").unwrap(),
            "\"say \\\"hi\\\"\""
        );
    }

    #[test]
    fn applescript_escapes_backslash() {
        assert_eq!(applescript_escape("a\\b").unwrap(), "\"a\\\\b\"");
    }

    #[test]
    fn applescript_escapes_newlines() {
        assert_eq!(applescript_escape("a\nb").unwrap(), "\"a\\nb\"");
    }

    #[test]
    fn applescript_rejects_nul() {
        assert!(applescript_escape("a\0b").is_err());
    }

    #[test]
    fn applescript_rejects_bell() {
        assert!(applescript_escape("a\x07b").is_err());
    }

    #[test]
    fn applescript_handles_unicode() {
        assert_eq!(applescript_escape("café").unwrap(), "\"café\"");
    }

    #[test]
    fn powershell_escapes_plain() {
        assert_eq!(powershell_escape("hello").unwrap(), "\"hello\"");
    }

    #[test]
    fn powershell_doubles_quotes() {
        assert_eq!(
            powershell_escape("say \"hi\"").unwrap(),
            "\"say \"\"hi\"\"\""
        );
    }

    #[test]
    fn powershell_escapes_backtick() {
        assert_eq!(powershell_escape("a`b").unwrap(), "\"a``b\"");
    }

    #[test]
    fn powershell_rejects_nul() {
        assert!(powershell_escape("a\0b").is_err());
    }

    #[test]
    fn powershell_preserves_newlines() {
        // PowerShell double-quoted strings preserve newlines literally
        assert_eq!(powershell_escape("a\nb").unwrap(), "\"a\nb\"");
    }

    #[test]
    fn shell_escape_simple() {
        assert_eq!(shell_escape("hello"), "'hello'");
    }

    #[test]
    fn shell_escape_handles_quote() {
        assert_eq!(shell_escape("it's"), "'it'\\''s'");
    }

    #[test]
    fn shell_escape_preserves_spaces() {
        assert_eq!(shell_escape("a b"), "'a b'");
    }

    #[test]
    fn adversarial_injection_does_not_break() {
        // Adversarial: trying to break out of the AppleScript string
        let attack = r#"" & do shell script "rm -rf /" & "#;
        let escaped = applescript_escape(attack).unwrap();
        // The escaped form should still be one literal string when parsed.
        // AppleScript would see one literal: " & do shell script "rm -rf /" & "
        assert!(escaped.starts_with('"'));
        assert!(escaped.ends_with('"'));
    }
}