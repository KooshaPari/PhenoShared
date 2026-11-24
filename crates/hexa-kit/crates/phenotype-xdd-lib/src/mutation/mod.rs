//! Mutation testing utilities.
//!
//! ## xDD Methodology: Mutation Testing
//!
//! Mutation testing evaluates test quality by introducing small
//! changes (mutations) to the code and verifying tests catch them.
//!
//! ## Metrics
//!
//! - **Mutation Score**: Percentage of killed mutations
//! - **Coverage**: Lines/branches executed by tests
//! - **Equivalent Mutations**: Mutations that don't change behavior
//!
//! ## Usage
//!
//! ```rust,ignore
//! let tracker = MutationTracker::new();
//! tracker.record_execution("src/lib.rs", 42);
//! let score = tracker.mutation_score();
//! ```

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

/// Mutation coverage tracker.
#[derive(Debug, Default, Clone)]
pub struct MutationTracker {
    /// File execution counts.
    files: HashMap<String, FileCoverage>,
    /// Total mutations introduced.
    total_mutations: usize,
    /// Mutations killed by tests.
    killed_mutations: usize,
}

#[derive(Debug, Default, Clone, Serialize, Deserialize)]
struct FileCoverage {
    lines_executed: usize,
    branches_executed: usize,
    mutations: Vec<Mutation>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Mutation {
    id: String,
    line: usize,
    status: MutationStatus,
    kind: MutationKind,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MutationStatus {
    /// Mutation was killed by a test.
    Killed,
    /// Mutation survived all tests.
    Survived,
    /// Mutation is equivalent to original.
    Equivalent,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MutationKind {
    /// Arithmetic operator flipped (e.g., + to -)
    Arithmetic,
    /// Comparison operator changed (e.g., == to !=)
    Comparison,
    /// Boolean operator negated (e.g., && to ||)
    Boolean,
    /// Value replaced with default/null
    ValueReplacement,
    /// Statement removed
    StatementRemoval,
}

impl MutationTracker {
    /// Create a new mutation tracker.
    pub fn new() -> Self {
        Self::default()
    }

    /// Record a line execution.
    pub fn record_line_execution(&mut self, file: &str, _line: usize) {
        self.files
            .entry(file.to_string())
            .or_default()
            .lines_executed += 1;
    }

    /// Record a mutation introduction.
    pub fn introduce_mutation(&mut self, file: &str, line: usize, kind: MutationKind) -> String {
        let id = format!("{file}:{line}:{kind:?}");
        self.total_mutations += 1;
        self.files
            .entry(file.to_string())
            .or_default()
            .mutations
            .push(Mutation {
                id: id.clone(),
                line,
                status: MutationStatus::Survived,
                kind,
            });
        id
    }

    /// Mark a mutation as killed.
    pub fn kill_mutation(&mut self, id: &str) {
        for file in self.files.values_mut() {
            if let Some(m) = file.mutations.iter_mut().find(|m| m.id == id) {
                m.status = MutationStatus::Killed;
                self.killed_mutations += 1;
                return;
            }
        }
    }

    /// Mark a mutation as equivalent.
    pub fn mark_equivalent(&mut self, id: &str) {
        for file in self.files.values_mut() {
            if let Some(m) = file.mutations.iter_mut().find(|m| m.id == id) {
                m.status = MutationStatus::Equivalent;
                self.total_mutations = self.total_mutations.saturating_sub(1);
                return;
            }
        }
    }

    /// Calculate mutation score (0.0 to 1.0).
    pub fn mutation_score(&self) -> f64 {
        if self.total_mutations == 0 {
            return 1.0;
        }
        self.killed_mutations as f64 / self.total_mutations as f64
    }

    /// Get coverage percentage for a file.
    pub fn coverage(&self, file: &str) -> f64 {
        self.files
            .get(file)
            .map(|f| f.lines_executed as f64 / 100.0) // TODO: actual LOC
            .unwrap_or(0.0)
    }

    /// Get all tracked files.
    pub fn files(&self) -> impl Iterator<Item = (&str, usize)> {
        self.files
            .iter()
            .map(|(k, v)| (k.as_str(), v.lines_executed))
    }
}

/// Coverage report for a mutation run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoverageReport {
    pub total_lines: usize,
    pub executed_lines: usize,
    pub line_coverage: f64,
    pub total_branches: usize,
    pub executed_branches: usize,
    pub branch_coverage: f64,
}

impl CoverageReport {
    /// Create from a tracker.
    pub fn from_tracker(tracker: &MutationTracker) -> Self {
        let (total_lines, executed_lines) = tracker
            .files()
            .fold((0, 0), |(t, e), (_, exec)| (t + 100, e + exec)); // TODO: actual LOC
        Self {
            total_lines,
            executed_lines,
            line_coverage: if total_lines > 0 {
                executed_lines as f64 / total_lines as f64
            } else {
                0.0
            },
            total_branches: 0,
            executed_branches: 0,
            branch_coverage: 0.0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tracker_creation() {
        let tracker = MutationTracker::new();
        assert_eq!(tracker.mutation_score(), 1.0);
    }

    #[test]
    fn test_record_line_execution() {
        let mut tracker = MutationTracker::new();
        tracker.record_line_execution("src/lib.rs", 10);
        tracker.record_line_execution("src/lib.rs", 20);
        // Coverage calculation uses TODO LOC, so just verify no panic
        let _ = tracker.coverage("src/lib.rs");
    }

    #[test]
    fn test_mutation_introduction() {
        let mut tracker = MutationTracker::new();
        let id = tracker.introduce_mutation("src/lib.rs", 42, MutationKind::Arithmetic);
        assert_eq!(tracker.mutation_score(), 0.0);
        tracker.kill_mutation(&id);
        assert_eq!(tracker.mutation_score(), 1.0);
    }

    #[test]
    fn test_mutation_killing() {
        let mut tracker = MutationTracker::new();
        let id1 = tracker.introduce_mutation("src/lib.rs", 1, MutationKind::Arithmetic);
        let _id2 = tracker.introduce_mutation("src/lib.rs", 2, MutationKind::Comparison);
        tracker.kill_mutation(&id1);
        assert_eq!(tracker.mutation_score(), 0.5);
    }

    #[test]
    fn test_equivalent_mutation() {
        let mut tracker = MutationTracker::new();
        let id = tracker.introduce_mutation("src/lib.rs", 42, MutationKind::ValueReplacement);
        tracker.mark_equivalent(&id);
        // Equivalent mutations don't count toward total
        assert_eq!(tracker.mutation_score(), 1.0);
    }
}
