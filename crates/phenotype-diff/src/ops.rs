//! Core operations: [`diff`] and [`apply`].

use similar::{ChangeTag, TextDiff};

use crate::{
    error::DiffError,
    model::{DiffLine, Hunk, HunkHeader, UnifiedDiff},
};

const CONTEXT_LINES: usize = 3;

/// Compute a [`UnifiedDiff`] between `old` and `new` text.
///
/// Both inputs are split on line boundaries (preserving `\n` endings).
#[must_use]
pub fn diff(old: &str, new: &str) -> UnifiedDiff {
    let text_diff = TextDiff::from_lines(old, new);
    let mut hunks = Vec::new();

    for group in text_diff.grouped_ops(CONTEXT_LINES) {
        let mut lines: Vec<DiffLine> = Vec::new();
        let mut old_start = usize::MAX;
        let mut old_count = 0usize;
        let mut new_start = usize::MAX;
        let mut new_count = 0usize;

        for op in &group {
            for change in text_diff.iter_changes(op) {
                let tag = change.tag();
                let content = change.value().to_owned();

                match tag {
                    ChangeTag::Delete => {
                        let idx = change.old_index().unwrap_or(0);
                        if old_start == usize::MAX {
                            old_start = idx + 1;
                        }
                        old_count += 1;
                        lines.push(DiffLine::Removed(content));
                    }
                    ChangeTag::Insert => {
                        let idx = change.new_index().unwrap_or(0);
                        if new_start == usize::MAX {
                            new_start = idx + 1;
                        }
                        new_count += 1;
                        lines.push(DiffLine::Added(content));
                    }
                    ChangeTag::Equal => {
                        let oi = change.old_index().unwrap_or(0);
                        let ni = change.new_index().unwrap_or(0);
                        if old_start == usize::MAX {
                            old_start = oi + 1;
                        }
                        if new_start == usize::MAX {
                            new_start = ni + 1;
                        }
                        old_count += 1;
                        new_count += 1;
                        lines.push(DiffLine::Context(content));
                    }
                }
            }
        }

        if old_start == usize::MAX {
            old_start = 1;
        }
        if new_start == usize::MAX {
            new_start = 1;
        }

        hunks.push(Hunk {
            header: HunkHeader {
                old_start,
                old_lines: old_count,
                new_start,
                new_lines: new_count,
            },
            lines,
        });
    }

    UnifiedDiff { hunks }
}

