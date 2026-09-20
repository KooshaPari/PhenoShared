//! Regex patterns and the [`ScanTraceLink`] output type.

use serde::{Deserialize, Serialize};

/// A trace annotation discovered in source code.
///
/// This is intentionally leaner than [`traceability_core::TraceLink`] — it
/// carries raw string ids and source coordinates, not graph UUIDs. Consumers
/// (e.g. `trace-gate`) convert these to richer types after collection.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ScanTraceLink {
    /// Functional-requirement id (e.g. `FR-001`).
    pub fr_id: String,
    /// Optional spec / ADR id (e.g. `SPEC-001`). May be empty string if absent.
    pub spec_id: String,
    /// Source file path (relative to scan root or absolute).
    pub file: String,
    /// 1-based line number of the annotation.
    pub line: usize,
    /// Symbol / identifier context (function name, struct name, etc.) if
    /// detectable; otherwise empty.
    pub symbol: String,
}

impl ScanTraceLink {
    /// Construct a minimal link with just fr_id and file coordinates.
    pub fn new(fr_id: impl Into<String>, file: impl Into<String>, line: usize) -> Self {
        Self {
            fr_id: fr_id.into(),
            spec_id: String::new(),
            file: file.into(),
            line,
            symbol: String::new(),
        }
    }
}

/// All compiled regexes for annotation recognition.
///
/// Compiled once at startup via [`Patterns::new`]; cheap to clone via Arc inside
/// the scanner.
pub struct Patterns {
    /// `#[trace_fr(spec="SPEC-001", fr="FR-001")]` — Rust attribute form.
    pub rust_attr: regex::Regex,
    /// `// FR: FR-001` — generic single-line comment.
    pub line_comment_fr: regex::Regex,
    /// `@trace_fr spec="SPEC-001" fr="FR-001"` — TS/Go block-comment form.
    pub ts_go_attr: regex::Regex,
    /// Optional spec capture from `rust_attr` or `ts_go_attr` annotations.
    pub spec_capture: regex::Regex,
}

impl Patterns {
    /// Compile all patterns. Panics only if the (hardcoded) patterns are invalid.
    pub fn new() -> Self {
        Self {
            // Matches: #[trace_fr(fr="FR-001")] or #[trace_fr(spec="X", fr="FR-001")]
            rust_attr: regex::Regex::new(
                r#"#\[trace_fr\((?:[^)]*?spec\s*=\s*"([^"]+)"\s*,\s*)?fr\s*=\s*"([^"]+)"[^)]*\)\]"#,
            )
            .expect("rust_attr regex"),

            // Matches: // FR: FR-001  or  # FR: FR-001  or  -- FR: FR-001
            line_comment_fr: regex::Regex::new(r"(?:/{2,}|#|--)\s*FR:\s*([A-Za-z0-9_-]+)")
                .expect("line_comment_fr regex"),

            // Matches: @trace_fr fr="FR-001" (with optional spec="X")
            ts_go_attr: regex::Regex::new(
                r#"@trace_fr(?:\s+spec\s*=\s*"([^"]+)")?\s+fr\s*=\s*"([^"]+)""#,
            )
            .expect("ts_go_attr regex"),

            // Standalone spec= capture for simple extraction
            spec_capture: regex::Regex::new(r#"spec\s*=\s*"([^"]+)""#).expect("spec_capture"),
        }
    }
}

impl Default for Patterns {
    fn default() -> Self {
        Self::new()
    }
}
