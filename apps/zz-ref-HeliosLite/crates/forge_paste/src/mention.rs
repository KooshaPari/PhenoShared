//! `@`-mention parsing and resolution.
//!
//! Recognizes the following mention forms (extending the existing ZSH `wrap_pasted_text`
//! path-only logic in `crates/forge_main/src/zsh/paste.rs`):
//!
//! | Form                | Kind        | Example              |
//! |---------------------|-------------|----------------------|
//! | `@relative/path`    | `Path`      | `@src/lib.rs`        |
//! | `@/abs/path`        | `Path`      | `@/etc/hosts`        |
//! | `@~user/path`       | `Path`      | `@~/notes.md`        |
//! | `@dir/`             | `Directory` | `@src/`              |
//! | `@file.rs:123`      | `Path`      | `@src/lib.rs:42`     |
//! | `@file.rs#sym`      | `Path`      | `@src/lib.rs#Search` |
//! | `@agent:forge`      | `Agent`     | `@agent:forge`       |
//! | `@git:HEAD~3`       | `Git`       | `@git:HEAD~3`        |
//! | `@web:"query"`      | `Web`       | `@web:"rust async"`  |
//!
//! [`MentionSet`] is the result of parsing a full input string.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MentionKind {
    Path,
    Directory,
    Agent,
    Git,
    Web,
}

impl MentionKind {
    pub fn as_str(self) -> &'static str {
        match self {
            MentionKind::Path => "path",
            MentionKind::Directory => "directory",
            MentionKind::Agent => "agent",
            MentionKind::Git => "git",
            MentionKind::Web => "web",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Mention {
    pub kind: MentionKind,
    /// Raw text as it appeared in the input (e.g. `@src/lib.rs:42`).
    pub raw: String,
    /// Span `[start, end)` in the original input (UTF-8 byte offsets).
    pub start: usize,
    pub end: usize,
    /// Resolved value (e.g. the absolute path, agent id, git ref).
    /// `None` if not yet resolved — resolver is async and may need I/O.
    pub resolved: Option<String>,
    /// Line number, if applicable (e.g. `@src/lib.rs:42`).
    pub line: Option<u32>,
    /// Symbol/column, if applicable (e.g. `@src/lib.rs#search`).
    pub symbol: Option<String>,
}

impl Mention {
    pub fn placeholder(&self) -> String {
        // Match the existing wrap_pasted_text convention: `@[relative/path]`
        match self.kind {
            MentionKind::Path | MentionKind::Directory => {
                // `raw` already excludes the `:line` / `#symbol` suffix, so no
                // trimming after the leading `@` (trimming alphanumerics would
                // strip file extensions like `.rs`).
                let inner = self.raw.trim_start_matches('@');
                format!("@[{}]", inner)
            }
            MentionKind::Agent => {
                format!("@[{}]", self.raw.trim_start_matches("@agent:"))
            }
            MentionKind::Git => format!("@[{}]", self.raw.trim_start_matches("@git:")),
            MentionKind::Web => format!("@[{}]", self.raw.trim_start_matches("@web:")),
        }
    }
}

/// Result of parsing all mentions from an input string.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct MentionSet {
    pub mentions: Vec<Mention>,
    /// Input with mentions replaced by placeholders (so the model sees `@[...]`).
    pub rewritten: String,
}

/// Parse all mentions out of `input`.
///
/// Pure function — does no I/O, no FS access, no git lookups. Resolution happens
/// later via [`MentionSet::resolve`] (async).
pub fn parse(input: &str) -> MentionSet {
    let bytes = input.as_bytes();
    let mut mentions = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'@' {
            // Try parsing each kind starting at this position. Longest match wins.
            let rest = &input[i..];
            let best = parse_at_position(rest, i);
            if let Some((m, consumed)) = best {
                mentions.push(m);
                i += consumed;
                continue;
            }
        }
        i += 1;
    }

    // Build rewritten text by replacing mentions with placeholders, preserving order.
    let mut rewritten = String::with_capacity(input.len());
    let mut cursor = 0;
    for m in &mentions {
        rewritten.push_str(&input[cursor..m.start]);
        rewritten.push_str(&m.placeholder());
        cursor = m.end;
    }
    rewritten.push_str(&input[cursor..]);

    MentionSet { mentions, rewritten }
}

