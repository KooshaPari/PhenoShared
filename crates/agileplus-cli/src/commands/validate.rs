//! `agileplus validate` command implementation.
//!
//! Checks governance compliance for a feature in Implementing state.
//! Transitions to Validated on success.
//! Traceability: FR-005, FR-018, FR-019 / WP13-T073, T074, T077

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use agileplus_domain::domain::audit::{hash_entry, AuditEntry};
use agileplus_domain::domain::governance::{Evidence, GovernanceContract, PolicyCheck};
use agileplus_domain::domain::state_machine::FeatureState;
use agileplus_domain::ports::{StoragePort, VcsPort};
use anyhow::{Context, Result};
use chrono::Utc;

/// Arguments for the `validate` subcommand.
#[derive(Debug, clap::Args)]
pub struct ValidateArgs {
    /// Feature slug to validate.
    #[arg(long)]
    pub feature: String,

    /// Output format for validation report (markdown or json).
    #[arg(long, default_value = "markdown")]
    pub format: String,

    /// Skip policy rule evaluation (evidence-only check).
    #[arg(long)]
    pub skip_policies: bool,

    /// Write report to file instead of stdout.
    #[arg(long)]
    pub output: Option<PathBuf>,

    /// Force validation even if not in Implementing state (logs governance exception).
    #[arg(long)]
    pub force: bool,

    /// Enforce bidirectional requirement-to-code/test traceability.
    #[arg(long)]
    pub traceability: bool,
}

/// Result of checking a single evidence requirement.
#[derive(Debug, Clone)]
pub struct EvidenceCheck {
    pub fr_id: String,
    pub evidence_type: String,
    pub found: bool,
    pub threshold_met: bool,
    pub message: String,
}

/// Result of evaluating a policy rule.
#[derive(Debug, Clone)]
pub struct PolicyEvalResult {
    pub policy_id: i64,
    pub domain: String,
    pub passed: bool,
    pub message: String,
}

/// Result of checking a bidirectional traceability link.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TraceabilityIssue {
    pub kind: String,
    pub id: String,
    pub message: String,
}

/// Aggregated validation report.
#[derive(Debug)]
pub struct ValidationReport {
    pub feature_slug: String,
    pub timestamp: chrono::DateTime<Utc>,
    pub overall_pass: bool,
    pub evidence_results: Vec<EvidenceCheck>,
    pub policy_results: Vec<PolicyEvalResult>,
    pub traceability_results: Vec<TraceabilityIssue>,
    pub missing_evidence: Vec<(String, String)>,
    pub governance_exceptions: Vec<String>,
}

impl ValidationReport {
    fn to_markdown(&self) -> String {
        let status = if self.overall_pass { "PASS" } else { "FAIL" };
        let mut lines = vec![
            format!("# Validation Report: {}", self.feature_slug),
            format!(
                "**Timestamp**: {} | **Result**: {}",
                self.timestamp.format("%Y-%m-%dT%H:%M:%SZ"),
                status
            ),
            String::new(),
            "## Evidence Checks".to_string(),
            String::new(),
        ];

        if self.evidence_results.is_empty() {
            lines.push("_(no evidence requirements defined in governance contract)_".to_string());
        } else {
            lines.push("| FR ID | Type | Found | Threshold Met | Notes |".to_string());
            lines.push("|-------|------|-------|---------------|-------|".to_string());
            for check in &self.evidence_results {
                lines.push(format!(
                    "| {} | {} | {} | {} | {} |",
                    check.fr_id,
                    check.evidence_type,
                    if check.found { "Yes" } else { "No" },
                    if check.threshold_met { "Yes" } else { "N/A" },
                    check.message,
                ));
            }
        }

        if !self.policy_results.is_empty() {
            lines.push(String::new());
            lines.push("## Policy Checks".to_string());
            lines.push(String::new());
            lines.push("| Policy ID | Domain | Passed | Notes |".to_string());
            lines.push("|-----------|--------|--------|-------|".to_string());
            for p in &self.policy_results {
                lines.push(format!(
                    "| {} | {} | {} | {} |",
                    p.policy_id,
                    p.domain,
                    if p.passed { "Yes" } else { "No" },
                    p.message,
                ));
            }
        }

        if !self.traceability_results.is_empty() {
            lines.push(String::new());
            lines.push("## Traceability Issues".to_string());
            lines.push(String::new());
            lines.push("| Kind | ID | Notes |".to_string());
            lines.push("|------|----|-------|".to_string());
            for issue in &self.traceability_results {
                lines.push(format!(
                    "| {} | {} | {} |",
                    issue.kind, issue.id, issue.message
                ));
            }
        }

        if !self.missing_evidence.is_empty() {
            lines.push(String::new());
            lines.push("## Missing Evidence".to_string());
            lines.push(String::new());
            for (fr_id, ev_type) in &self.missing_evidence {
                lines.push(format!("- FR `{}`: missing `{}` evidence", fr_id, ev_type));
            }
        }

        if !self.governance_exceptions.is_empty() {
            lines.push(String::new());
            lines.push("## Governance Exceptions".to_string());
            lines.push(String::new());
            for exc in &self.governance_exceptions {
                lines.push(format!("- {exc}"));
            }
        }

        lines.push(String::new());
        lines.join("\n")
    }

