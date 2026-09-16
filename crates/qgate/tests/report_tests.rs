// @trace QG-RPT-001: machine-readable JSON report + human tree summary
// Tests for report generation and output format.

use qgate::checks::{CheckCategory, CheckMatrix, CheckResult, CheckStatus};
use qgate::coverage::{CoverageNode, CoverageTree};
use qgate::report::{GateReport, GateStatus};

/// QG-RPT-001: gate report with all-pass produces GateStatus::Pass
#[test]
fn all_pass_produces_pass_status() {
    let coverage = CoverageTree {
        threshold: 85.0,
        nodes: vec![CoverageNode {
            path: "src/lib.rs".into(),
            line_rate: 0.90,
            branch_rate: 0.88,
            lines_covered: 90,
            lines_valid: 100,
            children: vec![],
        }],
    };
    let matrix = CheckMatrix::from_results(vec![CheckResult {
        category: CheckCategory::Unit,
        status: CheckStatus::Passed,
        score: Some(100.0),
        threshold: Some(100.0),
        details: String::new(),
    }]);
    let report = GateReport::new(coverage, matrix);
    assert_eq!(report.status, GateStatus::Pass);
}

/// QG-RPT-002: gate report with coverage failure produces GateStatus::Fail
#[test]
fn coverage_fail_produces_fail_status() {
    let coverage = CoverageTree {
        threshold: 85.0,
        nodes: vec![CoverageNode {
            path: "src/weak.rs".into(),
            line_rate: 0.40,
            branch_rate: 0.40,
            lines_covered: 40,
            lines_valid: 100,
            children: vec![],
        }],
    };
    let matrix = CheckMatrix::from_results(vec![]);
    let report = GateReport::new(coverage, matrix);
    assert_eq!(report.status, GateStatus::Fail);
}

/// QG-RPT-003: report serializes to valid JSON with required fields
#[test]
fn report_json_has_required_fields() {
    let coverage = CoverageTree {
        threshold: 85.0,
        nodes: vec![],
    };
    let matrix = CheckMatrix::from_results(vec![]);
    let report = GateReport::new(coverage, matrix);
    let json = serde_json::to_string(&report).expect("serialize");
    assert!(json.contains("\"status\""));
    assert!(json.contains("\"coverage\""));
    assert!(json.contains("\"checks\""));
    assert!(json.contains("\"timestamp\""));
}

/// QG-RPT-004: human tree summary contains pass/fail markers
#[test]
fn human_summary_contains_markers() {
    let coverage = CoverageTree {
        threshold: 85.0,
        nodes: vec![
            CoverageNode {
                path: "src/pass.rs".into(),
                line_rate: 0.90,
                branch_rate: 0.90,
                lines_covered: 90,
                lines_valid: 100,
                children: vec![],
            },
            CoverageNode {
                path: "src/fail.rs".into(),
                line_rate: 0.50,
                branch_rate: 0.50,
                lines_covered: 50,
                lines_valid: 100,
                children: vec![],
            },
        ],
    };
    let matrix = CheckMatrix::from_results(vec![]);
    let report = GateReport::new(coverage, matrix);
    let summary = report.render_summary();
    // should contain PASS and FAIL markers for the two nodes
    assert!(summary.contains("PASS") || summary.contains("✓") || summary.contains("ok"));
    assert!(summary.contains("FAIL") || summary.contains("✗") || summary.contains("fail"));
}

/// QG-RPT-005: exit code is 0 for pass, 1 for fail
#[test]
fn exit_codes() {
    assert_eq!(GateStatus::Pass.exit_code(), 0);
    assert_eq!(GateStatus::Fail.exit_code(), 1);
}