fn parse_at_position(s: &str, abs_start: usize) -> Option<(Mention, usize)> {
    // @agent:NAME (alphanumeric + dash + underscore)
    if let Some(rest) = s.strip_prefix("@agent:") {
        if let Some(end) = find_word_end(rest) {
            let name = &rest[..end];
            if !name.is_empty() {
                return Some((
                    Mention {
                        kind: MentionKind::Agent,
                        raw: format!("@agent:{}", name),
                        start: abs_start,
                        end: abs_start + 8 + name.len(), // "@agent:" + name
                        resolved: Some(name.to_string()),
                        line: None,
                        symbol: None,
                    },
                    8 + name.len(),
                ));
            }
        }
    }
    // @git:REF (anything until whitespace)
    if let Some(rest) = s.strip_prefix("@git:") {
        if let Some(end) = find_word_end(rest) {
            let git_ref = &rest[..end];
            if !git_ref.is_empty() {
                return Some((
                    Mention {
                        kind: MentionKind::Git,
                        raw: format!("@git:{}", git_ref),
                        start: abs_start,
                        end: abs_start + 5 + git_ref.len(),
                        resolved: Some(git_ref.to_string()),
                        line: None,
                        symbol: None,
                    },
                    5 + git_ref.len(),
                ));
            }
        }
    }
    // @web:"QUERY" or @web:QUERY (quoted preferred)
    if let Some(rest) = s.strip_prefix("@web:") {
        if let Some(q) = rest.strip_prefix('"').and_then(|r| r.split_once('"')) {
            // @web:"…" — count actual bytes consumed by the quote + query + closing quote
            let consumed = ("@web:\"".len()) + q.0.len() + 1; // closing quote
            return Some((
                Mention {
                    kind: MentionKind::Web,
                    raw: format!("@web:\"{}\"", q.0),
                    start: abs_start,
                    end: abs_start + consumed,
                    resolved: Some(q.0.to_string()),
                    line: None,
                    symbol: None,
                },
                consumed,
            ));
        }
        if let Some(end) = find_word_end(rest) {
            let query = &rest[..end];
            if !query.is_empty() {
                return Some((
                    Mention {
                        kind: MentionKind::Web,
                        raw: format!("@web:{}", query),
                        start: abs_start,
                        end: abs_start + 5 + query.len(),
                        resolved: Some(query.to_string()),
                        line: None,
                        symbol: None,
                    },
                    5 + query.len(),
                ));
            }
        }
    }
    // @/abs/path, @~user/path, @relative/path (with optional :line and #symbol)
    if s.starts_with("@/") || s.starts_with("@~/") || (s.len() > 1 && is_path_char(s.as_bytes()[1]))
    {
        return parse_path_mention(s, abs_start);
    }
    None
}

fn parse_path_mention(s: &str, abs_start: usize) -> Option<(Mention, usize)> {
    // Don't treat @agent:/@git:/@web: as path
    if s.starts_with("@agent:") || s.starts_with("@git:") || s.starts_with("@web:") {
        return None;
    }
    // Path body — must start with one of: `/`, `~/`, `[A-Za-z0-9_./-]`
    let body_start = 1; // skip '@'
    let bytes = s.as_bytes();
    if body_start >= bytes.len() {
        return None;
    }
    let mut i = body_start;
    let mut is_dir = false;
    while i < bytes.len() {
        let b = bytes[i];
        if is_path_char(b) {
            i += 1;
        } else {
            break;
        }
    }
    if i == body_start {
        return None;
    }
    let raw_path = &s[1..i];
    if raw_path.is_empty() {
        return None;
    }
    let mut end = i;
    let mut line: Option<u32> = None;
    let mut symbol: Option<String> = None;

    // Optional :line
    if end < bytes.len() && bytes[end] == b':' {
        // Look ahead for digits
        let mut j = end + 1;
        let digit_start = j;
        while j < bytes.len() && bytes[j].is_ascii_digit() {
            j += 1;
        }
        if j > digit_start {
            line = s[digit_start..j].parse::<u32>().ok();
            end = j;
        }
    }
    // Optional #symbol
    if end < bytes.len() && bytes[end] == b'#' {
        let sym_start = end + 1;
        let mut j = sym_start;
        while j < bytes.len() && (bytes[j].is_ascii_alphanumeric() || bytes[j] == b'_') {
            j += 1;
        }
        if j > sym_start {
            symbol = Some(s[sym_start..j].to_string());
            end = j;
        }
    }
    // Trailing `/` -> directory mention
    if raw_path.ends_with('/') || raw_path.ends_with('\\') {
        is_dir = true;
    }
    let kind = if is_dir {
        MentionKind::Directory
    } else {
        MentionKind::Path
    };
    let raw_full = s[1..end].to_string();
    Some((
        Mention {
            kind,
            raw: format!("@{}", raw_full),
            start: abs_start,
            end: abs_start + end,
            resolved: None, // resolved async via fs canonicalize
            line,
            symbol,
        },
        end,
    ))
}

