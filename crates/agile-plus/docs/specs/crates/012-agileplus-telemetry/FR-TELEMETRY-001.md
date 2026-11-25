# FR-TELEMETRY-001 — AgilePlus Telemetry Port

> Spec anchor: `specs/012-agileplus-telemetry/`
> Status: PROPOSED → accepted on `cargo test -p agileplus-telemetry` pass
> Crate: `agileplus-telemetry`

## Description

The `agileplus-telemetry` crate exposes a `TelemetrySink` port for emitting
spans, metrics, and structured logs without coupling callers to a specific
backend. The default adapter is OTLP-over-HTTP, with a no-op adapter for
tests and an in-memory recorder for assertions. Sampling is configurable
per-signal; PII redaction runs at the port boundary.

## Acceptance Criteria

| AC  | Criterion |
|-----|-----------|
| AC1 | `TelemetrySink` trait exposes `span(name, attrs)`, `counter(name, value)`, `log(level, msg)`. |
| AC2 | No-op adapter compiles and never panics on any input. |
| AC3 | In-memory recorder exposes `recorded()` for test assertions. |
| AC4 | OTLP adapter serializes to the documented JSON shape. |
| AC5 | PII redaction runs before any span/counter/log reaches a sink. |
| AC6 | Sampling config is per-signal and hot-reloadable from `agileplus-config`. |
| AC7 | Backpressure on a sink does not block callers for more than 10ms. |
| AC8 | `telemetry_integration.rs` proves ACs above with at least one assertion per AC. |

## Traceability

- Spec: `specs/012-agileplus-telemetry/`
- Code: `crates/agileplus-telemetry/src/`
- BDD: `specs/012-agileplus-telemetry/bdd/`
- Tests: `crates/agileplus-telemetry/tests/telemetry_integration.rs`
- Journey: `docs/journeys/telemetry-emission.md`
