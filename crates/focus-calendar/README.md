# focus-calendar

Calendar port abstraction and in-memory reference implementation. Defines the trait contract that the scheduler and rule engine use to access calendar availability without coupling to any specific provider (Google Calendar, Apple EventKit, CalDAV).

## Purpose

Provides a vendor-agnostic calendar interface. Real GCal, EventKit, and CalDAV adapters are shipped separately. This crate only exports the trait and reference in-memory implementation for testing and feature development.

## Key Types

- `CalendarPort` — trait: `list_events()`, `create_event()`, `delete_event()`, `get_busy_times()`
- `CalendarEvent` — models event with start, end, summary, organizer, attendees, transparency
- `InMemoryCalendarAdapter` — reference implementation for tests
- `BusyBlock` — time range with rigidity level (Hard/Soft)

## Entry Points

- `CalendarPort::list_events()` — query events in date range
- `CalendarPort::get_busy_times()` — return merged busy blocks for scheduling
- `InMemoryCalendarAdapter::new()` — create test fixture

## Functional Requirements

- FR-CONNECTOR-001 (Calendar port definition)
- No real provider logic; trait and types only

## Consumers

- `focus-scheduler::RigidityScheduler` (queries busy times for task placement)
- `focus-eval::RuleEvaluationPipeline` (calendar events as rule triggers)
- `connector-gcal` (implements via REST polling)