fn is_path_char(b: u8) -> bool {
    b.is_ascii_alphanumeric()
        || b == b'/'
        || b == b'\\'
        || b == b'_'
        || b == b'-'
        || b == b'.'
        || b == b'~'
}

fn find_word_end(s: &str) -> Option<usize> {
    for (i, c) in s.char_indices() {
        if c.is_whitespace() || c == '\n' || c == '\r' {
            return Some(i);
        }
    }
    Some(s.len())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_relative_path() {
        let ms = parse("see @src/lib.rs for the fix");
        assert_eq!(ms.mentions.len(), 1);
        assert_eq!(ms.mentions[0].kind, MentionKind::Path);
        assert_eq!(ms.mentions[0].raw, "@src/lib.rs");
        assert_eq!(ms.rewritten, "see @[src/lib.rs] for the fix");
    }

    #[test]
    fn parse_abs_path() {
        let ms = parse("open @/etc/hosts now");
        assert_eq!(ms.mentions.len(), 1);
        assert_eq!(ms.mentions[0].kind, MentionKind::Path);
        assert_eq!(ms.mentions[0].raw, "@/etc/hosts");
    }

    #[test]
    fn parse_path_with_line() {
        let ms = parse("look at @src/lib.rs:42");
        assert_eq!(ms.mentions.len(), 1);
        assert_eq!(ms.mentions[0].line, Some(42));
        assert_eq!(ms.mentions[0].raw, "@src/lib.rs:42");
    }

    #[test]
    fn parse_path_with_symbol() {
        let ms = parse("find @src/lib.rs#Search");
        assert_eq!(ms.mentions.len(), 1);
        assert_eq!(ms.mentions[0].symbol.as_deref(), Some("Search"));
    }

    #[test]
    fn parse_directory() {
        let ms = parse("list @src/");
        assert_eq!(ms.mentions.len(), 1);
        assert_eq!(ms.mentions[0].kind, MentionKind::Directory);
    }

    #[test]
    fn parse_agent_mention() {
        let ms = parse("ask @agent:sage to refactor");
        assert_eq!(ms.mentions.len(), 1);
        assert_eq!(ms.mentions[0].kind, MentionKind::Agent);
        assert_eq!(ms.mentions[0].resolved.as_deref(), Some("sage"));
    }

    #[test]
    fn parse_git_mention() {
        let ms = parse("compare with @git:HEAD~3");
        assert_eq!(ms.mentions.len(), 1);
        assert_eq!(ms.mentions[0].kind, MentionKind::Git);
    }

    #[test]
    fn parse_web_mention() {
        let ms = parse("search @web:\"rust async\" please");
        assert_eq!(ms.mentions.len(), 1);
        assert_eq!(ms.mentions[0].kind, MentionKind::Web);
        assert_eq!(ms.mentions[0].resolved.as_deref(), Some("rust async"));
    }

    #[test]
    fn multiple_mentions() {
        let ms = parse("see @src/lib.rs and @src/main.rs");
        assert_eq!(ms.mentions.len(), 2);
        assert_eq!(ms.rewritten, "see @[src/lib.rs] and @[src/main.rs]");
    }

    #[test]
    fn no_mentions() {
        let ms = parse("just plain text without @ mentions that aren't mentions");
        // 'just plain text without' has no @, then ' mentions' has @ followed by space (not @word).
        assert_eq!(ms.mentions.len(), 0);
    }

    #[test]
    fn empty_input() {
        let ms = parse("");
        assert_eq!(ms.mentions.len(), 0);
        assert_eq!(ms.rewritten, "");
    }

    #[test]
    fn path_with_dot() {
        let ms = parse("open @./config.toml");
        assert_eq!(ms.mentions.len(), 1);
        assert_eq!(ms.mentions[0].raw, "@./config.toml");
    }
}
