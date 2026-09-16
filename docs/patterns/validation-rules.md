# Composable validation rules

This pattern captures the Guardis workstream in a repository that already owns
Phenotype governance and handbook content.

## What it covers

- String rules: not-empty, length bounds, regex matching, email, URL
- Numeric rules: min, max, positive, integer, range
- Collection rules: non-empty, min/max length, all/any predicates, uniqueness
- Composition: `and`, `or`, `not`
- Custom rules with reusable error reporting
- Reference implementation: [docs/reference/validation-rules.py](../reference/validation-rules.py)

## Why it lives here

The standalone validation library was absorbed into the broader handbook and
guardrail material instead of staying as a separate repository.

## Reference shape

- `guard(value).check(rule, field)` for field-oriented validation
- `rule(name, fn)` for custom checks
- `ValidationResult` and `RuleError` for structured outcomes
