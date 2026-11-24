# focus-rules

Rule DSL, evaluation, priority, cooldowns, explanation. Traces to FR-RULE-001..008. Defines `Rule` primitive: trigger (event type match), conditions (state predicates), actions (wallet/penalty/policy mutations), cooldown (re-fire window), priority (conflict resolution).

## Purpose

Encodes all user policies as first-class `Rule` objects. Supports fluent builder API for construction, deterministic evaluation against events and state snapshots, priority-based tie-breaking, and explainability (every action has rationale text). Rules are storable, composable, and can be disabled per user.

## Key Types

- `Rule` — trigger, conditions[], actions[], cooldown_ms, priority, enabled, explanation_template
- `RuleBuilder` — fluent construction with validation
- `RuleEngine` — evaluates rule against event, manages cooldown, returns `EvaluationResult`
- `Condition` enum — event match, state predicates (wallet balance, penalty tier, time-of-day)
- `Action` enum — Earn, Spend, Escalate, Unblock, UpdatePolicy

## Entry Points

- `RuleBuilder::new()` → `.with_trigger()` → `.add_condition()` → `.add_action()` → `.build()`
- `RuleEngine::evaluate()` — match rule against event with state context
- `Rule::explain()` — human-readable explanation of action taken

## Functional Requirements

- FR-RULE-001..008 (DSL, evaluation, cooldown, priority, explanation)
- Deterministic evaluation given (rule, event, state_snapshot)
- Support for temporal conditions and scheduler integration

## Consumers

- `focus-eval::RuleEvaluationPipeline` (invokes evaluate)
- `focus-templates` (distributes rule packs)
- Admin CLI/web editor (rule management)
