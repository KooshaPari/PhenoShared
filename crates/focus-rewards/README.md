# focus-rewards

Reward wallet aggregate and mutations. Traces to FR-STATE-001. Manages earned_credits, spent_credits, streaks, unlock_balances, multiplier_state. All mutations are append-only (`WalletMutation` log) so state can be replayed from audit and forensically verified.

## Purpose

Tracks user rewards earned through productivity streaks and rule compliance. Wallet state is derived from immutable mutations: earning credits for consecutive focus days, spending on unlocks or privileges, multiplier boosts during peak productivity. All transactions append to audit chain.

## Key Types

- `RewardWallet` — earned, spent, current_balance, streak_count, multiplier_active
- `WalletMutation` — Earn, Spend, ResetStreak, ActivateMultiplier, RecordUnlock
- `Streak` — day_count, started_at, last_activity_at
- `WalletError` — variants for insufficient balance, invalid spend reason

## Entry Points

- `RewardWallet::new()` — initialize with zero balance
- `RewardWallet::earn()` → `WalletMutation` — add credits with streak tracking
- `RewardWallet::spend()` → `WalletMutation` — deduct for unlock/privilege
- Mutations append to audit automatically

## Functional Requirements

- FR-STATE-001 (Wallet state + mutations)
- FR-STATE-003 (Append-only mutations)
- Streak tracking and multiplier logic

## Consumers

- `focus-eval::RuleEvaluationPipeline` (fires earn/spend actions)
- `focus-entitlements` (enforces subscription tier limits)
- iOS/Android native (render wallet UI, unlock flows)
