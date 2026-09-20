//! File-walking scanner that extracts [`ScanTraceLink`]s from source text.

use std::path::Path;

use thiserror::Error;
use walkdir::WalkDir;

use crate::patterns::{Patterns, ScanTraceLink};

/// Errors that can arise during a scan.
#[derive(Debug, Error)]
pub enum ScanError {
    /// I/O error reading a source file.
    #[error("I/O error reading {path}: {source}")]
    Io {
        path: String,
        #[source]
        source: std::io::Error,
    },
    /// Directory walk error.
    #[error("walk error: {0}")]
    Walk(#[from] walkdir::Error),
}

/// Scan a single source file and return all [`ScanTraceLink`]s found.
///
/// `file_path` is used as-is in the emitted links (caller controls whether it's
/// absolute or relative to the scan root).
pub fn scan_file(file_path: &str, content: &str, patterns: &Patterns) -> Vec<ScanTraceLink> {
    let mut links = Vec::new();

    for (idx, line) in content.lines().enumerate() {
        let line_no = idx + 1;

        // ── Rust attribute: #[trace_fr(spec="…", fr="…")] ──────────────────
        if let Some(caps) = patterns.rust_attr.captures(line) {
            let spec_id = caps.get(1).map_or("", |m| m.as_str()).to_string();
            let fr_id = caps.get(2).map_or("", |m| m.as_str()).to_string();
            if !fr_id.is_empty() {
                links.push(ScanTraceLink {
                    fr_id,
                    spec_id,
                    file: file_path.to_string(),
                    line: line_no,
                    symbol: extract_symbol_context(content, idx),
                });
            }
            continue;
        }

        // ── TS/Go @trace_fr annotation ──────────────────────────────────────
        if let Some(caps) = patterns.ts_go_attr.captures(line) {
            let spec_id = caps.get(1).map_or("", |m| m.as_str()).to_string();
            let fr_id = caps.get(2).map_or("", |m| m.as_str()).to_string();
            if !fr_id.is_empty() {
                links.push(ScanTraceLink {
                    fr_id,
                    spec_id,
                    file: file_path.to_string(),
                    line: line_no,
                    symbol: String::new(),
                });
            }
            continue;
        }

        // ── Generic line comment: // FR: FR-001 ─────────────────────────────
        if let Some(caps) = patterns.line_comment_fr.captures(line) {
            let fr_id = caps.get(1).map_or("", |m| m.as_str()).to_string();
            if !fr_id.is_empty() {
                // Try to also pull a spec= if it appears later on the same line.
                let spec_id = patterns
                    .spec_capture
                    .captures(line)
                    .and_then(|c| c.get(1))
                    .map(|m| m.as_str().to_string())
                    .unwrap_or_default();
                links.push(ScanTraceLink {
                    fr_id,
                    spec_id,
                    file: file_path.to_string(),
                    line: line_no,
                    symbol: String::new(),
                });
            }
        }
    }

    links
}

/// Walk `dir` recursively, scanning every file for trace annotations.
///
/// Skips binary-looking files (non-UTF-8). Follows symlinks.
// FR: FR-GATE-002
pub fn scan_dir(dir: &Path, patterns: &Patterns) -> Result<Vec<ScanTraceLink>, ScanError> {
    let mut all = Vec::new();
    for entry in WalkDir::new(dir).follow_links(true) {
        let entry = entry?;
        if !entry.file_type().is_file() {
            continue;
        }
        let path = entry.path();
        // Skip obviously binary or non-source extensions we won't find annotations in.
        if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
            if matches!(
                ext,
                "png"
                    | "jpg"
                    | "jpeg"
                    | "gif"
                    | "svg"
                    | "woff"
                    | "woff2"
                    | "ttf"
                    | "otf"
                    | "ico"
                    | "pdf"
                    | "lock"
            ) {
                continue;
            }
        }
        let path_str = path.to_string_lossy().to_string();
        let content = match std::fs::read_to_string(path) {
            Ok(c) => c,
            Err(e) if e.kind() == std::io::ErrorKind::InvalidData => {
                // Binary file — skip silently.
                continue;
            }
            Err(e) => {
                return Err(ScanError::Io {
                    path: path_str,
                    source: e,
                })
            }
        };
        let links = scan_file(&path_str, &content, patterns);
        all.extend(links);
    }
    Ok(all)
}

/// Attempt to extract the nearest symbol name (fn/struct/class/func).
///
/// Searches up to 3 lines *before* and 3 lines *after* `line_idx` (0-based).
/// Annotations in Rust sit on the line *before* `fn`, so the forward scan is
/// the common case; backward scan covers `// FR:` comments placed after a fn
/// signature or inside a body.
fn extract_symbol_context(content: &str, line_idx: usize) -> String {
    let lines: Vec<&str> = content.lines().collect();
    let n = lines.len();
    // Search window: up to 3 back, up to 3 forward.
    let back_start = line_idx.saturating_sub(3);
    let fwd_end = (line_idx + 3).min(n.saturating_sub(1));

    // Collect candidate indices sorted by proximity: forward first (common for
    // Rust attrs), then backward.
    let mut candidates: Vec<usize> = (line_idx + 1..=fwd_end).collect();
    for i in (back_start..line_idx).rev() {
        candidates.push(i);
    }

    for i in candidates {
        if let Some(sym) = try_extract_symbol(lines[i]) {
            return sym;
        }
    }
    String::new()
}

