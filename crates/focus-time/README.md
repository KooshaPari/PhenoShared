# focus-time

Clock abstraction for deterministic tests. Provides `ClockPort` trait with `SystemClock` (wall-clock) and `TestClock` (manually-advanced) implementations. Enables tests to advance time without sleeping, ensuring deterministic scheduling and timeout logic.

## Purpose

Decouples business logic from real time so rules, scheduler, and sync logic can be tested with controlled clocks. `TestClock::advance()` jumps to a future timestamp; all dependent code sees the new time. Used in `focus-eval`, `focus-scheduler`, and `focus-sync` tests.

## Key Types

- `ClockPort` trait — `now()` returns current timestamp
- `SystemClock` — delegates to `std::time::SystemTime`
- `TestClock` — stores internal `Instant`, can be advanced via `.set_now()`

## Entry Points

- `SystemClock::new()` — use wall-clock
- `TestClock::new()` — create with initial timestamp
- `TestClock::advance()` — jump to future time

## Functional Requirements

- Deterministic time for testing
- No dependencies on actual system time in tests
- Support for scheduler and cooldown logic testing

## Consumers

- All test modules (`focus-eval`, `focus-scheduler`, `focus-rules`, `focus-sync`)
- Native app integration testing (time manipulation for daily rituals)
