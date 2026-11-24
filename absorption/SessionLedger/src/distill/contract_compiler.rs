//! Compiler for turning a structured [`Contract`] into a bundle slice.

use crate::distill::token_estimator::TokenEstimator;
use crate::domain::bundle::{Bundle, BundleKind};
use crate::domain::contract::Contract;
use serde_json::json;

/// Compiles structured contract data and assigns its injection token estimate.
#[derive(Debug, Clone)]
pub struct ContractCompiler<E> {
    estimator: E,
}

impl<E> ContractCompiler<E>
where
    E: TokenEstimator,
{
    /// Create a compiler backed by the given token estimator.
    pub const fn new(estimator: E) -> Self {
        Self { estimator }
    }

    /// Compile a contract into a typed, token-sized bundle slice.
    #[must_use]
    pub fn compile(&self, contract: &Contract) -> Bundle {
        let body = json!({
            "success_criteria": contract.success_criteria,
            "tests_or_verifications": contract.tests_or_verifications,
            "constraints": contract.constraints,
            "do_not_touch": contract.do_not_touch,
        });
        let token_estimate = self.estimator.estimate_json(&body);

        Bundle { kind: BundleKind::Contract, token_estimate, body }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::distill::token_estimator::CharCountTokenEstimator;

    #[test]
    fn compiler_emits_structured_contract_body() {
        let contract = Contract {
            success_criteria: vec!["resume succeeds".into()],
            tests_or_verifications: vec!["cargo test".into()],
            constraints: vec!["preserve API".into()],
            do_not_touch: vec!["src/viewer".into()],
        };

        let bundle = ContractCompiler::new(CharCountTokenEstimator).compile(&contract);

        assert_eq!(bundle.kind, BundleKind::Contract);
        assert_eq!(bundle.body["success_criteria"][0], "resume succeeds");
        assert_eq!(bundle.body["tests_or_verifications"][0], "cargo test");
        assert_eq!(bundle.body["constraints"][0], "preserve API");
        assert_eq!(bundle.body["do_not_touch"][0], "src/viewer");
        assert!(bundle.token_estimate > 0);
    }

    #[test]
    fn empty_contract_still_has_a_sized_schema() {
        let bundle = ContractCompiler::new(CharCountTokenEstimator).compile(&Contract::empty());

        assert!(bundle.body["success_criteria"].as_array().is_some_and(Vec::is_empty));
        assert!(bundle.token_estimate > 0);
    }
}
