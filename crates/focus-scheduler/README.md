# focus-scheduler

Rigidity-aware task scheduler. Traces to FR-PLAN-002. Greedy priority-weighted bin-packing into free time between calendar events, respecting working hours and per-task constraints. A Hard calendar event is infinite cost; a Semi(cost) conflict is budgeted; a Soft event can be overridden and incurs an override count.

## Purpose

Takes a list of `Task`s and calendar availability, produces a `Schedule` that respects time blocks and rigor constraints. Deterministic given the same inputs and wall-clock time. Handles task chunking (break long tasks into sub-blocks), constraint satisfaction (Hard/Semi/Soft conflicts), and priority-weighted placement to maximize completion likelihood.

## Key Types

- `RigidityScheduler` — orchestrates bin-packing algorithm
- `Schedule` — list of scheduled tasks with start_time, duration, scheduled_for_date
- `UnplacedReason` enum — NoTimeAvailable, ConstraintViolation, InsufficientBudget
- `RigidityCostSummary` — cost breakdown per constraint type

## Entry Points

- `RigidityScheduler::new()` — initialize with calendar and working hours
- `RigidityScheduler::schedule()` — place tasks into free time slots
- Returns schedule + unplaced task reasons

## Functional Requirements

- FR-PLAN-002 (Rigidity-aware scheduling)
- Deterministic placement given inputs + timestamp
- Constraint satisfaction (Hard/Semi/Soft conflict budgeting)

## Consumers

- iOS/Android native (render weekly/daily schedule UI)
- `focus-rituals` (generates suggested task times)
- `focus-eval` (scheduler-based rule conditions)
