//! Real progress metrics from a [`CoverageMatrix`] — percent covered and velocity.

use serde::{Deserialize, Serialize};

use crate::matrix::{CoverageMatrix, CoverageState};

/// Snapshot of coverage progress derived from a matrix (not fabricated task %).
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct ProgressSnapshot {
    /// Total matrix cells counted as criteria.
    pub total_criteria: usize,
    pub covered: usize,
    pub partial: usize,
    pub missing: usize,
    pub conflict: usize,
    /// Percent of cells in [`CoverageState::Covered`], 0–100.
    pub percent_covered: f32,
    /// Delta covered vs a prior snapshot (0 when taken alone).
    pub slope: f32,
}

/// Build a progress snapshot from the current matrix cell coverage states.
pub fn snapshot(matrix: &CoverageMatrix) -> ProgressSnapshot {
    let mut covered = 0usize;
    let mut partial = 0usize;
    let mut missing = 0usize;
    let mut conflict = 0usize;

    for cell in matrix.cells.values() {
        match cell.coverage {
            CoverageState::Covered => covered += 1,
            CoverageState::Partial | CoverageState::Stale => partial += 1,
            CoverageState::Missing => missing += 1,
            CoverageState::Conflict => conflict += 1,
        }
    }

    let total_criteria = covered + partial + missing + conflict;
    let percent_covered = if total_criteria == 0 {
        0.0
    } else {
        (covered as f32 / total_criteria as f32) * 100.0
    };

    ProgressSnapshot {
        total_criteria,
        covered,
        partial,
        missing,
        conflict,
        percent_covered,
        slope: 0.0,
    }
}

/// Velocity: change in covered cell count between two snapshots.
pub fn slope(prev: &ProgressSnapshot, cur: &ProgressSnapshot) -> f32 {
    (cur.covered as f32) - (prev.covered as f32)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::matrix::MatrixCell;
    use chrono::Utc;
    use indexmap::IndexMap;

    fn cell(from: &str, to: &str, coverage: CoverageState) -> MatrixCell {
        MatrixCell {
            from: from.to_string(),
            to: to.to_string(),
            trace_links: vec![],
            coverage,
        }
    }

    fn matrix_with(states: &[CoverageState]) -> CoverageMatrix {
        let mut cells = IndexMap::new();
        for (i, state) in states.iter().enumerate() {
            let from = format!("test:T-{i}");
            let to = format!("FR-{i}");
            cells.insert((from.clone(), to.clone()), cell(&from, &to, *state));
        }
        CoverageMatrix {
            cells,
            generated_at: Utc::now(),
        }
    }

    #[test]
    fn snapshot_counts_coverage_states() {
        let matrix = matrix_with(&[
            CoverageState::Covered,
            CoverageState::Covered,
            CoverageState::Partial,
            CoverageState::Missing,
            CoverageState::Conflict,
            CoverageState::Stale,
        ]);
        let snap = snapshot(&matrix);
        assert_eq!(snap.total_criteria, 6);
        assert_eq!(snap.covered, 2);
        assert_eq!(snap.partial, 2); // Partial + Stale
        assert_eq!(snap.missing, 1);
        assert_eq!(snap.conflict, 1);
        assert!((snap.percent_covered - (2.0 / 6.0 * 100.0)).abs() < f32::EPSILON);
        assert_eq!(snap.slope, 0.0);
    }

    #[test]
    fn snapshot_empty_matrix_zero_percent() {
        let snap = snapshot(&CoverageMatrix::default());
        assert_eq!(snap.total_criteria, 0);
        assert_eq!(snap.percent_covered, 0.0);
    }

    #[test]
    fn slope_delta_covered_between_snapshots() {
        let prev = snapshot(&matrix_with(&[
            CoverageState::Covered,
            CoverageState::Missing,
        ]));
        let cur = snapshot(&matrix_with(&[
            CoverageState::Covered,
            CoverageState::Covered,
            CoverageState::Partial,
        ]));
        assert_eq!(slope(&prev, &cur), 1.0);
        assert_eq!(prev.covered, 1);
        assert_eq!(cur.covered, 2);
    }
}
