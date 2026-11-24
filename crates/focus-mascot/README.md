# focus-mascot

Coachy — the FocalPoint mascot state machine. Fiery flame-shaped coach with red cape and gold-star buckle. The Rust side owns logical state (pose × emotion × bubble copy); the Swift layer binds this to Spline scenes to render transitions. Character image is fixed; palette tokens live in `docs/reference/design_tokens.md`.

## Purpose

Provides a conversational coach that responds to rule events with contextual emotion and copy. LLM-driven bubble text is opt-in via `with_coaching()`; on failure or when disabled, falls back to static copy for offline mode. Mascot state transitions drive UI animations on native platforms.

## Key Types

- `MascotMachine` — state machine: `on_event()` → `(Pose, Emotion, bubble_copy)`
- `Pose` enum — Confident, Encouraging, Curious, Stern, Celebratory, SleepyDisappointed
- `Emotion` enum — Warm, Proud, Concerned, etc. (6 emotions per Coachy art)
- `MascotEvent` — event triggering state transition (RuleFired, WalletEarned, PenaltyEscalated, DailyCheckIn)

## Entry Points

- `MascotMachine::new()` — initialize with default/test state
- `MascotMachine::on_event()` — deterministic transition
- `MascotMachine::with_coaching()` — wire LLM provider for bubble text

## Functional Requirements

- Deterministic state transitions
- Optional LLM-driven copy with kill switch and fallback
- Offline mode support (no LLM available)

## Consumers

- iOS app (native Spline scene binding)
- Android app (Spline/Jetpack animation binding)
- `focus-rituals` (morning brief, evening shutdown prompts)
