//! Mutation testing utilities tests.
//!
//! ## xDD Methodology: Mutation Testing
//!
//! These tests verify the mutation tracking functionality.

use phenotype_xdd_lib::mutation::{CoverageReport, MutationKind, MutationStatus, MutationTracker};

#[test]
fn test_mutation_tracker_initialization() {
    let tracker = MutationTracker::new();
    assert_eq!(tracker.mutation_score(), 1.0); // No mutations = perfect score
}

#[test]
fn test_record_line_execution() {
    let mut tracker = MutationTracker::new();
    tracker.record_line_execution("src/lib.rs", 10);
    tracker.record_line_execution("src/lib.rs", 20);
    tracker.record_line_execution("src/lib.rs", 30);

    let files: Vec<_> = tracker.files().collect();
    assert_eq!(files.len(), 1);
    assert_eq!(files[0].0, "src/lib.rs");
}

#[test]
fn test_mutation_introduction() {
    let mut tracker = MutationTracker::new();

    // Introduce a mutation
    let id = tracker.introduce_mutation("src/lib.rs", 42, MutationKind::Arithmetic);

    // Score should be 0% (mutation survived)
    assert_eq!(tracker.mutation_score(), 0.0);

    // Kill the mutation
    tracker.kill_mutation(&id);

    // Score should be 100%
    assert_eq!(tracker.mutation_score(), 1.0);
}

#[test]
fn test_multiple_mutations() {
    let mut tracker = MutationTracker::new();

    let id1 = tracker.introduce_mutation("src/lib.rs", 1, MutationKind::Arithmetic);
    let _id2 = tracker.introduce_mutation("src/lib.rs", 2, MutationKind::Comparison);
    let id3 = tracker.introduce_mutation("src/lib.rs", 3, MutationKind::Boolean);

    // Kill 2 out of 3
    tracker.kill_mutation(&id1);
    tracker.kill_mutation(&id3);

    // Score should be 66.67%
    let score = tracker.mutation_score();
    assert!((score - 0.666).abs() < 0.01);
}

#[test]
fn test_equivalent_mutations() {
    let mut tracker = MutationTracker::new();

    let id = tracker.introduce_mutation("src/lib.rs", 42, MutationKind::ValueReplacement);

    // Mark as equivalent (doesn't affect behavior)
    tracker.mark_equivalent(&id);

    // Should not count toward total
    assert_eq!(tracker.mutation_score(), 1.0);
}

#[test]
fn test_coverage_report() {
    let tracker = MutationTracker::new();
    let report = CoverageReport::from_tracker(&tracker);

    assert_eq!(report.total_lines, 0);
    assert_eq!(report.executed_lines, 0);
    assert_eq!(report.line_coverage, 0.0);
}

#[test]
fn test_mutation_status_variants() {
    assert_eq!(format!("{:?}", MutationStatus::Killed), "Killed");
    assert_eq!(format!("{:?}", MutationStatus::Survived), "Survived");
    assert_eq!(format!("{:?}", MutationStatus::Equivalent), "Equivalent");
}

#[test]
fn test_mutation_kind_variants() {
    assert_eq!(format!("{:?}", MutationKind::Arithmetic), "Arithmetic");
    assert_eq!(format!("{:?}", MutationKind::Comparison), "Comparison");
    assert_eq!(format!("{:?}", MutationKind::Boolean), "Boolean");
    assert_eq!(
        format!("{:?}", MutationKind::ValueReplacement),
        "ValueReplacement"
    );
    assert_eq!(
        format!("{:?}", MutationKind::StatementRemoval),
        "StatementRemoval"
    );
}