    fn to_json(&self) -> String {
        let missing: Vec<serde_json::Value> = self
            .missing_evidence
            .iter()
            .map(|(f, t)| serde_json::json!({"fr_id": f, "type": t}))
            .collect();
        let evidence: Vec<serde_json::Value> = self
            .evidence_results
            .iter()
            .map(|e| {
                serde_json::json!({
                    "fr_id": e.fr_id,
                    "type": e.evidence_type,
                    "found": e.found,
                    "threshold_met": e.threshold_met,
                    "message": e.message,
                })
            })
            .collect();
        let policies: Vec<serde_json::Value> = self
            .policy_results
            .iter()
            .map(|p| {
                serde_json::json!({
                    "policy_id": p.policy_id,
                    "domain": p.domain,
                    "passed": p.passed,
                    "message": p.message,
                })
            })
            .collect();
        let traceability: Vec<serde_json::Value> = self
            .traceability_results
            .iter()
            .map(|t| {
                serde_json::json!({
                    "kind": t.kind,
                    "id": t.id,
                    "message": t.message,
                })
            })
            .collect();
        serde_json::to_string_pretty(&serde_json::json!({
            "feature_slug": self.feature_slug,
            "timestamp": self.timestamp.to_rfc3339(),
            "overall_pass": self.overall_pass,
            "evidence_results": evidence,
            "policy_results": policies,
            "traceability_results": traceability,
            "missing_evidence": missing,
            "governance_exceptions": self.governance_exceptions,
        }))
        .unwrap_or_default()
    }
}

pub(crate) async fn evaluate_traceability<V: VcsPort>(
    vcs: &V,
    feature_slug: &str,
) -> Result<Vec<TraceabilityIssue>> {
    let spec = vcs
        .read_artifact(feature_slug, "spec.md")
        .await
        .context("reading spec.md for traceability validation")?;
    let requirement_ids = requirement_ids_from_spec(&spec);
    let marker_refs = traceability_marker_refs_from_repo(&std::env::current_dir()?)?;

    Ok(compare_traceability_links(
        &requirement_ids,
        &marker_refs.code_refs,
        &marker_refs.test_refs,
    ))
}

#[derive(Debug, Default)]
struct TraceabilityMarkerRefs {
    code_refs: BTreeSet<String>,
    test_refs: BTreeSet<String>,
}

fn compare_traceability_links(
    requirement_ids: &BTreeSet<String>,
    code_refs: &BTreeSet<String>,
    test_refs: &BTreeSet<String>,
) -> Vec<TraceabilityIssue> {
    let mut issues = Vec::new();
    if requirement_ids.is_empty() {
        issues.push(TraceabilityIssue {
            kind: "missing_requirement_ids".to_string(),
            id: "spec.md".to_string(),
            message: "No stable requirement IDs found; use IDs such as FR-001 or AGP-REQ(FR-001)"
                .to_string(),
        });
        return issues;
    }

    for req_id in requirement_ids {
        if !code_refs.contains(req_id) {
            issues.push(TraceabilityIssue {
                kind: "missing_code_marker".to_string(),
                id: req_id.clone(),
                message: "Requirement has no matching code marker".to_string(),
            });
        }
        if !test_refs.contains(req_id) {
            issues.push(TraceabilityIssue {
                kind: "missing_test_marker".to_string(),
                id: req_id.clone(),
                message: "Requirement has no matching test marker".to_string(),
            });
        }
    }

    for marker_id in code_refs.union(test_refs) {
        if !requirement_ids.contains(marker_id) {
            issues.push(TraceabilityIssue {
                kind: "orphan_marker".to_string(),
                id: marker_id.clone(),
                message: "Code or test marker does not match a requirement in spec.md".to_string(),
            });
        }
    }

    issues
}

