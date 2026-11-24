# focus-rituals

Coachy's Planning Coach personality. Traces to FR-RITUAL-001..004. Builds Sunsama-style Morning Brief ("what's your intention?") and Evening Shutdown ("what slipped, what carries over"), plus weekly and monthly cadences for sustained productivity. All LLM calls route through `focus_coaching::CoachingProvider` with kill switch and fallback copy.

## Purpose

Scaffolds daily and periodic planning rituals that guide users through intention-setting and reflection. Mascot mapping ties each ritual to a Pose/Emotion (Morning: Confident/Warm, Evening: Proud/Concerned). Rituals are opt-in and integrate with calendar, tasks, and coaching provider.

## Key Types

- `MorningBrief` — generates intention-setting prompt with task context
- `EveningShutdown` — aggregates completions, prompts reflection, cascades carrover
- `WeeklyReview` / `MonthlyRetrospective` — longer reflection cycles
- `RitualResult` — structured response (intention, reflection_summary, next_focus)

## Entry Points

- `MorningBrief::run()` — ask coaching provider for contextual opening
- `EveningShutdown::run()` — review day, prompt reflection
- All calls route through `focus_coaching::CoachingProvider` wrapper
- Silent fallback on coaching disabled or network error

## Functional Requirements

- FR-RITUAL-001..004 (Morning brief, evening shutdown, weekly/monthly)
- LLM calls gated via provider trait (no direct reqwest)
- Fallback to static copy when coaching unavailable

## Consumers

- iOS/Android native (ritual flow UI)
- `focus-mascot` (pose/emotion selection based on ritual)
- `focus-planning` + `focus-scheduler` (task context for rituals)
