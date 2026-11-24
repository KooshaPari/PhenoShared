---
fr_id: FR-DASHBOARD-HEALTH-001
spec_slug: 002-agileplus-dashboard
spec_anchor: "#fr-dashboard-health-001"
status: pending-capture
captured_at: null
---

# Journey: Dashboard Service Health Check

> **Status: stub** — `FR-DASHBOARD-HEALTH-001`. See
> `specs/002-agileplus-dashboard/FR-DASHBOARD-HEALTH-001.md` for the source
> of truth and `specs/002-agileplus-dashboard/bdd/dashboard-health.feature`
> for the executable acceptance scenarios.

## User story

As a **dashboard operator**, I open the health panel and see real (not
mock) status for every backing service — SQLite, in-memory store, process
metrics, and build info — with measured latencies, so I can trust the
dashboard's green/yellow/red indicators during incidents.

## Steps

1. Run `cargo run -p agileplus-dashboard` to start the server.
2. Open `http://localhost:<port>/health` in a browser.
   ![stub: dashboard-health-overview](./assets/stubs/dashboard-health-overview.gif)
3. Click into the services panel; confirm four rows render.
   ![stub: dashboard-health-services-panel](./assets/stubs/dashboard-health-services-panel.gif)
4. Confirm each row shows `healthy: true` and a numeric latency in ms.
   ![stub: dashboard-health-latency-detail](./assets/stubs/dashboard-health-latency-detail.gif)
5. Hit `GET /services/health.json`; confirm JSON payload matches the
   in-process `Vec<ServiceHealth>` shape.
   ![stub: dashboard-health-json-payload](./assets/stubs/dashboard-health-json-payload.gif)

## Traceability

| AC  | Criterion | Test / Evidence |
|-----|-----------|-----------------|
| AC1 | `HealthChecker::check` returns `(bool, Option<u64>)` | `health_integration.rs::healthchecker_port_contract` |
| AC2 | `SqliteChecker` healthy + latency | `health_integration.rs::sqlite_checker_healthy_and_latency` |
| AC3 | `MemoryStoreChecker` healthy + latency | `health_integration.rs::memory_store_checker_healthy_and_latency` |
| AC4 | `ProcessChecker` healthy + latency | `health_integration.rs::process_checker_healthy_and_latency` |
| AC5 | `BuildInfoChecker` healthy + latency | `health_integration.rs::build_info_checker_healthy_and_latency` |
| AC6 | `run_health_checks` returns 4 healthy entries | `health_integration.rs::run_health_checks_returns_four_healthy_services` |
| AC7 | At least one service reports measurable latency | `health_integration.rs::at_least_one_service_reports_measurable_latency` |
| AC8 | `ServiceHealth` shape stable | `health_integration.rs::service_health_shape_is_stable` |
| AC9 | No silent error swallowing | `health_integration.rs::checker_failures_surface_as_healthy_false` |
| AC10 | Integration tests cover all ACs | this file + `health_integration.rs` |

## Eval checklist

- [ ] `cargo test -p agileplus-dashboard` exits 0.
- [ ] All 10 ACs above have at least one passing test in
      `crates/agileplus-dashboard/tests/health_integration.rs`.
- [ ] BDD scenarios in
      `specs/002-agileplus-dashboard/bdd/dashboard-health.feature` are
      one-to-one with ACs.
- [ ] No existing spec under `kitty-specs/` or
      `docs/requirements/agileplus-frnfr.md` is regressed.
- [ ] No silent error swallowing: failure modes (timeout, db down, etc.)
      flip `healthy` to `false` and remain visible to the operator.
- [ ] Latency is non-negative and reported in milliseconds.
- [ ] Stub GIFs referenced above exist or are tracked for capture under
      `docs/journeys/assets/stubs/`.