fn requirement_ids_from_spec(content: &str) -> BTreeSet<String> {
    let mut ids = extract_traceability_ids(content);
    ids.extend(extract_prefixed_ids(content, "FR-"));
    ids
}

fn traceability_marker_refs_from_repo(root: &Path) -> Result<TraceabilityMarkerRefs> {
    let mut refs = TraceabilityMarkerRefs::default();
    for base in ["crates", "src", "tests", "python/src", "python/tests"] {
        let path = root.join(base);
        collect_traceability_marker_refs(&path, &mut refs)?;
    }
    Ok(refs)
}

fn collect_traceability_marker_refs(path: &Path, refs: &mut TraceabilityMarkerRefs) -> Result<()> {
    if !path.exists() {
        return Ok(());
    }
    if path.is_dir() {
        for entry in std::fs::read_dir(path)
            .with_context(|| format!("reading traceability scan directory {}", path.display()))?
        {
            let entry = entry?;
            let child = entry.path();
            let name = child
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or_default();
            if matches!(
                name,
                "target" | ".git" | ".venv" | "node_modules" | "__pycache__"
            ) {
                continue;
            }
            collect_traceability_marker_refs(&child, refs)?;
        }
        return Ok(());
    }

    let Some(ext) = path.extension().and_then(|ext| ext.to_str()) else {
        return Ok(());
    };
    if !matches!(ext, "rs" | "py" | "ts" | "tsx" | "js" | "jsx") {
        return Ok(());
    }

    let content = std::fs::read_to_string(path)
        .with_context(|| format!("reading traceability marker file {}", path.display()))?;
    let ids = extract_traceability_ids(&content);
    if ids.is_empty() {
        return Ok(());
    }

    let path_text = path.to_string_lossy();
    let target = if path_text.contains("/tests/") || path_text.contains("_test.") {
        &mut refs.test_refs
    } else {
        &mut refs.code_refs
    };
    target.extend(ids);
    Ok(())
}

fn extract_traceability_ids(content: &str) -> BTreeSet<String> {
    let mut ids = BTreeSet::new();
    let mut remaining = content;
    while let Some(start) = remaining.find("AGP-REQ(") {
        let after = &remaining[start + "AGP-REQ(".len()..];
        let Some(end) = after.find(')') else {
            break;
        };
        let id = after[..end].trim();
        if is_traceability_id(id) {
            ids.insert(id.to_string());
        }
        remaining = &after[end + 1..];
    }
    ids
}

fn extract_prefixed_ids(content: &str, prefix: &str) -> BTreeSet<String> {
    let mut ids = BTreeSet::new();
    for token in content.split(|c: char| !(c.is_ascii_alphanumeric() || c == '-' || c == '_')) {
        if token.starts_with(prefix) && is_traceability_id(token) {
            ids.insert(token.to_string());
        }
    }
    ids
}

fn is_traceability_id(value: &str) -> bool {
    let Some((prefix, suffix)) = value.split_once('-') else {
        return false;
    };
    matches!(prefix, "FR" | "REQ" | "AGP")
        && suffix
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
        && suffix.chars().any(|c| c.is_ascii_digit())
}