/// Apply a [`UnifiedDiff`] patch to `source`, returning the patched text.
///
/// Returns [`DiffError::ContextMismatch`] if context lines do not match,
/// or [`DiffError::OutOfRange`] if the patch refers to lines beyond the source.
pub fn apply(source: &str, patch: &UnifiedDiff) -> Result<String, DiffError> {
    if patch.is_empty() {
        return Ok(source.to_owned());
    }

    let source_lines: Vec<&str> = source.split_inclusive('\n').collect();
    let source_len = source_lines.len();
    let mut output: Vec<String> = Vec::with_capacity(source_len);
    let mut src_cursor = 0usize; // 0-based index into source_lines

    for hunk in &patch.hunks {
        let hunk_old_start = hunk.header.old_start.saturating_sub(1); // convert to 0-based

        // Validate the hunk start is reachable
        if hunk_old_start > source_len {
            return Err(DiffError::OutOfRange {
                line: hunk.header.old_start,
                source_len,
            });
        }

        // Copy source lines that precede this hunk
        while src_cursor < hunk_old_start {
            output.push(source_lines[src_cursor].to_owned());
            src_cursor += 1;
        }

        // Apply each diff line in the hunk
        for dl in &hunk.lines {
            match dl {
                DiffLine::Context(expected) => {
                    if src_cursor >= source_len {
                        return Err(DiffError::OutOfRange {
                            line: src_cursor + 1,
                            source_len,
                        });
                    }
                    if source_lines[src_cursor] != expected.as_str() {
                        return Err(DiffError::ContextMismatch {
                            expected: expected.clone(),
                            got: source_lines[src_cursor].to_owned(),
                        });
                    }
                    output.push(expected.clone());
                    src_cursor += 1;
                }
                DiffLine::Removed(expected) => {
                    if src_cursor >= source_len {
                        return Err(DiffError::OutOfRange {
                            line: src_cursor + 1,
                            source_len,
                        });
                    }
                    if source_lines[src_cursor] != expected.as_str() {
                        return Err(DiffError::ContextMismatch {
                            expected: expected.clone(),
                            got: source_lines[src_cursor].to_owned(),
                        });
                    }
                    // Drop the line (it's removed)
                    src_cursor += 1;
                }
                DiffLine::Added(line) => {
                    output.push(line.clone());
                }
            }
        }
    }

    // Append any remaining source lines after the last hunk
    while src_cursor < source_len {
        output.push(source_lines[src_cursor].to_owned());
        src_cursor += 1;
    }

    Ok(output.join(""))
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── diff ─────────────────────────────────────────────────────────────────

    #[test]
    fn diff_identical_texts_produces_empty_patch() {
        let text = "line one\nline two\n";
        let patch = diff(text, text);
        assert!(patch.is_empty(), "identical texts should produce no hunks");
    }

    #[test]
    fn diff_single_line_change_produces_one_hunk() {
        let old = "hello world\n";
        let new = "hello rust\n";
        let patch = diff(old, new);
        assert_eq!(patch.hunks.len(), 1);
        let hunk = &patch.hunks[0];
        assert!(hunk.lines.iter().any(|l| matches!(l, DiffLine::Removed(_))));
        assert!(hunk.lines.iter().any(|l| matches!(l, DiffLine::Added(_))));
    }

    #[test]
    fn diff_added_lines_only() {
        let old = "line one\n";
        let new = "line one\nline two\n";
        let patch = diff(old, new);
        assert!(!patch.is_empty());
        let added: Vec<_> = patch
            .hunks
            .iter()
            .flat_map(|h| &h.lines)
            .filter(|l| matches!(l, DiffLine::Added(_)))
            .collect();
        assert!(!added.is_empty());
    }

    #[test]
    fn diff_removed_lines_only() {
        let old = "line one\nline two\n";
        let new = "line one\n";
        let patch = diff(old, new);
        assert!(!patch.is_empty());
        let removed: Vec<_> = patch
            .hunks
            .iter()
            .flat_map(|h| &h.lines)
            .filter(|l| matches!(l, DiffLine::Removed(_)))
            .collect();
        assert!(!removed.is_empty());
    }

    #[test]
    fn diff_multiline_change_produces_correct_hunk_counts() {
        let old = "a\nb\nc\nd\ne\n";
        let new = "a\nb\nX\nd\ne\n";
        let patch = diff(old, new);
        assert_eq!(patch.hunks.len(), 1);
    }

    // ── apply ────────────────────────────────────────────────────────────────

    #[test]
    fn apply_empty_patch_returns_source_unchanged() {
        let src = "hello world\n";
        let patch = UnifiedDiff { hunks: vec![] };
        assert_eq!(apply(src, &patch).unwrap(), src);
    }

    #[test]
    fn diff_then_apply_roundtrip() {
        let old = "hello world\n";
        let new = "hello rust\n";
        let patch = diff(old, new);
        let result = apply(old, &patch).unwrap();
        assert_eq!(result, new);
    }

    #[test]
    fn diff_then_apply_multiline_roundtrip() {
        let old = "alpha\nbeta\ngamma\ndelta\n";
        let new = "alpha\nBETA\ngamma\ndelta\n";
        let patch = diff(old, new);
        let result = apply(old, &patch).unwrap();
        assert_eq!(result, new);
    }

    #[test]
    fn diff_then_apply_add_lines_roundtrip() {
        let old = "first\nlast\n";
        let new = "first\nmiddle\nlast\n";
        let patch = diff(old, new);
        let result = apply(old, &patch).unwrap();
        assert_eq!(result, new);
    }

    #[test]
    fn diff_then_apply_remove_lines_roundtrip() {
        let old = "first\nmiddle\nlast\n";
        let new = "first\nlast\n";
        let patch = diff(old, new);
        let result = apply(old, &patch).unwrap();
        assert_eq!(result, new);
    }

    #[test]
    fn apply_context_mismatch_returns_error() {
        let old = "hello world\n";
        let new = "hello rust\n";
        let patch = diff(old, new);
        // Apply patch against wrong source
        let wrong_src = "goodbye world\n";
        let err = apply(wrong_src, &patch).unwrap_err();
        assert!(matches!(err, DiffError::ContextMismatch { .. }));
    }

    #[test]
    fn diff_preserves_empty_string() {
        let patch = diff("", "");
        assert!(patch.is_empty());
        let result = apply("", &patch).unwrap();
        assert_eq!(result, "");
    }
}
