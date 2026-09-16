# focus-always-on

Habit predictor and nudge engine for the always-on agent pipeline.

## Overview

`focus-always-on` implements the habit prediction and nudge proposal system for FocalPoint. It learns user focus patterns from historical event data and proactively suggests productive windows or break times.

## Key Components

### NudgeKind

Five types of proactive nudges:

- `StartFocus` — High-productivity window detected; user should start a focus session
- `TakeBreak` — Activity fatigue or interruption spike detected
- `ReviewDeadline` — Upcoming deadline or review checkpoint
- `StreakAtRisk` — Current focus streak at risk due to predicted distraction window
- `WindDown` — Evening wind-down suggestion (approaching sleep boundary)

### NudgeProposal

Output of the predictor:

```rust
NudgeProposal {
    when: DateTime<Utc>,
    kind: NudgeKind,
    reason: String,
    confidence: f32, // 0.0–1.0
}
```

### HabitPredictor Trait

Defines the interface for activity prediction:

```rust
#[async_trait]
pub trait HabitPredictor {
    async fn predict_next_nudge(&self, now: DateTime<Utc>) -> Result<Option<NudgeProposal>>;
    async fn productive_hours(&self, day_of_week: u32) -> Result<Vec<u32>>;
    async fn distraction_hours(&self, day_of_week: u32) -> Result<Vec<u32>>;
}
```

### RollingAverageHabitPredictor

MVP implementation using 7-day rolling averages:

- Maintains 168 hour-of-week buckets (Mon 0:00 … Sun 23:00)
- Tracks rolling average of focus success rate per bucket
- Never nudges during sleep hours (22:00–06:00, hardcoded in Phase 1)
- Emits nudges only when confidence > 60%

### AlwaysOnEngine

Main coordinator; wraps the predictor:

```rust
let engine = AlwaysOnEngine::new(predictor, nudge_tx);
engine.tick(now).await?; // Emit 0–1 proposals per tick
```

In production, called by the 60-second foreground heartbeat (focus-ffi).

## Architecture

See `docs/architecture/always_on_agent_pipeline_2026_04.md` for full design.

## Testing

6 unit tests covering:

1. Empty history (new predictor)
2. Rolling average calculation
3. Productive/distraction hour filtering
4. Sleep-hour suppression (22:00–06:00)
5. Cross-hour bucketing
6. Determinism with fixed clock

Run:

```bash
cargo test -p focus-always-on
```

## Phase 1 Scope

- [x] HabitPredictor trait + RollingAverageHabitPredictor impl
- [x] NudgeProposal + NudgeKind enum
- [x] AlwaysOnEngine wrapper
- [x] 6 unit tests + determinism verification
- [ ] Integration with focus-ffi heartbeat (Phase 2)
- [ ] Mascot UI nudge rendering (Phase 2)
- [ ] CoreML upgrade (Phase 2+)
- [ ] Cheap-LLM nudge text generation (Phase 2+)

## Known Unknowns

- **Nudge frequency:** Per hour? Per day? (Phase 2, user feedback)
- **Cheap-LLM integration:** Phase 1 (template) vs Phase 2 (dynamic text)
- **Cross-device sync:** On-device only in Phase 1; optional encrypted sync in Phase 3+
- **Sleep detection:** Hardcoded 22:00–06:00; upgrade to `pmset` + device-motion data in Phase 2+

## License

MIT OR Apache-2.0
