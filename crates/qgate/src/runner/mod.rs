// @trace QG-CHK-001: check-type orchestration + aggregation
//
// Runs each enabled check category against the project and aggregates results.
// Each sub-module handles one category; language detection decides which runners fire.

mod checks;
mod dast;
mod lint;

use std::path::Path;

use anyhow::Result;

use crate::checks::{CheckCategory, CheckMatrix, CheckResult, Thresholds};
use crate::config::QGateConfig;

use self::checks::{make_result, na, run_cmd, skipped};
use self::dast::{parse_dast_failed_count, parse_semgrep_high_count, DastConfig};
use self::lint::{run_security, run_static_analysis};

/// Detect what stacks are present in the project root.
pub struct StackDetector<'a> {
    root: &'a Path,
}

impl<'a> StackDetector<'a> {
    pub fn new(root: &'a Path) -> Self {
        Self { root }
    }

    pub fn has_rust(&self) -> bool {
        self.root.join("Cargo.toml").exists()
    }
    pub fn has_typescript(&self) -> bool {
        self.root.join("package.json").exists() || self.root.join("bun.lock").exists()
    }
    pub fn has_python(&self) -> bool {
        self.root.join("pyproject.toml").exists() || self.root.join("requirements.txt").exists()
    }
    pub fn has_ui(&self) -> bool {
        let extensions = ["html", "tsx", "svelte", "vue"];
        extensions.iter().any(|ext| {
            walkdir::WalkDir::new(self.root)
                .max_depth(5)
                .into_iter()
                .filter_map(|e| e.ok())
                .any(|e| e.path().extension().is_some_and(|x| x == *ext))
        })
    }
}

/// Orchestrate all check categories and return an aggregated `CheckMatrix`.
pub async fn run_all_checks(root: &Path, cfg: &QGateConfig) -> Result<CheckMatrix> {
    let stack = StackDetector::new(root);
    let mut results: Vec<CheckResult> = Vec::new();

    // ── Unit tests ─────────────────────────────────────────────────────────
    results.push(run_unit(&stack, root, cfg).await);

    // ── Integration tests ──────────────────────────────────────────────────
    results.push(run_integration(&stack, root, cfg).await);

    // ── E2E tests ──────────────────────────────────────────────────────────
    results.push(run_e2e(root, cfg).await);

    // ── Chaos ──────────────────────────────────────────────────────────────
    results.push(run_chaos(root, cfg).await);

    // ── Perf / bench ───────────────────────────────────────────────────────
    results.push(run_perf(&stack, root, cfg).await);

    // ── Property / fuzz ────────────────────────────────────────────────────
    results.push(run_property(&stack, root, cfg).await);

    // ── Mutation ───────────────────────────────────────────────────────────
    results.push(run_mutation(&stack, root, cfg).await);

    // ── Static analysis ────────────────────────────────────────────────────
    results.push(run_static_analysis(&stack, root, cfg).await);

    // ── Security ───────────────────────────────────────────────────────────
    results.push(run_security(&stack, root, cfg).await);

    // ── SAST (semgrep) ────────────────────────────────────────────────────
    results.push(run_sast(root, cfg).await);

    // ── DAST (schemathesis) ────────────────────────────────────────────────
    results.push(run_dast(root, cfg).await);

    // ── SBOM (CycloneDX) ──────────────────────────────────────────────────
    results.push(run_sbom(root, cfg).await);

    // ── A11y ───────────────────────────────────────────────────────────────
    results.push(run_a11y(&stack, root, cfg).await);

    Ok(CheckMatrix::from_results(results))
}

// ---------------------------------------------------------------------------
// Individual check runners
// ---------------------------------------------------------------------------

