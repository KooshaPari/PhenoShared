# Plan: Observability Baseline

## Objective
Every active <REDACTED> service emits structured logs, OpenTelemetry metrics, and traces; a unified dashboard exists; coverage is 100% and machine-verified.

## Scope
- OpenTelemetry SDK adoption across all active services (Rust, Go, Swift, Python)
- Structured log migration to JSON with required fields
- Grafana dashboard provisioning in `docs/operations/observability/dashboards/`
- A `make observability-check` linter that emits a coverage JSON
- CI wiring as a required check

## Implementation Steps
1. Inventory active services: `agileplus repo list --active > worklogs/active-services.txt`.
2. Publish `docs/engineering/observability-sdk-pinning.md` with pinned OTel SDK versions per language.
3. For each Rust service, add `opentelemetry` + `opentelemetry-otlp` + `tracing-subscriber` (JSON formatter) in a shared `crates/observability` crate.
4. For each Go service, add `go.opentelemetry.io/otel` and `otelgin`/`otelmux` middleware.
5. For each Swift app, add the iOS OTel SDK and propagate `traceparent` over URLSession.
6. Migrate plain-text logs to JSON with required fields (`level`, `msg`, `service`, `trace_id`, `span_id`).
7. Stand up Grafana (or reuse existing) and provision dashboards from `docs/operations/observability/dashboards/`.
8. Add `make observability-check` that probes each service's `/health`, `/metrics`, and a sample trace export, then writes `worklogs/observability-coverage-<date>.json`.
9. Add CI workflow `.github/workflows/observability-check.yml` on every PR.
10. Publish `docs/operations/observability.md` linking dashboards and coverage reports.

## Verification
- `make observability-check` exits 0 on the live tree
- Coverage JSON lists every active service with `logs: true, metrics: true, traces: true`
- A sample request from one service appears in the dashboard with all three signals correlated
- Removing instrumentation from one service makes the check exit non-zero
