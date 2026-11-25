# focus-planning

Task model for the Motion-layer scheduler. Traces to FR-PLAN-001. Provides pure data types the scheduler consumes: `Task`, `DurationSpec`, `Priority`, `Deadline`, `ChunkingPolicy`, `Constraint`, `TaskStatus`, `TimeBlock`. All types are `Clone + Serialize + Deserialize` so they cross the FFI/storage boundary.

## Purpose

Defines the task abstraction: what users author, what the scheduler accepts, and what stores persist. Separate from `focus-scheduler` (which places tasks) and `focus-rituals` (which generates task suggestions).

## Key Types

- `Task` — id, user_id, title, description, priority, deadline, status, duration_spec, constraints, tags
- `DurationSpec` enum — Fixed duration or Estimate (p50/p90)
- `Priority` enum — Critical, High, Normal, Low, Later
- `Constraint` enum — Hard/Soft/None calendar conflicts
- `TaskStatus` enum — Open, InProgress, Blocked, Completed, Archived
- `TimeBlock` — start, end, rigidity (Hard/Soft/Soft(cost))

## Entry Points

- `Task::builder()` — fluent construction
- `Task::validate()` — check required fields, invariants
- Serialization via `serde` for storage/FFI

## Functional Requirements

- FR-PLAN-001 (Task model)
- Pure types without I/O or persistence
- Deterministic validation and serialization

## Consumers

- `focus-scheduler` (consumes tasks, produces schedule)
- `focus-storage` (persists tasks to SQLite)
- FFI (exposed to Swift/Kotlin)
- `focus-rituals` (generates tasks)