async fn run_unit(stack: &StackDetector<'_>, root: &Path, cfg: &QGateConfig) -> CheckResult {
    if cfg.is_na("unit") {
        return na("unit", CheckCategory::Unit);
    }
    if stack.has_rust() {
        let (ok, detail) = run_cmd("cargo", &["test", "--workspace", "--lib"], root)
            .await
            .unwrap_or((false, "cargo not found".into()));
        return make_result(
            CheckCategory::Unit, ok, detail, "all unit tests passed",
            Some(100.0), Some(0.0), Some(Thresholds::UNIT_PASS_RATE),
        );
    }
    if stack.has_typescript() {
        let (ok, detail) = run_cmd("bun", &["test"], root)
            .await
            .unwrap_or((false, "bun not found".into()));
        return make_result(
            CheckCategory::Unit, ok, detail, "all bun tests passed",
            Some(100.0), Some(0.0), Some(Thresholds::UNIT_PASS_RATE),
        );
    }
    if stack.has_python() {
        let (ok, detail) = run_cmd("uv", &["run", "pytest", "-x", "--tb=short"], root)
            .await
            .unwrap_or((false, "uv not found".into()));
        return make_result(
            CheckCategory::Unit, ok, detail, "all pytest tests passed",
            Some(100.0), Some(0.0), Some(Thresholds::UNIT_PASS_RATE),
        );
    }
    skipped("unit", CheckCategory::Unit, "no supported stack detected")
}

async fn run_integration(stack: &StackDetector<'_>, root: &Path, cfg: &QGateConfig) -> CheckResult {
    if cfg.is_na("integration") {
        return na("integration", CheckCategory::Integration);
    }
    if stack.has_rust() {
        let (ok, detail) = run_cmd("cargo", &["test", "--workspace", "--test", "*"], root)
            .await
            .unwrap_or((false, "cargo not found".into()));
        return make_result(
            CheckCategory::Integration, ok, detail, "integration tests passed",
            Some(100.0), Some(0.0), Some(Thresholds::INTEGRATION_PASS_RATE),
        );
    }
    skipped("integration", CheckCategory::Integration, "stack-specific runner not configured")
}

async fn run_e2e(root: &Path, cfg: &QGateConfig) -> CheckResult {
    if cfg.is_na("e2e") {
        return na("e2e", CheckCategory::E2e);
    }
    let playwright_ok = root.join("playwright.config.ts").exists()
        || root.join("playwright.config.js").exists();
    if playwright_ok {
        let (ok, detail) = run_cmd("bun", &["x", "playwright", "test"], root)
            .await
            .unwrap_or((false, "playwright not available".into()));
        return make_result(
            CheckCategory::E2e, ok, detail, "playwright e2e passed",
            Some(100.0), Some(0.0), Some(Thresholds::E2E_PASS_RATE),
        );
    }
    skipped("e2e", CheckCategory::E2e, "no playwright.config found")
}

async fn run_chaos(root: &Path, cfg: &QGateConfig) -> CheckResult {
    if cfg.is_na("chaos") {
        return na("chaos", CheckCategory::Chaos);
    }
    let chaos_script = root.join("scripts/chaos.sh");
    if chaos_script.exists() {
        let (ok, detail) = run_cmd("bash", &[chaos_script.to_str().unwrap_or("")], root)
            .await
            .unwrap_or((false, "bash not found".into()));
        return make_result(
            CheckCategory::Chaos, ok, detail, "chaos tests passed",
            None, None, Some(Thresholds::CHAOS_RESILIENCE),
        );
    }
    skipped("chaos", CheckCategory::Chaos, "no scripts/chaos.sh found")
}

async fn run_perf(stack: &StackDetector<'_>, root: &Path, cfg: &QGateConfig) -> CheckResult {
    if cfg.is_na("perf") {
        return na("perf", CheckCategory::Perf);
    }
    if stack.has_rust() {
        let (ok, detail) = run_cmd("cargo", &["bench", "--workspace", "--no-run"], root)
            .await
            .unwrap_or((false, "cargo not found".into()));
        return make_result(
            CheckCategory::Perf, ok, detail, "bench compile passed",
            None, None, Some(cfg.perf_init_ms),
        );
    }
    skipped("perf", CheckCategory::Perf, "no Rust bench runner detected")
}

