use serde::{Deserialize, Serialize};

/// A single line in a diff hunk.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum DiffLine {
    /// Line present only in the old text (removal).
    Removed(String),
    /// Line present only in the new text (addition).
    Added(String),
    /// Line identical in both texts (context).
    Context(String),
}

impl DiffLine {
    /// The text content of the line (without the diff sigil).
    #[must_use]
    pub fn content(&self) -> &str {
        match self {
            DiffLine::Removed(s) | DiffLine::Added(s) | DiffLine::Context(s) => s.as_str(),
        }
    }
}

/// Hunk positional metadata matching the unified-diff `@@ -a,b +c,d @@` header.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HunkHeader {
    /// Starting line in the old file (1-based).
    pub old_start: usize,
    /// Number of lines from the old file in this hunk.
    pub old_lines: usize,
    /// Starting line in the new file (1-based).
    pub new_start: usize,
    /// Number of lines from the new file in this hunk.
    pub new_lines: usize,
}

/// A hunk: one contiguous changed region with surrounding context.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Hunk {
    pub header: HunkHeader,
    pub lines: Vec<DiffLine>,
}

/// A complete unified diff between two text inputs.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UnifiedDiff {
    pub hunks: Vec<Hunk>,
}

impl UnifiedDiff {
    /// `true` when there are no changes.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.hunks.is_empty()
    }
}
