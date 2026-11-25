# Tasks: Observability Baseline

## WP-01: Inventory & SDK pin
**Effort:** S
- [ ] T001 — Run `agileplus repo list --active`, write to `worklogs/active-services.txt`.
- [ ] T002 — Publish `docs/engineering/observability-sdk-pinning.md` (Rust, Go, Swift, Python).

## WP-02: Rust instrumentation
**Effort:** M
- [ ] T003 — Add `crates/observability` (shared OTel + tracing-subscriber init).
- [ ] T004 — Wire `crates/observability` into every Rust service binary.
- [ ] T005 — Migrate plain-text logs to JSON with required fields.

## WP-03: Go instrumentation
**Effort:** M
- [ ] T006 — Add `go.opentelemetry.io/otel` to every Go module.
- [ ] T007 — Wire OTel middleware into Gin / gRPC / mux servers.
- [ ] T008 — Migrate `log` / `zap` to JSON with required fields.

## WP-04: Swift instrumentation
**Effort:** M
- [ ] T009 — Add iOS OTel SDK to every iOS app target.
- [ ] T010 — Propagate `traceparent` over URLSession.
- [ ] T011 — Emit structured logs (os_log with JSON formatter) with required fields.

## WP-05: Dashboards & verification
**Effort:** M
- [ ] T012 — Provision Grafana dashboard JSON in `docs/operations/observability/dashboards/`.
- [ ] T013 — Add per-service RED panels and a fleet overview.
- [ ] T014 — `make observability-check` linter + coverage JSON writer.
- [ ] T015 — CI workflow `.github/workflows/observability-check.yml` (required check).
- [ ] T016 — Publish `docs/operations/observability.md` with dashboard URL.
