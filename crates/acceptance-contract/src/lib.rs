mod evaluate;
pub mod types;

use anyhow::{anyhow, Result};
use std::collections::HashMap;
use std::path::Path;
use std::process::Command;

// Re-export public types so downstream callers keep the same API.
pub use types::{
    AcceptanceContract, BaselineDelta, BaselineEntry, BaselineFile, ExecutionContext,
    Requirement, RequirementResult, ScoreCard, load_baseline, load_contract, save_baseline,
};

// ---------------------------------------------------------------------------
// Core: run_acceptance
// ---------------------------------------------------------------------------

pub fn run_acceptance(
    contract_path: &Path,
    baseline_path: &Path,
    workspace_root: &Path,
    options: ExecutionContext,
) -> Result<ScoreCard> {
    let contract = load_contract(contract_path)?;
    let mut baseline = load_baseline(baseline_path)?;
    let mut card = ScoreCard {
        contract_path: contract_path.to_path_buf(),
        hard_requirements: Vec::new(),
        soft_requirements: Vec::new(),
        hard_passed: true,
        total_soft_score: 0.0,
        max_soft_score: 0.0,
        soft_percentage: 0.0,
        delegated_checks: Vec::new(),
    };

    let delegated = delegate_context(workspace_root, options.skip_delegation)?;
    card.delegated_checks = delegated;

    for req in &contract.hard_requirements {
        let result = evaluate::evaluate_requirement(req, &mut baseline, true)?;
        if !result.passed {
            card.hard_passed = false;
        }
        card.hard_requirements.push(result);
    }

    for req in &contract.soft_requirements {
        let result = evaluate::evaluate_requirement(req, &mut baseline, false)?;
        let max = req.weight.unwrap_or(1.0);
        card.max_soft_score += max;
        card.total_soft_score += result.score.unwrap_or(0.0);
        card.soft_requirements.push(result);
    }

    if card.max_soft_score > 0.0 {
        card.soft_percentage = (card.total_soft_score / card.max_soft_score) * 100.0;
    }

    if options.update_baseline {
        let mut next = BaselineFile {
            schema_version: "1.0".to_string(),
            requirements: HashMap::new(),
        };

        for result in card
            .hard_requirements
            .iter()
            .chain(card.soft_requirements.iter())
        {
            next.requirements.insert(
                result.id.clone(),
                BaselineEntry {
                    value: result.value.clone(),
                    score: result.score,
                },
            );
        }

        save_baseline(baseline_path, &next)?;
    }

    Ok(card)
}

// ---------------------------------------------------------------------------
// Delegation
// ---------------------------------------------------------------------------

fn delegate_context(workspace_root: &Path, skip: bool) -> Result<Vec<String>> {
    if skip {
        return Ok(Vec::new());
    }

    let mut delegated = Vec::new();

    match run_quality_gate_delegation(workspace_root) {
        Ok(output) => delegated.push(format!("qgate: ok ({})", output)),
        Err(err) => delegated.push(format!("qgate: failed ({})", err)),
    }

    match run_legacy_scan_delegation(workspace_root) {
        Ok(output) => delegated.push(format!("legacy-scan: ok ({})", output)),
        Err(err) => delegated.push(format!("legacy-scan: failed ({})", err)),
    }

    match run_bench_guard_delegation(workspace_root) {
        Ok(output) => delegated.push(format!("bench-guard: ok ({})", output)),
        Err(err) => delegated.push(format!("bench-guard: failed ({})", err)),
    }

    Ok(delegated)
}

fn run_quality_gate_delegation(workspace_root: &Path) -> Result<String> {
    let output = Command::new("cargo")
        .args([
            "run",
            "-p",
            "qgate",
            "--",
            "run",
            "--path",
            workspace_root.to_string_lossy().as_ref(),
        ])
        .output()?;

    if !output.status.success() {
        return Err(anyhow!("qgate delegation failed"));
    }

    Ok(String::from_utf8(output.stdout)?.trim().to_string())
}

fn run_legacy_scan_delegation(workspace_root: &Path) -> Result<String> {
    let output = Command::new("cargo")
        .args([
            "run", "-p", "legacy-scan", "--", "--path",
            workspace_root.to_string_lossy().as_ref(), "--json",
        ])
        .output()?;

    if !output.status.success() {
        return Err(anyhow!("legacy-scan delegation failed"));
    }

    Ok(String::from_utf8(output.stdout)?.trim().to_string())
}

pub(crate) fn run_bench_guard_probe(workspace_root: &Path) -> Result<String> {
    let baseline = workspace_root.join("docs/reference/perf_baseline.json");
    let baseline = baseline.to_string_lossy();
    let output = Command::new("cargo")
        .args([
            "run", "-p", "bench-guard", "--", "--baseline",
            baseline.as_ref(),
        ])
        .current_dir(workspace_root)
        .output()?;

    if !output.status.success() {
        return Err(anyhow!("bench-guard delegation failed"));
    }

    Ok(String::from_utf8(output.stdout)?.trim().to_string())
}

fn run_bench_guard_delegation(workspace_root: &Path) -> Result<String> {
    run_bench_guard_probe(workspace_root)
}

// ---------------------------------------------------------------------------
// Output: render_markdown
// ---------------------------------------------------------------------------

pub fn render_markdown(score_card: &ScoreCard) -> String {
    let mut out = String::new();
    out.push_str("# Acceptance Scorecard\n\n");
    out.push_str(&format!(
        "- Contract: `{}`\n",
        score_card.contract_path.display()
    ));
    out.push_str(&format!(
        "- Hard requirements passed: `{}`\n",
        score_card.hard_passed
    ));
    out.push_str(&format!(
        "- Soft score: {:.2} / {:.2} ({:.1}%)\n\n",
        score_card.total_soft_score, score_card.max_soft_score, score_card.soft_percentage
    ));

    out.push_str("## Hard requirements\n");
    for req in &score_card.hard_requirements {
        out.push_str(&format!(
            "- `{}` {}\n",
            req.id,
            if req.passed { "PASS" } else { "FAIL" }
        ));
        out.push_str(&format!("  - probe: {}\n", req.probe));
        out.push_str(&format!("  - value: `{}`\n", req.value));
        if let Some(msg) = &req.message {
            out.push_str(&format!("  - detail: {}\n", msg));
        }
    }

    out.push_str("\n## Soft requirements\n");
    for req in &score_card.soft_requirements {
        out.push_str(&format!(
            "- `{}` {:.2}/{:.2}\n",
            req.id,
            req.score.unwrap_or(0.0),
            req.score.unwrap_or(0.0)
        ));
        out.push_str(&format!("  - probe: {}\n", req.probe));
        out.push_str(&format!("  - value: `{}`\n", req.value));
        if let Some(delta) = &req.baseline_comparison {
            out.push_str(&format!("  - baseline: `{}`\n", delta.baseline));
            out.push_str(&format!("  - changed: {}\n", delta.changed));
            if let Some(ratio) = delta.score_ratio {
                out.push_str(&format!("  - ratio: {:.3}\n", ratio));
            }
        }
        if let Some(msg) = &req.message {
            out.push_str(&format!("  - detail: {}\n", msg));
        }
    }

    if !score_card.delegated_checks.is_empty() {
        out.push_str("\n## Delegated checks\n");
        for item in &score_card.delegated_checks {
            out.push_str(&format!("- {}\n", item));
        }
    }

    out
}