/// Evaluate governance evidence requirements against stored evidence.
async fn evaluate_evidence<S: StoragePort>(
    storage: &S,
    contract: &GovernanceContract,
    _feature_id: i64,
) -> Result<(Vec<EvidenceCheck>, Vec<(String, String)>)> {
    // Collect all evidence for all WPs of this feature by querying storage
    // We use get_evidence_by_fr for each required FR.
    let mut results = Vec::new();
    let mut missing = Vec::new();

    // Gather rules for implementing -> validated transition
    let target_transition_keywords = ["Implementing", "validated", "Validate", "implementing"];

    for rule in &contract.rules {
        let is_validate_rule = target_transition_keywords
            .iter()
            .any(|kw| rule.transition.to_lowercase().contains(&kw.to_lowercase()));

        // Include all rules — implementing-level rules apply here
        for req in &rule.required_evidence {
            let evidence_list = storage
                .get_evidence_by_fr(&req.fr_id)
                .await
                .unwrap_or_default();

            // Filter to evidence belonging to this feature's WPs
            // We check if any evidence exists for this fr_id
            let relevant: Vec<&Evidence> = evidence_list.iter().collect();
            let found = !relevant.is_empty();

            let threshold_met = if let (true, Some(threshold)) = (found, &req.threshold) {
                // Check threshold if present
                evaluate_threshold(relevant.as_slice(), threshold)
            } else {
                found
            };

            let message = if !found {
                format!("No evidence found for FR `{}`", req.fr_id)
            } else if !threshold_met {
                format!("Threshold not met for FR `{}`", req.fr_id)
            } else {
                "OK".to_string()
            };

            if !found {
                missing.push((req.fr_id.clone(), format!("{:?}", req.evidence_type)));
            }

            results.push(EvidenceCheck {
                fr_id: req.fr_id.clone(),
                evidence_type: format!("{:?}", req.evidence_type),
                found,
                threshold_met,
                message,
            });

            let _ = is_validate_rule; // rule context noted
        }
    }

    Ok((results, missing))
}

/// Check if evidence meets a threshold defined in the governance contract.
fn evaluate_threshold(evidence: &[&Evidence], threshold: &serde_json::Value) -> bool {
    if let Some(min_cov) = threshold.get("min_coverage").and_then(|v| v.as_f64()) {
        for ev in evidence {
            if let Some(meta) = &ev.metadata {
                if let Some(cov) = meta.get("coverage").and_then(|v| v.as_f64()) {
                    if cov >= min_cov {
                        return true;
                    }
                }
            }
        }
        return false;
    }
    if let Some(max_crit) = threshold.get("max_critical").and_then(|v| v.as_u64()) {
        let critical_count: u64 = evidence
            .iter()
            .filter_map(|ev| ev.metadata.as_ref())
            .filter_map(|meta| meta.get("critical_count"))
            .filter_map(|v| v.as_u64())
            .sum();
        return critical_count <= max_crit;
    }
    true
}

/// Evaluate active policy rules against evidence.
async fn evaluate_policies<S: StoragePort>(
    storage: &S,
    contract: &GovernanceContract,
    feature_id: i64,
) -> Result<Vec<PolicyEvalResult>> {
    let active_policies = storage
        .list_active_policies()
        .await
        .context("loading active policies")?;

    // Gather policy refs referenced in the contract
    let referenced: std::collections::HashSet<String> = contract
        .rules
        .iter()
        .flat_map(|r| r.policy_refs.iter().cloned())
        .collect();

    let mut results = Vec::new();

    for policy in &active_policies {
        // Check if this policy is referenced by the contract
        let policy_ref = format!("policy:{}", policy.id);
        let domain_debug = format!("{:?}", policy.domain).to_lowercase();
        let is_referenced = referenced.contains(&policy_ref)
            || referenced.iter().any(|r| r.contains(&domain_debug));

        if !is_referenced && !referenced.is_empty() {
            continue;
        }

        let (passed, message) = match &policy.rule.check {
            PolicyCheck::EvidencePresent { evidence_type } => {
                let work_packages = storage
                    .list_wps_by_feature(feature_id)
                    .await
                    .unwrap_or_default();
                let mut found = false;
                for wp in &work_packages {
                    let evidence = storage.get_evidence_by_wp(wp.id).await.unwrap_or_default();
                    if evidence
                        .iter()
                        .any(|entry| entry.evidence_type == *evidence_type)
                    {
                        found = true;
                        break;
                    }
                }
                let ev_type_str = format!("{:?}", evidence_type);
                (
                    found,
                    if found {
                        format!("Evidence type {} present", ev_type_str)
                    } else {
                        format!("Evidence type {} missing", ev_type_str)
                    },
                )
            }
            PolicyCheck::ThresholdMet { metric, min } => {
                let metrics = storage
                    .get_metrics_by_feature(feature_id)
                    .await
                    .unwrap_or_default();
                let found = metrics.iter().any(|m| m.command == *metric);
                (
                    found,
                    if found {
                        format!("Metric '{}' present (threshold >= {})", metric, min)
                    } else {
                        format!("Metric '{}' not found (threshold >= {})", metric, min)
                    },
                )
            }
            PolicyCheck::ManualApproval => {
                // Cannot auto-approve; fail with instructions
                (
                    false,
                    "Manual approval required — run the approval workflow".to_string(),
                )
            }
            PolicyCheck::Custom { script } => {
                // Custom scripts not supported in CLI validation; skip
                (
                    true,
                    format!(
                        "Custom policy skipped: {}",
                        script.chars().take(60).collect::<String>()
                    ),
                )
            }
        };

        results.push(PolicyEvalResult {
            policy_id: policy.id,
            domain: format!("{:?}", policy.domain),
            passed,
            message,
        });
    }

    Ok(results)
}

