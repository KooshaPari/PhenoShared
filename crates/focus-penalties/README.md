# focus-penalties

Penalty state machine: escalation tiers, bypass budget, lockout windows, debt balance, strict mode. Traces to FR-STATE-002. Manages enforcement escalation: warning → block → lockout, with configurable cooldowns and budget-based overrides.

## Purpose

Tracks user violations and enforces escalating penalties. Encodes state as immutable mutations (append-only log). Supports gradual escalation (warmings before blocks), bypass-budget spending (user can unlock ~3x per day), and debt-based recovery (streaks reduce debt). All mutations append to audit for forensics and replay safety.

## Key Types

- `PenaltyState` — escalation_tier, bypass_budget, lockout_windows, debt_balance, strict_mode_until
- `PenaltyMutation` — append-only mutation (Escalate, DeductBypass, RecoverDebt, ResetDebt)
- `Tier` enum — None, Warning, Block, Lockout
- `PenaltyError` — variants for invalid state, expired lockout, insufficient bypass budget

## Entry Points

- `PenaltyState::new()` — initialize at tier None
- `PenaltyState::escalate()` → `PenaltyMutation` — advance tier with automatic audit append
- `PenaltyState::spend_bypass_budget()` — deduct budget and unlock
- `PenaltyState::recover()` — reduce debt via streaks

## Functional Requirements

- FR-STATE-002 (Escalation tiers and bypass budget)
- FR-STATE-003 (Append-only mutations)
- Deterministic tie-breaking (priority-based)

## Consumers

- `focus-eval::RuleEvaluationPipeline` (fires escalation actions)
- `focus-policy` (uses tier to generate enforcement)
- iOS/Android drivers (apply policy based on tier)
