// @trace QG-COV-001: granular-recursive coverage gate
// Tests for coverage parsing and tree-walk enforcement.

use qgate::coverage::{parse_cobertura, parse_lcov, CoverageNode, CoverageTree};

/// QG-COV-001: overall coverage ≥ threshold passes
#[test]
fn overall_above_threshold_passes() {
    let tree = CoverageTree {
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
    assert!(tree.all_pass());
}

/// QG-COV-002: module below threshold fails even if overall passes
#[test]
fn module_below_threshold_fails() {
    let tree = CoverageTree {
        threshold: 85.0,
        nodes: vec![
            CoverageNode {
                path: "src/a.rs".into(),
                line_rate: 0.95,
                branch_rate: 0.95,
                lines_covered: 95,
                lines_valid: 100,
                children: vec![],
            },
            CoverageNode {
                path: "src/b.rs".into(),
                line_rate: 0.50, // below threshold
                branch_rate: 0.50,
                lines_covered: 50,
                lines_valid: 100,
                children: vec![],
            },
        ],
    };
    // even though average would be 72.5% covered lines, the gate must fail
    // because src/b.rs is below 85%
    assert!(!tree.all_pass());
}

/// QG-COV-003: recursive — nested module below threshold fails entire tree
#[test]
fn nested_module_below_threshold_fails() {
    let tree = CoverageTree {
        threshold: 85.0,
        nodes: vec![CoverageNode {
            path: "src".into(),
            line_rate: 0.90,
            branch_rate: 0.90,
            lines_covered: 90,
            lines_valid: 100,
            children: vec![CoverageNode {
                path: "src/deep".into(),
                line_rate: 0.90,
                branch_rate: 0.90,
                lines_covered: 90,
                lines_valid: 100,
                children: vec![CoverageNode {
                    path: "src/deep/hidden.rs".into(),
                    line_rate: 0.60, // hidden deep failure
                    branch_rate: 0.60,
                    lines_covered: 60,
                    lines_valid: 100,
                    children: vec![],
                }],
            }],
        }],
    };
    assert!(!tree.all_pass());
}

/// QG-COV-004: all nodes at exactly threshold pass
#[test]
fn exactly_at_threshold_passes() {
    let tree = CoverageTree {
        threshold: 85.0,
        nodes: vec![CoverageNode {
            path: "src/exact.rs".into(),
            line_rate: 0.85,
            branch_rate: 0.85,
            lines_covered: 85,
            lines_valid: 100,
            children: vec![],
        }],
    };
    assert!(tree.all_pass());
}

/// QG-COV-005: parse minimal cobertura XML and return tree
#[test]
fn parse_cobertura_minimal() {
    let xml = r#"<?xml version="1.0" ?>
<coverage line-rate="0.90" branch-rate="0.88" lines-covered="90" lines-valid="100">
  <packages>
    <package name="src" line-rate="0.90" branch-rate="0.88">
      <classes>
        <class name="lib" filename="src/lib.rs" line-rate="0.90" branch-rate="0.88">
        </class>
      </classes>
    </package>
  </packages>
</coverage>"#;
    let tree = parse_cobertura(xml, 85.0).expect("parse should succeed");
    assert!(!tree.nodes.is_empty(), "should parse at least one node");
    assert!(tree.threshold == 85.0);
}

/// QG-COV-006: parse lcov tracefile
#[test]
fn parse_lcov_minimal() {
    let lcov = "TN:\nSF:src/lib.rs\nDA:1,1\nDA:2,1\nDA:3,0\nLH:2\nLF:3\nend_of_record\n";
    let tree = parse_lcov(lcov, 85.0).expect("parse should succeed");
    assert!(!tree.nodes.is_empty());
    // 2/3 = 66.6% — below threshold
    assert!(!tree.all_pass());
}

/// QG-COV-007: coverage node renders pass/fail correctly
#[test]
fn node_pass_fail_rendering() {
    let node = CoverageNode {
        path: "src/mod.rs".into(),
        line_rate: 0.92,
        branch_rate: 0.91,
        lines_covered: 92,
        lines_valid: 100,
        children: vec![],
    };
    assert!(node.passes(85.0));
    assert!(!node.passes(95.0));
}

/// QG-COV-008: tree renders as human-readable string
#[test]
fn tree_renders_to_string() {
    let tree = CoverageTree {
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
    let rendered = tree.render_tree();
    assert!(rendered.contains("src/lib.rs"));
    assert!(rendered.contains("90.0%") || rendered.contains("90%"));
}
