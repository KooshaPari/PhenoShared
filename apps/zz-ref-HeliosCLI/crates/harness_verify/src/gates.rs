// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Gate evaluation logic.

use crate::result::{GateDetail, GateResult, VerificationResult, VerificationStatus};
use tracing::instrument;

/// Gate configuration
#[derive(Debug, Clone)]
pub struct GateConfig {
    pub name: String,
    pub criteria: String,
    pub threshold: Option<f64>,
}

/// Evaluate verification gates against results.
#[instrument(skip(results, gates), fields(gates = gates.len()))]
pub fn run_gates(results: &[VerificationResult], gates: &[GateConfig]) -> Vec<GateResult> {
    let mut gate_results = Vec::new();

    for gate in gates {
        let passed = evaluate_gate(gate, results);
        let details: Vec<GateDetail> = results
            .iter()
            .map(|r| {
                let check_passed = matches!(r.status, VerificationStatus::Passed);
                GateDetail {
                    check: format!("{:?}", r.verification_type),
                    passed: check_passed,
                    message: r.output.clone(),
                }
            })
            .collect();

        gate_results.push(GateResult {
            name: gate.name.clone(),
            passed,
            message: if passed {
                "All gates passed".to_string()
            } else {
                "Gate check failed".to_string()
            },
            details,
        });
    }

    gate_results
}

fn evaluate_gate(gate: &GateConfig, results: &[VerificationResult]) -> bool {
    match gate.criteria.as_str() {
        "all_passed" => results.iter().all(|r| matches!(r.status, VerificationStatus::Passed)),
        "any_passed" => results.iter().any(|r| matches!(r.status, VerificationStatus::Passed)),
        "no_failures" => !results.iter().any(|r| matches!(r.status, VerificationStatus::Failed)),
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::result::{VerificationResult, VerificationType};
    use chrono::Utc;
    use uuid::Uuid;

    fn sample_result(status: VerificationStatus) -> VerificationResult {
        VerificationResult {
            id: Uuid::new_v4(),
            spec_id: "demo-spec".to_string(),
            verification_type: VerificationType::Test,
            status,
            started_at: Utc::now(),
            completed_at: Some(Utc::now()),
            duration_ms: 1,
            output: "ok".to_string(),
            errors: vec![],
            metrics: Default::default(),
        }
    }

    #[test]
    fn run_gates_all_passed_requires_every_result_passed() {
        let results = vec![
            sample_result(VerificationStatus::Passed),
            sample_result(VerificationStatus::Passed),
        ];
        let gates = vec![GateConfig {
            name: "all".to_string(),
            criteria: "all_passed".to_string(),
            threshold: None,
        }];
        let gate_results = run_gates(&results, &gates);
        assert_eq!(gate_results.len(), 1);
        assert!(gate_results[0].passed);
    }

    #[test]
    fn run_gates_no_failures_allows_skipped() {
        let results = vec![
            sample_result(VerificationStatus::Passed),
            sample_result(VerificationStatus::Skipped),
        ];
        let gates = vec![GateConfig {
            name: "no_failures".to_string(),
            criteria: "no_failures".to_string(),
            threshold: None,
        }];
        let gate_results = run_gates(&results, &gates);
        assert!(gate_results[0].passed);
    }

    #[test]
    fn run_gates_unknown_criteria_fails() {
        let results = vec![sample_result(VerificationStatus::Passed)];
        let gates = vec![GateConfig {
            name: "unknown".to_string(),
            criteria: "unsupported".to_string(),
            threshold: None,
        }];
        let gate_results = run_gates(&results, &gates);
        assert!(!gate_results[0].passed);
    }
}
