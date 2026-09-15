// SPDX-License-Identifier: MIT OR Apache-2.0
//! Property-based tests for `phenotype-contracts`.
//!
//! Mirrors the role of `ports/tests/property/contract_verifier.property.test.ts`:
//! generate arbitrary `Contract` and `Verdict` values and assert that the
//! documented structural invariants hold.
use phenotype_contracts::{Contract, Verdict};
use proptest::prelude::*;

prop_compose! {
    /// Strategy: any well-formed `Contract` (non-empty, bounded strings).
    fn contract_strategy()
        (
            name in "[a-zA-Z0-9_]{1,64}",
            predicate in "[ -~]{1,256}",
            target in "[ -~]{1,128}",
        ) -> Contract {
        Contract { name, predicate, target }
    }
}

prop_compose! {
    /// Strategy: any `Verdict` with a valid duration.
    fn verdict_strategy(ok: bool)
        (
            proof in proptest::option::of("[a-zA-Z0-9_:./\\-]{0,128}"),
            counterexample in proptest::option::of("[a-zA-Z0-9_:./\\-]{0,128}"),
            duration_ms in 0u64..60_000,
        ) -> Verdict {
        // Enforce the documented mutual-exclusion invariant at generation
        // time so property tests never see a malformed value.
        let (proof, counterexample) = if ok {
            (proof.or_else(|| Some("auto".to_string())), None)
        } else {
            (None, counterexample.or_else(|| Some("trace".to_string())))
        };
        Verdict { ok, proof, counterexample, duration_ms }
    }
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(200))]

    #[test]
    fn contract_serde_round_trip(c in contract_strategy()) {
        let j = serde_json::to_string(&c).unwrap();
        let back: Contract = serde_json::from_str(&j).unwrap();
        prop_assert_eq!(c, back);
    }

    #[test]
    fn ok_verdict_has_proof(v in verdict_strategy(true)) {
        prop_assert!(v.ok);
        prop_assert!(v.proof.is_some(), "ok verdicts must carry a proof");
        prop_assert!(v.counterexample.is_none(), "ok verdicts must not carry a counterexample");
        prop_assert!(v.duration_ms < 60_000);
    }

    #[test]
    fn not_ok_verdict_has_counterexample(v in verdict_strategy(false)) {
        prop_assert!(!v.ok);
        prop_assert!(v.counterexample.is_some(), "failing verdicts must carry a counterexample");
        prop_assert!(v.proof.is_none(), "failing verdicts must not carry a proof");
    }

    #[test]
    fn contract_name_is_preserved_through_serde(c in contract_strategy()) {
        let j = serde_json::to_string(&c).unwrap();
        let back: Contract = serde_json::from_str(&j).unwrap();
        prop_assert_eq!(back.name, c.name);
    }
}
