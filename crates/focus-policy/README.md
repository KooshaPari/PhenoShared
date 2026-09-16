# focus-policy

Enforcement policy generation from rule decisions. Traces to FR-ENF-001. Converts rule-fired events (e.g., "exceeded daily limit") into `EnforcementPolicy` with concrete block/whitelist/unblock instructions that native drivers apply via FamilyControls (iOS) and UsageStats (Android).

## Purpose

Translates abstract rule decisions into platform-specific enforcement instructions. Handles priority resolution (if multiple rules fire contradicting actions, higher priority wins), merges block profiles, and emits deterministic policies that iOS and Android can apply atomically.

## Key Types

- `EnforcementPolicy` — version, effective_at, block_profiles, unlock_schedule, whitelist_ids
- `BlockProfile` — (app_id, rigidity, expires_at) tuple
- `Rigidity` enum — Hard (non-dismissible) vs Soft (dismissible with bypass budget)
- Policy composition via priority-based merge

## Entry Points

- `EnforcementPolicy::from_rules()` — build policy from fired rules
- `EnforcementPolicy::merge()` — combine policies with priority resolution
- `EnforcementPolicy::apply()` → native driver API calls

## Functional Requirements

- FR-ENF-001 (Policy generation from rules)
- FR-RIGIDITY-001 (Block rigidity tracking)
- Deterministic merge when multiple rules fire

## Consumers

- `focus-eval::RuleEvaluationPipeline` (generates on rule fire)
- Native iOS/Android drivers (apply FamilyControls/UsageStats)
