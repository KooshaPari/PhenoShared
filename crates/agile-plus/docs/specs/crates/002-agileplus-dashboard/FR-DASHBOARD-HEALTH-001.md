# FR-DASHBOARD-HEALTH-001 — Dashboard Service Health Endpoints

> Spec anchor: `specs/002-agileplus-dashboard/`
> Status: PROPOSED → accepted on `cargo test -p agileplus-dashboard` pass
> Crate: `agileplus-dashboard`

## Description

The `agileplus-dashboard` web/desktop app exposes real (non-mock) health
checks for its backing services. The `HealthChecker` port and four default
adapters (`SqliteChecker`, `MemoryStoreChecker`, `ProcessChecker`,
`BuildInfoChecker`) are wired so the dashboard `/health` and
`/services/health.json` endpoints surface accurate status and latency for
each backing service. Health results are cached for 5 seconds to avoid
load.

## Acceptance Criteria

| AC  | Criterion |
|-----|-----------|
| AC1 | `HealthChecker` trait exposes `check(&self) -> (bool, Option<u64>)` returning `(healthy, latency_ms)`. |
| AC2 | `SqliteChecker` returns `healthy == true` and a non-negative latency in ms. |
| AC3 | `MemoryStoreChecker` returns `healthy == true` and a non-negative latency in ms. |
| AC4 | `ProcessChecker` returns `healthy == true` and a non-negative latency in ms. |
| AC5 | `BuildInfoChecker` returns `healthy == true` and a non-negative latency in ms. |
| AC6 | `run_health_checks()` returns a `Vec<ServiceHealth>` with exactly 4 entries (one per checker), all `healthy`. |
| AC7 | At least one service reports a measurable latency (`latency_ms.is_some()`). |
| AC8 | `ServiceHealth` shape: `{ name, healthy, degraded, latency_ms, last_check }`. |
| AC9 | No checker silently swallows I/O errors; failure modes surface as `healthy == false`. |
| AC10 | `health_integration.rs` proves all ACs above with at least one assertion per AC. |

## Traceability

- Spec: `specs/002-agileplus-dashboard/`
- Code: `crates/agileplus-dashboard/src/health.rs`
- BDD: `specs/002-agileplus-dashboard/bdd/dashboard-health.feature`
- Tests: `crates/agileplus-dashboard/tests/health_integration.rs`
- Journey: `docs/journeys/dashboard-health-check.md`