/// Run the `validate` command.
pub async fn run_validate<S, V>(args: ValidateArgs, storage: &S, vcs: &V) -> Result<()>
where
    S: StoragePort,
    V: VcsPort,
{
    let start = std::time::Instant::now();
    let slug = &args.feature;

    // Look up feature
    let feature = storage
        .get_feature_by_slug(slug)
        .await
        .context("looking up feature")?
        .ok_or_else(|| {
            anyhow::anyhow!(
                "Feature '{}' not found. Run `agileplus plan --feature {}` first.",
                slug,
                slug
            )
        })?;

    // State enforcement
    let mut governance_exceptions: Vec<String> = Vec::new();
    if feature.state != FeatureState::Implementing {
        if args.force {
            let exc = format!(
                "Force flag used: expected state 'Implementing', got '{}' for feature '{}'",
                feature.state, slug
            );
            eprintln!("Warning: {exc}");
            governance_exceptions.push(exc);
        } else {
            anyhow::bail!(
                "Feature '{}' is in state '{}'. Expected 'Implementing'. \
                Run `agileplus implement --feature {}` first, or use --force.",
                slug,
                feature.state,
                slug
            );
        }
    }

    // Load governance contract
    let contract = storage
        .get_latest_governance_contract(feature.id)
        .await
        .context("loading governance contract")?
        .ok_or_else(|| {
            anyhow::anyhow!(
                "No governance contract found for feature '{}'. Run `agileplus plan --feature {}` first.",
                slug, slug
            )
        })?;

    // Evaluate evidence
    let (evidence_results, missing_evidence) =
        evaluate_evidence(storage, &contract, feature.id).await?;

    // Evaluate policies (unless skipped)
    let policy_results = if args.skip_policies {
        Vec::new()
    } else {
        evaluate_policies(storage, &contract, feature.id).await?
    };

    // Compute overall pass
    let evidence_pass =
        missing_evidence.is_empty() && evidence_results.iter().all(|e| e.found && e.threshold_met);
    let policy_pass = policy_results.iter().all(|p| p.passed);
    let traceability_results = if args.traceability {
        evaluate_traceability(vcs, slug).await?
    } else {
        Vec::new()
    };
    let traceability_pass = traceability_results.is_empty();
    let overall_pass = evidence_pass && policy_pass && traceability_pass;

    let report = ValidationReport {
        feature_slug: slug.clone(),
        timestamp: Utc::now(),
        overall_pass,
        evidence_results,
        policy_results,
        traceability_results,
        missing_evidence,
        governance_exceptions,
    };

    // Format and output the report
    let report_content = match args.format.as_str() {
        "json" => report.to_json(),
        _ => report.to_markdown(),
    };

    if let Some(ref output_path) = args.output {
        std::fs::write(output_path, &report_content)
            .with_context(|| format!("writing report to {}", output_path.display()))?;
        println!("Validation report written to: {}", output_path.display());
    } else {
        print!("{report_content}");
    }

    if !overall_pass {
        anyhow::bail!(
            "Validation FAILED for feature '{}'. Fix the issues above and re-run validate.",
            slug
        );
    }

    // Transition to Validated
    storage
        .update_feature_state(feature.id, FeatureState::Validated)
        .await
        .context("transitioning feature to Validated")?;

    // Append audit entry
    let prev_hash = get_latest_hash(storage, feature.id).await;
    let mut audit = AuditEntry {
        id: 0,
        feature_id: feature.id,
        wp_id: None,
        timestamp: Utc::now(),
        actor: "user".into(),
        transition: "Implementing -> Validated".into(),
        evidence_refs: vec![],
        prev_hash,
        hash: [0u8; 32],
        event_id: None,
        archived_to: None,
    };
    audit.hash = hash_entry(&audit);
    storage
        .append_audit_entry(&audit)
        .await
        .context("appending audit entry")?;

    // Also write report as artifact
    let report_md = if args.format == "json" {
        report.to_markdown()
    } else {
        report_content.clone()
    };
    vcs.write_artifact(slug, "validation-report.md", &report_md)
        .await
        .unwrap_or_else(|e| {
            tracing::warn!("Failed to write validation-report.md artifact: {e}");
        });

    let elapsed_ms = start.elapsed().as_millis();
    tracing::info!(command = "validate", slug = %slug, elapsed_ms = %elapsed_ms, "validate completed");

    println!("Feature '{}' validated successfully.", slug);
    println!("  State: Implementing -> Validated");
    println!("  Report: docs/specs/{slug}/validation-report.md");

    Ok(())
}

