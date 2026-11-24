//! Gate runner — runs the four sequential Phase 2/3 gates against the
//! current workspace and reports a typed verdict that the CLI can render
//! via [`crate::report`].

use std::path::PathBuf;

/// Status of a single gate after it has been evaluated.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Status {
    /// The gate ran to completion and produced no violations.
    Passed,
    /// The gate ran but at least one violation was reported.
    Failed,
    /// The gate could not be evaluated (missing tool, invalid input).
    Skipped,
}

/// A single governance gate that contributes to the overall PTX verdict.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Gate {
    /// Stable gate name (e.g. `fmt`, `clippy`, `test`, `audit`).
    pub name: String,
    /// Wall-clock duration of the gate run in milliseconds.
    pub elapsed_ms: u64,
    /// Final verdict.
    pub status: Status,
    /// Captured output snippets — never the full loud output, only
    /// the first 1 KiB per stream.
    pub stdout_tail: String,
    /// First 1 KiB of the captured stderr stream.
    pub stderr_tail: String,
    /// Human-readable detail string emitted into `report.md`. Markdown-safe
    /// (newlines collapsed by `report::render_markdown`).
    pub detail: String,
}

impl Gate {
    /// Construct a passed gate (test helper for unit tests).
    #[must_use]
    pub fn passed(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            elapsed_ms: 0,
            status: Status::Passed,
            stdout_tail: String::new(),
            stderr_tail: String::new(),
            detail: String::new(),
        }
    }

    /// Attach a human-readable detail string to an existing gate.
    /// Builder pattern so callers do not need to update this constructor
    /// each time a new detail field is added.
    #[must_use]
    pub fn with_detail(mut self, detail: impl Into<String>) -> Self {
        self.detail = detail.into();
        self
    }
}

/// The sequence of gates PTX will evaluate per `ptx check`.
#[must_use]
pub const fn default_sequence() -> &'static [&'static str] {
    &["fmt", "clippy", "test", "audit"]
}

/// Wired gates array (stub). Real implementations will be wired in later
/// phases; this enumerates the names so `crate::all_passed`'s usage site
/// is consistent.
#[must_use]
pub fn nop_gates() -> Vec<Gate> {
    default_sequence()
        .iter()
        .map(|name| Gate::passed(*name))
        .collect()
}

/// Root directory the gate runner should evaluate. Defaults to the
/// current working directory but can be overridden per-invocation so
/// CI can run PTX against any workspace.
#[derive(Debug, Clone)]
pub struct GateContext {
    /// Absolute path to the workspace root.
    pub workspace_root: PathBuf,
}

impl GateContext {
    /// Use the current working directory as the workspace root.
    pub fn from_cwd() -> Result<Self, crate::PtxError> {
        let cwd = std::env::current_dir().map_err(|source| crate::PtxError::Io {
            path: PathBuf::from("<cwd>"),
            source,
        })?;
        Ok(Self {
            workspace_root: cwd,
        })
    }

    /// Use an explicit workspace root.
    #[must_use]
    pub fn new(workspace_root: PathBuf) -> Self {
        Self { workspace_root }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_sequence_lists_four_gates() {
        assert_eq!(default_sequence().len(), 4);
    }

    #[test]
    fn nop_gates_default_all_pass() {
        let gates = nop_gates();
        assert_eq!(gates.len(), 4);
        assert!(gates.iter().all(|g| g.status == Status::Passed));
    }

    #[test]
    fn gate_passed_constructor_sets_status() {
        let g = Gate::passed("fmt");
        assert_eq!(g.name, "fmt");
        assert_eq!(g.status, Status::Passed);
    }
}