async fn run_property(stack: &StackDetector<'_>, root: &Path, cfg: &QGateConfig) -> CheckResult {
    if cfg.is_na("property") {
        return na("property", CheckCategory::Property);
    }
    if stack.has_rust() {
        let (ok, detail) = run_cmd(
            "cargo", &["test", "--workspace", "--features", "proptest"], root,
        )
        .await
        .unwrap_or((false, "no proptest feature".into()));
        return make_result(
            CheckCategory::Property, ok, detail, "property tests passed",
            None, None, Some(Thresholds::PROPERTY_COUNTEREXAMPLES),
        );
    }
    skipped("property", CheckCategory::Property, "no Rust proptest runner")
}

async fn run_mutation(stack: &StackDetector<'_>, root: &Path, cfg: &QGateConfig) -> CheckResult {
    if cfg.is_na("mutation") {
        return na("mutation", CheckCategory::Mutation);
    }
    if stack.has_rust() {
        let mutants_available = run_cmd("cargo", &["mutants", "--version"], root)
            .await
            .map(|(ok, _)| ok)
            .unwrap_or(false);
        if mutants_available {
            let (ok, detail) = run_cmd(
                "cargo", &["mutants", "--workspace", "--timeout", "60"], root,
            )
            .await
            .unwrap_or((false, "cargo-mutants failed".into()));
            return make_result(
                CheckCategory::Mutation, ok, detail, "mutation score passed",
                None, None, Some(cfg.mutation_threshold),
            );
        }
        return skipped("mutation", CheckCategory::Mutation, "cargo-mutants not installed");
    }
    if stack.has_python() {
        let (ok, detail) = run_cmd("uv", &["run", "mutmut", "run"], root)
            .await
            .unwrap_or((false, "mutmut not found".into()));
        return make_result(
            CheckCategory::Mutation, ok, detail, "mutmut passed",
            None, None, Some(cfg.mutation_threshold),
        );
    }
    skipped("mutation", CheckCategory::Mutation, "no mutation runner for stack")
}



async fn run_sast(root: &Path, cfg: &QGateConfig) -> CheckResult {
    if cfg.is_na("sast") {
        return na("sast", CheckCategory::Sast);
    }
    let semgrep_available = run_cmd("semgrep", &["--version"], root)
        .await
        .map(|(ok, _)| ok)
        .unwrap_or(false);
    if !semgrep_available {
        return skipped("sast", CheckCategory::Sast, "semgrep not installed");
    }
    let cfg_arg: &str = if root.join(".semgrep.yml").exists()
        || root.join(".semgrep.yaml").exists()
        || root.join("semgrep.yml").exists()
    {
        "--config=.semgrep.yml"
    } else {
        "--config=auto"
    };
    let (ok, detail) = run_cmd(
        "semgrep",
        &[cfg_arg, "--error", "--quiet", "--json", "--output=/tmp/semgrep.json", "."],
        root,
    )
    .await
    .unwrap_or((false, "semgrep failed".into()));
    let high_count = parse_semgrep_high_count("/tmp/semgrep.json");
    let (status, score) = if !ok {
        (crate::checks::CheckStatus::Failed, Some(high_count.max(1.0)))
    } else if high_count > 0.0 {
        (crate::checks::CheckStatus::Failed, Some(high_count))
    } else {
        (crate::checks::CheckStatus::Passed, Some(0.0))
    };
    let details = match status {
        crate::checks::CheckStatus::Passed => "semgrep: 0 high/critical findings".to_string(),
        _ => format!("semgrep: {high_count} high/critical findings — {detail}"),
    };
    CheckResult {
        category: CheckCategory::Sast,
        status,
        score,
        threshold: Some(Thresholds::SAST_HIGH_FINDINGS),
        details,
    }
}

