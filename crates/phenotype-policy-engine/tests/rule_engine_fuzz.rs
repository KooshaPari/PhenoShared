use phenotype_policy_engine::{
    EvaluationContext, Policy, PolicyEngine, PolicyEngineError, Rule, RuleType,
};
use proptest::prelude::*;
use regex::Regex;

fn literal_pattern(value: &str) -> String {
    format!("^{}$", regex::escape(value))
}

fn rule_type_strategy() -> impl Strategy<Value = RuleType> {
    prop_oneof![
        Just(RuleType::Allow),
        Just(RuleType::Deny),
        Just(RuleType::Require),
    ]
}

fn invalid_pattern_strategy() -> impl Strategy<Value = &'static str> {
    prop_oneof![
        Just("["),
        Just("("),
        Just("*"),
        Just("(?P<"),
        Just("(?z)"),
        Just("\\"),
    ]
}

proptest! {
    // Traces to: FR-POL-004
    #[test]
    fn rule_evaluation_matches_regex_semantics(
        rule_type in rule_type_strategy(),
        fact in "[a-z][a-z0-9_]{0,24}",
        pattern_value in "\\PC{0,32}",
        fact_value in "\\PC{0,32}",
        fact_present in any::<bool>(),
    ) {
        let pattern = literal_pattern(&pattern_value);
        let rule = Rule::new(rule_type, fact.clone(), pattern.clone());
        let mut context = EvaluationContext::new();
        if fact_present {
            context.set_string(&fact, &fact_value);
        }

        let actual = rule.evaluate(&context).expect("escaped patterns compile");
        let regex = Regex::new(&pattern).expect("escaped pattern is valid");
        let expected = match (rule_type, fact_present) {
            (RuleType::Allow, false) | (RuleType::Deny, false) => true,
            (RuleType::Require, false) => false,
            (RuleType::Allow, true) | (RuleType::Require, true) => regex.is_match(&fact_value),
            (RuleType::Deny, true) => !regex.is_match(&fact_value),
        };

        prop_assert_eq!(actual, expected);
    }

    // Traces to: FR-POL-004
    #[test]
    fn invalid_regexes_return_errors_without_panics(
        fact in "[a-z][a-z0-9_]{0,24}",
        pattern in invalid_pattern_strategy(),
    ) {
        let rule = Rule::new(RuleType::Require, fact.clone(), pattern);
        let mut context = EvaluationContext::new();
        context.set_string(fact, "anything");

        let error = rule.evaluate(&context).expect_err("invalid regex must be reported");
        let is_regex_error = matches!(error, PolicyEngineError::RegexCompilationError { .. });
        prop_assert!(is_regex_error);
    }

    // Traces to: FR-POL-004
    #[test]
    fn disabled_policy_contributes_no_violations_for_any_required_fact(
        policy_name in "[a-z][a-z0-9_]{0,24}",
        fact in "[a-z][a-z0-9_]{0,24}",
        pattern_value in "\\PC{0,32}",
    ) {
        let policy = Policy::new(policy_name)
            .set_enabled(false)
            .add_rule(Rule::new(RuleType::Require, fact, literal_pattern(&pattern_value)));
        let engine = PolicyEngine::with_policies(vec![policy]);

        let result = engine.evaluate_all(&EvaluationContext::new()).unwrap();

        prop_assert!(result.passed);
        prop_assert!(result.violations.is_empty());
    }

    // Traces to: FR-POL-004
    #[test]
    fn duplicate_policy_names_replace_previous_policy(
        name in "[a-z][a-z0-9_]{0,24}",
        fact in "[a-z][a-z0-9_]{0,24}",
        value in "\\PC{0,32}",
    ) {
        let pattern = literal_pattern(&value);
        let failing = Policy::new(name.clone())
            .add_rule(Rule::new(RuleType::Require, fact.clone(), "^missing$"));
        let passing = Policy::new(name.clone())
            .add_rule(Rule::new(RuleType::Require, fact.clone(), pattern));
        let engine = PolicyEngine::with_policies(vec![failing, passing]);
        let mut context = EvaluationContext::new();
        context.set_string(fact, value);

        let result = engine.evaluate_policy(&name, &context).unwrap();

        prop_assert!(result.passed);
        prop_assert!(result.violations.is_empty());
    }

    // Traces to: FR-POL-004
    #[test]
    fn subset_evaluation_fails_fast_on_missing_policy_name(
        existing_name in "[a-z][a-z0-9_]{0,24}",
        missing_name in "[b-z][a-z0-9_]{0,24}",
        fact in "[a-z][a-z0-9_]{0,24}",
    ) {
        prop_assume!(existing_name != missing_name);
        let engine = PolicyEngine::with_policies(vec![
            Policy::new(existing_name.clone())
                .add_rule(Rule::new(RuleType::Allow, fact, ".*")),
        ]);
        let context = EvaluationContext::new();

        let error = engine
            .evaluate_subset(&[existing_name.as_str(), missing_name.as_str()], &context)
            .expect_err("missing subset policy should be reported");

        let is_missing_policy =
            matches!(error, PolicyEngineError::PolicyNotFound { name } if name == missing_name);
        prop_assert!(is_missing_policy);
    }
}
