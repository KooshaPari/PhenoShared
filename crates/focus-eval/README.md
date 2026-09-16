# focus-eval

Event → Rule → Action evaluation pipeline. Pulls new events from an `EventStore` via a persisted cursor, evaluates every enabled rule against each event using a shared `RuleEngine` (so cooldown state survives across ticks), dispatches fired actions into wallet/penalty/policy layers, and appends a `rule.fired` audit record per decision.

## Purpose

Closes the event→rule→action loop. Connectors persist events via `EventSink`, SQLite holds them, and the pipeline turns those rows into wallet/penalty/policy mutations. Deterministic, replay-safe (audit-trail preserves all decisions for forensics).

## Key Types

- `RuleEvaluationPipeline` — orchestrates tick logic
- `RuleEngine` — evaluates rule against event, manages cooldown state
- `EvaluationResult` — decision (fired/not_fired), explanation, sink dispatch
- Cursor constants `RULE_EVAL_CONNECTOR_ID`, `RULE_EVAL_ENTITY_TYPE`

## Entry Points

- `RuleEvaluationPipeline::tick()` — pull events from cursor, evaluate all rules, dispatch actions
- `RuleEngine::evaluate()` — match single rule against event with context
- `tick()` returns list of `EvaluationResult`s with audit records

## Functional Requirements

- FR-RULE-002 (Deterministic evaluation)
- FR-RULE-004 (Explanation recording)
- FR-FOCUS-001/002 (Rule eval + state snapshot)

## Consumers

- Scheduled runners (invoke `tick()` on interval)
- `focus-rules` (provides `Rule` definitions)
- `focus-rewards`, `focus-penalties`, `focus-policy` (consume fired actions)