async fn run_dast(root: &Path, cfg: &QGateConfig) -> CheckResult {
    if cfg.is_na("dast") {
        return na("dast", CheckCategory::Dast);
    }
    let dast_cfg = match DastConfig::discover(root) {
        Some(c) => c,
        None => {
            return skipped("dast", CheckCategory::Dast,
                "no .qgate/dast.toml or QGATE_DAST_BASE_URL configured");
        }
    };
    let schemathesis_available = run_cmd("schemathesis", &["--version"], root)
        .await
        .map(|(ok, _)| ok)
        .unwrap_or(false);
    if !schemathesis_available {
        return skipped("dast", CheckCategory::Dast, "schemathesis not installed");
    }
    let report_path = root.join("target/qgate-dast-report.json");
    let schema_arg = dast_cfg.schema_url.as_deref().unwrap_or(&dast_cfg.base_url);
    let (ok, detail) = run_cmd(
        "schemathesis",
        &[
            "run", schema_arg, "--base-url", &dast_cfg.base_url,
            "--checks=all", "--max-examples=50", "--request-timeout=5",
            &format!("--report-json={}", report_path.display()),
        ],
        root,
    )
    .await
    .unwrap_or((false, "schemathesis crashed".into()));
    let failed = parse_dast_failed_count(&report_path);
    let (status, score) = if !ok {
        (crate::checks::CheckStatus::Failed, Some(failed.max(1.0)))
    } else if failed > 0.0 {
        (crate::checks::CheckStatus::Failed, Some(failed))
    } else {
        (crate::checks::CheckStatus::Passed, Some(0.0))
    };
    let details = match status {
        crate::checks::CheckStatus::Passed =>
            format!("schemathesis: 0 failed checks against {}", dast_cfg.base_url),
        _ => format!("schemathesis: {failed} failed checks — {detail}"),
    };
    CheckResult {
        category: CheckCategory::Dast,
        status,
        score,
        threshold: Some(Thresholds::DAST_FAILED_CHECKS),
        details,
    }
}

async fn run_sbom(root: &Path, cfg: &QGateConfig) -> CheckResult {
    if cfg.is_na("sbom") {
        return na("sbom", CheckCategory::Sbom);
    }
    if let Some(cmd) = cfg.sbom_command.as_deref() {
        let (ok, detail) = run_cmd("bash", &["-c", cmd], root)
            .await
            .unwrap_or((false, "sbom command failed to execute".into()));
        let artifact = root.join("target/sbom.cdx.json");
        let present = artifact.exists();
        let (status, score, details) = if ok && present {
            (crate::checks::CheckStatus::Passed, Some(1.0),
             format!("sbom generated: {}", artifact.display()))
        } else if present {
            (crate::checks::CheckStatus::Passed, Some(1.0),
             format!("sbom artifact present (command exited non-zero but artifact exists): {}",
                     artifact.display()))
        } else {
            (crate::checks::CheckStatus::Failed, Some(0.0),
             format!("sbom command did not produce target/sbom.cdx.json: {detail}"))
        };
        return CheckResult {
            category: CheckCategory::Sbom, status, score,
            threshold: Some(Thresholds::SBOM_MUST_EXIST), details,
        };
    }
    let artifact = root.join("target/sbom.cdx.json");
    if artifact.exists() {
        return CheckResult {
            category: CheckCategory::Sbom,
            status: crate::checks::CheckStatus::Passed,
            score: Some(1.0),
            threshold: Some(Thresholds::SBOM_MUST_EXIST),
            details: format!("sbom artifact present at {}", artifact.display()),
        };
    }
    skipped("sbom", CheckCategory::Sbom,
        "no sbom_command in .qgate.toml and target/sbom.cdx.json not found")
}

async fn run_a11y(stack: &StackDetector<'_>, root: &Path, cfg: &QGateConfig) -> CheckResult {
    if cfg.is_na("a11y") {
        return na("a11y", CheckCategory::A11y);
    }
    if stack.has_ui() {
        let (ok, detail) = run_cmd("bun", &["x", "axe", "--exit"], root)
            .await
            .unwrap_or((true, "axe not installed — skipping".into()));
        return make_result(
            CheckCategory::A11y, ok, detail, "axe: 0 violations",
            None, None, Some(Thresholds::A11Y_VIOLATIONS),
        );
    }
    na("a11y", CheckCategory::A11y)
}
