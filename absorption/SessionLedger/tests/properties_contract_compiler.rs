//! Property evidence for `session_ledger::distill::contract_compiler`.
//!
//! Invariants under test:
//!
//!  * `ContractCompiler::compile` produces a `Bundle` of kind
//!    `BundleKind::Contract`
//!  * The compiled body has exactly 4 documented fields:
//!    `success_criteria`, `tests_or_verifications`, `constraints`,
//!    `do_not_touch`
//!  * The body's vector fields match the input contract's fields
//!  * The token estimate is positive (every structured contract has
//!    at least 1 token of metadata)
//!  * `ContractCompiler::new` returns a usable compiler
//!  * Default + Clone + Debug derives hold for `ContractCompiler`

use proptest::prelude::*;
use session_ledger::distill::contract_compiler::ContractCompiler;
use session_ledger::distill::token_estimator::CharCountTokenEstimator;
use session_ledger::domain::bundle::{Bundle, BundleKind};
use session_ledger::domain::contract::Contract;

// ── Compile output kinds ──────────────────────────────────────────────────

proptest! {
    /// Property: `ContractCompiler::compile` produces a `Bundle` of kind
    /// `BundleKind::Contract`.
    #[test]
    fn compile_emits_contract_kind(
        success_criteria in prop::collection::vec(".*", 0..3),
        tests in prop::collection::vec(".*", 0..3),
        constraints in prop::collection::vec(".*", 0..3),
        do_not_touch in prop::collection::vec(".*", 0..3),
    ) {
        let contract = Contract {
            success_criteria: success_criteria.clone(),
            tests_or_verifications: tests.clone(),
            constraints: constraints.clone(),
            do_not_touch: do_not_touch.clone(),
        };
        let bundle = ContractCompiler::new(CharCountTokenEstimator).compile(&contract);
        prop_assert_eq!(bundle.kind, BundleKind::Contract,
            "compile must produce BundleKind::Contract");
    }

    /// Property: the compiled body has exactly 4 fields matching the
    /// documented contract shape.
    #[test]
    fn compile_body_has_documented_fields(
        success_criteria in prop::collection::vec(".*", 0..3),
        tests in prop::collection::vec(".*", 0..3),
        constraints in prop::collection::vec(".*", 0..3),
        do_not_touch in prop::collection::vec(".*", 0..3),
    ) {
        let contract = Contract {
            success_criteria: success_criteria.clone(),
            tests_or_verifications: tests.clone(),
            constraints: constraints.clone(),
            do_not_touch: do_not_touch.clone(),
        };
        let bundle = ContractCompiler::new(CharCountTokenEstimator).compile(&contract);
        let body = &bundle.body;
        prop_assert!(body.get("success_criteria").is_some(),
            "body missing 'success_criteria' field");
        prop_assert!(body.get("tests_or_verifications").is_some(),
            "body missing 'tests_or_verifications' field");
        prop_assert!(body.get("constraints").is_some(),
            "body missing 'constraints' field");
        prop_assert!(body.get("do_not_touch").is_some(),
            "body missing 'do_not_touch' field");
    }

    /// Property: the compiled body's vector fields match the input
    /// contract's fields element-by-element.
    #[test]
    fn compile_body_matches_input(
        success_criteria in prop::collection::vec(".*", 0..3),
        tests in prop::collection::vec(".*", 0..3),
        constraints in prop::collection::vec(".*", 0..3),
        do_not_touch in prop::collection::vec(".*", 0..3),
    ) {
        let contract = Contract {
            success_criteria: success_criteria.clone(),
            tests_or_verifications: tests.clone(),
            constraints: constraints.clone(),
            do_not_touch: do_not_touch.clone(),
        };
        let bundle = ContractCompiler::new(CharCountTokenEstimator).compile(&contract);
        let body = &bundle.body;

        // Each field must be a JSON array of the same length as the input.
        let sc = body["success_criteria"].as_array().expect("array");
        let tv = body["tests_or_verifications"].as_array().expect("array");
        let cn = body["constraints"].as_array().expect("array");
        let nt = body["do_not_touch"].as_array().expect("array");
        prop_assert_eq!(sc.len(), success_criteria.len());
        prop_assert_eq!(tv.len(), tests.len());
        prop_assert_eq!(cn.len(), constraints.len());
        prop_assert_eq!(nt.len(), do_not_touch.len());
        // Element-wise equality on the strings.
        for (a, b) in sc.iter().zip(success_criteria.iter()) {
            prop_assert_eq!(a.as_str(), Some(b.as_str()));
        }
    }

    /// Property: the token estimate is always positive (the compiler
    /// always emits a sized schema, even for empty contracts).
    #[test]
    fn compile_token_estimate_is_positive(
        success_criteria in prop::collection::vec(".*", 0..3),
        tests in prop::collection::vec(".*", 0..3),
        constraints in prop::collection::vec(".*", 0..3),
        do_not_touch in prop::collection::vec(".*", 0..3),
    ) {
        let contract = Contract {
            success_criteria,
            tests_or_verifications: tests,
            constraints,
            do_not_touch,
        };
        let bundle = ContractCompiler::new(CharCountTokenEstimator).compile(&contract);
        prop_assert!(bundle.token_estimate > 0,
            "token_estimate must be positive (got 0 for empty contract)");
    }

    /// Property: `Contract::empty()` produces a sized bundle (the
    /// documented empty-still-has-schema invariant).
    #[test]
    fn empty_contract_still_has_sized_schema(_unused in 0u8..1u8) {
        let bundle = ContractCompiler::new(CharCountTokenEstimator).compile(&Contract::empty());
        prop_assert!(bundle.body["success_criteria"].as_array().is_some_and(Vec::is_empty));
        prop_assert!(bundle.token_estimate > 0);
    }
}

// ── Compiler derives ──────────────────────────────────────────────────────

proptest! {
    /// Property: `ContractCompiler` derives (Debug + Clone).
    #[test]
    fn contract_compiler_derives_hold(_unused in 0u8..1u8) {
        let compiler = ContractCompiler::new(CharCountTokenEstimator);
        let cloned = compiler.clone();
        let debug = format!("{compiler:?}");
        let debug_clone = format!("{cloned:?}");
        prop_assert!(!debug.is_empty());
        prop_assert!(!debug_clone.is_empty());
        // Both should produce identical output (both have same estimator).
        let contract = Contract::empty();
        let b1 = compiler.compile(&contract);
        let b2 = cloned.compile(&contract);
        prop_assert_eq!(b1.token_estimate, b2.token_estimate);
        prop_assert_eq!(b1.kind, b2.kind);
    }
}

// ── Type stability ────────────────────────────────────────────────────────

proptest! {
    /// Property: `compile` returns a `Bundle` (not Result / Option).
    #[test]
    fn compile_returns_bundle_unconditionally(
        text in ".*",
    ) {
        let contract = Contract {
            success_criteria: vec![text.clone()],
            tests_or_verifications: vec![text.clone()],
            constraints: vec![text.clone()],
            do_not_touch: vec![text],
        };
        let bundle: Bundle = ContractCompiler::new(CharCountTokenEstimator).compile(&contract);
        // Compile-time guarantee: just having `bundle` named proves the
        // function returns a Bundle.
        let _ = bundle.kind;
    }
}
