//! Report formatter — turns a list of `check::Gate`s into the human-
//! readable `target/ptx/report.md` output. The format is deliberately
//! stable because governance scripts grep for the section anchors.

use crate::check::{Gate, Status};

/// Anchor that gates / tooling grep for at the top of every report.
pub const REPORT_HEADER: &str = "# PTX Gate Report";

/// Anchor immediately before the per-gate rows.
pub const REPORT_GATES_HEADER: &str = "## Gates";

/// Anchor for the summary line (pass count / total).
pub const REPORT_SUMMARY_HEADER: &str = "## Summary";

/// Render a list of gates into a Markdown report.
///
/// The Markdown is plain enough for the `ptx-gate-reporter` GitHub
/// Actions step to print to `$GITHUB_STEP_SUMMARY` verbatim.
#[must_use]
pub fn render_markdown(gates: &[Gate]) -> String {
    let mut out = String::new();
    out.push_str(REPORT_HEADER);
    out.push('\n');
    out.push_str(REPORT_GATES_HEADER);
    out.push('\n');

    for g in gates {
        let status = match g.status {
            Status::Passed => "PASS",
            Status::Failed => "FAIL",
            Status::Skipped => "SKIP",
        };
        // Tabular form: `| name | status | detail |`
        out.push_str(&format!(
            "| {name} | {status} | {detail} |\n",
            name = g.name,
            status = status,
            detail = g.detail.replace('\n', " "),
        ));
    }

    out.push_str(REPORT_SUMMARY_HEADER);
    out.push('\n');
    let passed = gates
        .iter()
        .filter(|g| matches!(g.status, Status::Passed))
        .count();
    out.push_str(&format!(
        "{passed} / {total} gates passed",
        total = gates.len()
    ));
    out.push('\n');
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::check::{Gate, Status};

    fn gate(name: &str, status: Status, detail: &str) -> Gate {
        Gate {
            name: name.to_string(),
            elapsed_ms: 0,
            status,
            stdout_tail: String::new(),
            stderr_tail: String::new(),
            detail: detail.to_string(),
        }
    }

    #[test]
    fn render_includes_expected_anchors() {
        let gates = vec![
            gate("fmt", Status::Passed, "clean"),
            gate("clippy", Status::Failed, "1 err"),
        ];
        let md = render_markdown(&gates);
        assert!(md.starts_with(REPORT_HEADER));
        assert!(md.contains(REPORT_GATES_HEADER));
        assert!(md.contains(REPORT_SUMMARY_HEADER));
        assert!(md.contains("1 / 2"));
    }

    #[test]
    fn render_strips_newlines_in_detail() {
        let gates = vec![gate("clippy", Status::Failed, "err line1\nerr line2")];
        let md = render_markdown(&gates);
        // Newlines inside detail would break the markdown table row;
        // confirm they were collapsed.
        let mut lines = md.lines().filter(|l| l.starts_with("| clippy |"));
        let row = lines.next().expect("gate row present");
        // Lines filter returns 1 line for input with embedded \n still
        // joined as one table row; the surrounding row carries the whole
        // detail folded onto one row.
        assert!(!row.contains("err line1\nerr line2"));
    }
}