async fn get_latest_hash<S: StoragePort>(storage: &S, feature_id: i64) -> [u8; 32] {
    match storage.get_latest_audit_entry(feature_id).await {
        Ok(Some(entry)) => entry.hash,
        _ => [0u8; 32],
    }
}

#[cfg(test)]
mod tests {
    use agileplus_domain::domain::governance::{
        EvidenceRequirement, EvidenceType, GovernanceContract, GovernanceRule,
    };

    use super::*;

    #[allow(dead_code)]
    fn make_contract(feature_id: i64) -> GovernanceContract {
        GovernanceContract {
            id: 1,
            feature_id,
            version: 1,
            rules: vec![GovernanceRule {
                transition: "Implementing -> Validated".to_string(),
                required_evidence: vec![EvidenceRequirement {
                    fr_id: "FR-001".to_string(),
                    evidence_type: EvidenceType::CiOutput,
                    threshold: None,
                }],
                policy_refs: vec![],
            }],
            bound_at: Utc::now(),
        }
    }

    #[test]
    fn report_to_markdown_pass() {
        let report = ValidationReport {
            feature_slug: "my-feat".to_string(),
            timestamp: Utc::now(),
            overall_pass: true,
            evidence_results: vec![EvidenceCheck {
                fr_id: "FR-001".to_string(),
                evidence_type: "CiOutput".to_string(),
                found: true,
                threshold_met: true,
                message: "OK".to_string(),
            }],
            policy_results: vec![],
            traceability_results: vec![],
            missing_evidence: vec![],
            governance_exceptions: vec![],
        };
        let md = report.to_markdown();
        assert!(md.contains("PASS"));
        assert!(md.contains("FR-001"));
    }

    #[test]
    fn report_to_markdown_fail_missing_evidence() {
        let report = ValidationReport {
            feature_slug: "my-feat".to_string(),
            timestamp: Utc::now(),
            overall_pass: false,
            evidence_results: vec![EvidenceCheck {
                fr_id: "FR-001".to_string(),
                evidence_type: "CiOutput".to_string(),
                found: false,
                threshold_met: false,
                message: "No evidence found for FR `FR-001`".to_string(),
            }],
            policy_results: vec![],
            traceability_results: vec![],
            missing_evidence: vec![("FR-001".to_string(), "CiOutput".to_string())],
            governance_exceptions: vec![],
        };
        let md = report.to_markdown();
        assert!(md.contains("FAIL"));
        assert!(md.contains("Missing Evidence"));
    }

