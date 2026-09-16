// @trace QG-CHK-001: all-check-types orchestration + per-category thresholds
// Tests for check-type matrix and threshold enforcement.

use qgate::checks::{CheckCategory, CheckMatrix, CheckResult, CheckStatus};

/// QG-CHK-001: all categories present in a default matrix
#[test]
fn default_matrix_contains_all_categories() {
    let matrix = CheckMatrix::default();
    let categories: Vec<_> = matrix.categories().collect();
    let names: Vec<&str> = categories.iter().map(|c| c.category.name()).collect();

    assert!(names.contains(&"unit"), "missing unit");
    assert!(names.contains(&"integration"), "missing integration");
    assert!(names.contains(&"e2e"), "missing e2e");
    assert!(names.contains(&"chaos"), "missing chaos");
    assert!(names.contains(&"perf"), "missing perf");
    assert!(names.contains(&"property"), "missing property");
    assert!(names.contains(&"mutation"), "missing mutation");
    assert!(
        names.contains(&"static_analysis"),
        "missing static_analysis"
    );
    assert!(names.contains(&"security"), "missing security");
    assert!(names.contains(&"a11y"), "missing a11y");
    // Spectrum extension: DAST + SAST (split from Security) + SBOM
    assert!(names.contains(&"dast"), "missing dast");
    assert!(names.contains(&"sast"), "missing sast");
    assert!(names.contains(&"sbom"), "missing sbom");
}

/// QG-CHK-002: N/A category does not count as failure
#[test]
fn na_category_does_not_fail() {
    let result = CheckResult {
        category: CheckCategory::A11y,
        status: CheckStatus::NotApplicable,
        score: None,
        threshold: None,
        details: "No UI detected".into(),
    };
    assert!(!result.is_failure());
}

/// QG-CHK-003: failed category counts as failure
#[test]
fn failed_category_is_failure() {
    let result = CheckResult {
        category: CheckCategory::Unit,
        status: CheckStatus::Failed,
        score: Some(72.0),
        threshold: Some(100.0),
        details: "3 tests failed".into(),
    };
    assert!(result.is_failure());
}

/// QG-CHK-004: matrix with all passed results passes overall
#[test]
fn all_passed_matrix_passes() {
    let results = vec![
        CheckResult {
            category: CheckCategory::Unit,
            status: CheckStatus::Passed,
            score: Some(100.0),
            threshold: Some(100.0),
            details: "All tests pass".into(),
        },
        CheckResult {
            category: CheckCategory::StaticAnalysis,
            status: CheckStatus::Passed,
            score: None,
            threshold: None,
            details: "0 warnings".into(),
        },
        CheckResult {
            category: CheckCategory::Security,
            status: CheckStatus::Passed,
            score: None,
            threshold: None,
            details: "0 findings".into(),
        },
    ];
    let matrix = CheckMatrix::from_results(results);
    assert!(matrix.all_pass());
}

/// QG-CHK-005: matrix with one failure fails overall
#[test]
fn one_failed_matrix_fails() {
    let results = vec![
        CheckResult {
            category: CheckCategory::Unit,
            status: CheckStatus::Passed,
            score: Some(100.0),
            threshold: Some(100.0),
            details: "All tests pass".into(),
        },
        CheckResult {
            category: CheckCategory::Chaos,
            status: CheckStatus::Failed,
            score: Some(60.0),
            threshold: Some(80.0),
            details: "Resiliency score below threshold".into(),
        },
    ];
    let matrix = CheckMatrix::from_results(results);
    assert!(!matrix.all_pass());
}

/// QG-CHK-006: perf check enforces threshold assertion
#[test]
fn perf_below_threshold_fails() {
    let result = CheckResult {
        category: CheckCategory::Perf,
        status: CheckStatus::Failed,
        score: Some(20_000.0), // ms — above 15s init threshold
        threshold: Some(15_000.0),
        details: "init time 20s exceeds 15s threshold".into(),
    };
    assert!(result.is_failure());
}

/// QG-CHK-007: mutation score below threshold fails
#[test]
fn mutation_below_threshold_fails() {
    let result = CheckResult {
        category: CheckCategory::Mutation,
        status: CheckStatus::Failed,
        score: Some(55.0),
        threshold: Some(75.0),
        details: "mutation score 55% < 75%".into(),
    };
    assert!(result.is_failure());
}

/// QG-CHK-008: check matrix serializes to JSON
#[test]
fn matrix_serializes_to_json() {
    let results = vec![CheckResult {
        category: CheckCategory::Unit,
        status: CheckStatus::Passed,
        score: Some(100.0),
        threshold: Some(100.0),
        details: String::new(),
    }];
    let matrix = CheckMatrix::from_results(results);
    let json = serde_json::to_string(&matrix).expect("should serialize");
    assert!(json.contains("unit") || json.contains("Unit"));
}

// QG-CHK-201: SAST result serializes in snake_case (matches runner JSON output)
#[test]
fn sast_serializes_in_snake_case() {
    let r = CheckResult {
        category: CheckCategory::Sast,
        status: CheckStatus::Passed,
        score: Some(0.0),
        threshold: Some(0.0),
        details: "0 findings".into(),
    };
    let json = serde_json::to_string(&r).expect("should serialize");
    assert!(
        json.contains("\"sast\""),
        "expected snake_case sast in {json}"
    );
}

// QG-CHK-202: DAST and SBOM serialize in snake_case
#[test]
fn dast_and_sbom_serialize_in_snake_case() {
    let r1 = CheckResult {
        category: CheckCategory::Dast,
        status: CheckStatus::Skipped,
        score: None,
        threshold: None,
        details: "no config".into(),
    };
    let r2 = CheckResult {
        category: CheckCategory::Sbom,
        status: CheckStatus::Passed,
        score: Some(1.0),
        threshold: Some(0.0),
        details: "ok".into(),
    };
    let j1 = serde_json::to_string(&r1).unwrap();
    let j2 = serde_json::to_string(&r2).unwrap();
    assert!(j1.contains("\"dast\""), "expected dast in {j1}");
    assert!(j2.contains("\"sbom\""), "expected sbom in {j2}");
}

// QG-CHK-203: Skipped DAST does NOT fail the gate (graceful when no schema)
#[test]
fn skipped_dast_does_not_fail() {
    let r = CheckResult {
        category: CheckCategory::Dast,
        status: CheckStatus::Skipped,
        score: None,
        threshold: None,
        details: "schemathesis not installed".into(),
    };
    assert!(!r.is_failure());
    assert!(r.is_applicable());
}

// QG-CHK-204: SBOM missing artifact counts as failure
#[test]
fn sbom_missing_artifact_is_failure() {
    let r = CheckResult {
        category: CheckCategory::Sbom,
        status: CheckStatus::Failed,
        score: Some(0.0),
        threshold: Some(0.0),
        details: "target/sbom.cdx.json not generated".into(),
    };
    assert!(r.is_failure());
}

// QG-CHK-205: Spectrum extension visible in default matrix
#[test]
fn default_matrix_contains_spectrum_extensions() {
    let matrix = CheckMatrix::default();
    let names: Vec<&str> = matrix.results.iter().map(|c| c.category.name()).collect();
    assert_eq!(names.iter().filter(|n| **n == "dast").count(), 1);
    assert_eq!(names.iter().filter(|n| **n == "sast").count(), 1);
    assert_eq!(names.iter().filter(|n| **n == "sbom").count(), 1);
}
