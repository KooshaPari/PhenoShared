// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Verification pipeline

use crate::error::Result;
use crate::gates::{run_gates, GateConfig};
use crate::result::VerificationResult;
use crate::rules::{run_custom_rule, run_performance_rule, run_security_rule};
use crate::runners::run_cargo_test;
use harness_spec::models::{Specification, VerificationRule};
use tracing::{debug, instrument};

/// Verification pipeline
pub struct VerificationPipeline {
    _runners: PipelineRunners,
}

impl Default for VerificationPipeline {
    fn default() -> Self {
        Self::new()
    }
}

impl VerificationPipeline {
    pub fn new() -> Self {
        Self { _runners: PipelineRunners::default() }
    }

    #[instrument(skip(self, spec), fields(spec_id = %spec.spec.name, rules = spec.spec.verification.len()))]
    pub async fn verify(&self, spec: &Specification) -> Result<Vec<VerificationResult>> {
        let mut results = Vec::new();
        for rule in &spec.spec.verification {
            let result = self.run_verification(rule, &spec.spec.name).await?;
            results.push(result);
        }
        debug!(count = results.len(), "verification finished");
        Ok(results)
    }

    #[instrument(skip(self, rule), fields(spec_id = %spec_id))]
    async fn run_verification(
        &self,
        rule: &VerificationRule,
        spec_id: &str,
    ) -> Result<VerificationResult> {
        match rule {
            VerificationRule::Test { name: _, timeout_seconds } => {
                let timeout = *timeout_seconds as u64;
                run_cargo_test(spec_id, if timeout > 0 { timeout } else { 300 }).await
            }
            VerificationRule::Security { scanner, critical_only } => {
                run_security_rule(scanner, *critical_only, spec_id).await
            }
            VerificationRule::Performance { metric, threshold } => {
                run_performance_rule(metric, threshold, spec_id).await
            }
            VerificationRule::Custom { command, expected_exit_code } => {
                run_custom_rule(command, *expected_exit_code, spec_id).await
            }
        }
    }

    /// Run verification gates
    pub fn run_gates(
        &self,
        results: &[VerificationResult],
        gates: &[GateConfig],
    ) -> Vec<crate::result::GateResult> {
        run_gates(results, gates)
    }
}

/// Pipeline runners (extensible)
#[derive(Default)]
pub struct PipelineRunners {}