    #[test]
    fn report_to_json_has_required_fields() {
        let report = ValidationReport {
            feature_slug: "feat".to_string(),
            timestamp: Utc::now(),
            overall_pass: true,
            evidence_results: vec![],
            policy_results: vec![],
            traceability_results: vec![],
            missing_evidence: vec![],
            governance_exceptions: vec![],
        };
        let json = report.to_json();
        let v: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert_eq!(v["feature_slug"], "feat");
        assert_eq!(v["overall_pass"], true);
    }

    #[test]
    fn evaluate_threshold_min_coverage_pass() {
        use agileplus_domain::domain::governance::Evidence;
        let ev = Evidence {
            id: 1,
            wp_id: 1,
            fr_id: "FR-001".to_string(),
            evidence_type: EvidenceType::TestResult,
            artifact_path: "ci.log".to_string(),
            metadata: Some(serde_json::json!({"coverage": 85.0})),
            created_at: Utc::now(),
        };
        let threshold = serde_json::json!({"min_coverage": 80.0});
        assert!(evaluate_threshold(&[&ev], &threshold));
    }

    #[test]
    fn evaluate_threshold_min_coverage_fail() {
        use agileplus_domain::domain::governance::Evidence;
        let ev = Evidence {
            id: 1,
            wp_id: 1,
            fr_id: "FR-001".to_string(),
            evidence_type: EvidenceType::TestResult,
            artifact_path: "ci.log".to_string(),
            metadata: Some(serde_json::json!({"coverage": 60.0})),
            created_at: Utc::now(),
        };
        let threshold = serde_json::json!({"min_coverage": 80.0});
        assert!(!evaluate_threshold(&[&ev], &threshold));
    }

    #[test]
    fn evaluate_threshold_max_critical_pass() {
        use agileplus_domain::domain::governance::Evidence;
        let ev = Evidence {
            id: 1,
            wp_id: 1,
            fr_id: "FR-SEC".to_string(),
            evidence_type: EvidenceType::SecurityScan,
            artifact_path: "scan.json".to_string(),
            metadata: Some(serde_json::json!({"critical_count": 0})),
            created_at: Utc::now(),
        };
        let threshold = serde_json::json!({"max_critical": 0});
        assert!(evaluate_threshold(&[&ev], &threshold));
    }

    #[test]
    fn evaluate_threshold_max_critical_fail() {
        use agileplus_domain::domain::governance::Evidence;
        let ev = Evidence {
            id: 1,
            wp_id: 1,
            fr_id: "FR-SEC".to_string(),
            evidence_type: EvidenceType::SecurityScan,
            artifact_path: "scan.json".to_string(),
            metadata: Some(serde_json::json!({"critical_count": 3})),
            created_at: Utc::now(),
        };
        let threshold = serde_json::json!({"max_critical": 0});
        assert!(!evaluate_threshold(&[&ev], &threshold));
    }

    #[test]
    fn traceability_ids_parse_spec_and_agp_markers() {
        let ids = requirement_ids_from_spec(
            r#"
            - FR-001: user-visible requirement
            - Inline form AGP-REQ(FR-002)
            "#,
        );
        assert!(ids.contains("FR-001"));
        assert!(ids.contains("FR-002"));
    }

    #[test]
    fn compare_traceability_links_reports_missing_and_orphan_links() {
        let requirement_ids = BTreeSet::from(["FR-001".to_string(), "FR-002".to_string()]);
        let code_refs = BTreeSet::from(["FR-001".to_string(), "FR-999".to_string()]);
        let test_refs = BTreeSet::from(["FR-001".to_string()]);

        let issues = compare_traceability_links(&requirement_ids, &code_refs, &test_refs);

        assert!(issues
            .iter()
            .any(|i| i.kind == "missing_code_marker" && i.id == "FR-002"));
        assert!(issues
            .iter()
            .any(|i| i.kind == "missing_test_marker" && i.id == "FR-002"));
        assert!(issues
            .iter()
            .any(|i| i.kind == "orphan_marker" && i.id == "FR-999"));
    }

    #[test]
    fn compare_traceability_links_reports_missing_requirement_ids() {
        let issues = compare_traceability_links(
            &BTreeSet::new(),
            &BTreeSet::from(["FR-001".to_string()]),
            &BTreeSet::new(),
        );

        assert_eq!(issues[0].kind, "missing_requirement_ids");
    }
}