/// Try to extract a symbol name from a single source line. Returns `None` if
/// the line doesn't look like a function/struct/impl/class definition.
fn try_extract_symbol(line: &str) -> Option<String> {
    let l = line.trim();
    // Rust: `pub async fn`, `pub fn`, `async fn`, `fn`
    let sym = l
        .strip_prefix("pub async fn ")
        .or_else(|| l.strip_prefix("pub fn "))
        .or_else(|| l.strip_prefix("async fn "))
        .or_else(|| l.strip_prefix("fn "))
        // Rust struct/impl
        .or_else(|| l.strip_prefix("pub struct "))
        .or_else(|| l.strip_prefix("struct "))
        .or_else(|| l.strip_prefix("impl "))
        // TS/Go
        .or_else(|| l.strip_prefix("export async function "))
        .or_else(|| l.strip_prefix("export function "))
        .or_else(|| l.strip_prefix("function "))
        .or_else(|| l.strip_prefix("func "))
        // Python
        .or_else(|| l.strip_prefix("def "))
        .or_else(|| l.strip_prefix("async def "))?;
    let name = sym.split(['(', '<', ' ', '{']).next().unwrap_or("").trim();
    if name.is_empty() {
        None
    } else {
        Some(name.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::patterns::Patterns;

    fn p() -> Patterns {
        Patterns::new()
    }

    #[test]
    fn rust_attr_no_spec() {
        let src = r#"
#[trace_fr(fr="FR-042")]
pub fn my_handler() {}
"#;
        let links = scan_file("test.rs", src, &p());
        assert_eq!(links.len(), 1);
        assert_eq!(links[0].fr_id, "FR-042");
        assert_eq!(links[0].spec_id, "");
        assert_eq!(links[0].symbol, "my_handler");
    }

    #[test]
    fn rust_attr_with_spec() {
        let src = r##"
#[trace_fr(spec="SPEC-007", fr="FR-007")]
pub fn create_workspace() {}
"##;
        let links = scan_file("src/lib.rs", src, &p());
        assert_eq!(links.len(), 1);
        assert_eq!(links[0].fr_id, "FR-007");
        assert_eq!(links[0].spec_id, "SPEC-007");
    }

    #[test]
    fn line_comment_rust_style() {
        let src = "// FR: FR-100\nfn do_thing() {}";
        let links = scan_file("foo.rs", src, &p());
        assert_eq!(links.len(), 1);
        assert_eq!(links[0].fr_id, "FR-100");
        assert_eq!(links[0].line, 1);
    }

    #[test]
    fn line_comment_hash_style() {
        let src = "# FR: NFR-001\ndef my_func():";
        let links = scan_file("foo.py", src, &p());
        assert_eq!(links.len(), 1);
        assert_eq!(links[0].fr_id, "NFR-001");
    }

    #[test]
    fn ts_go_attr_with_spec() {
        let src = r##"
// @trace_fr spec="SPEC-003" fr="FR-003"
export function submitForm() {}
"##;
        let links = scan_file("form.ts", src, &p());
        assert_eq!(links.len(), 1);
        assert_eq!(links[0].fr_id, "FR-003");
        assert_eq!(links[0].spec_id, "SPEC-003");
    }

    #[test]
    fn ts_go_attr_without_spec() {
        let src = r##"/* @trace_fr fr="FR-099" */"##;
        let links = scan_file("handler.go", src, &p());
        assert_eq!(links.len(), 1);
        assert_eq!(links[0].fr_id, "FR-099");
        assert_eq!(links[0].spec_id, "");
    }

    #[test]
    fn no_annotations_returns_empty() {
        let src = "fn plain() { /* nothing here */ }";
        assert!(scan_file("plain.rs", src, &p()).is_empty());
    }

    #[test]
    fn multiple_annotations_in_file() {
        let src = r##"
// FR: FR-001
fn a() {}
#[trace_fr(fr="FR-002")]
fn b() {}
// @trace_fr fr="FR-003"
fn c() {}
"##;
        let links = scan_file("multi.rs", src, &p());
        assert_eq!(links.len(), 3);
        let ids: Vec<&str> = links.iter().map(|l| l.fr_id.as_str()).collect();
        assert!(ids.contains(&"FR-001"));
        assert!(ids.contains(&"FR-002"));
        assert!(ids.contains(&"FR-003"));
    }

    #[test]
    fn line_numbers_are_1_based() {
        let src = "fn noop() {}\n// FR: FR-010\nfn real() {}";
        let links = scan_file("nums.rs", src, &p());
        assert_eq!(links[0].line, 2);
    }
}
