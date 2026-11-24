# OTLP metrics export (L43 / L42 evidence)

SessionLedger ships **Prometheus HTTP RED** metrics at `GET /metrics` with no
collector or Cargo feature required. This document describes the **OTLP metrics
export path**: operator contract, optional `otel-metrics` feature wiring, and
hermetic SelfCheck evidence. It does **not** replace or break the default
Prometheus scrape path.

## What exists today

| Layer                            | Status     | Evidence                                                                                                                  |
| -------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------- |
| Prometheus HTTP RED (`/metrics`) | **landed** | `crates/sl-daemon/src/metrics.rs`; per-route labels + histogram buckets                                                   |
| App JSON aggregates              | **landed** | `GET /api/metrics` (product summary; parallel to RED)                                                                     |
| Feature-gated OTLP **traces**    | **landed** | `otel` feature + `SL_OTLP_ENDPOINT` ([`observability.md`](observability.md#opentelemetry-feature-gated-sketch--issue-65)) |
| OTLP **metrics** push            | **landed** | `otel-metrics` + `SL_OTLP_METRICS_ENDPOINT`; `otlp_metrics_export: otlp-grpc`                                             |
| Labeled RED → OTLP bridge        | **unpaid** | Future: counters/histograms mirrored as OTLP instruments                                                                  |
| Process USE gauges               | **unpaid** | Soft goal alongside OTLP metrics                                                                                          |

See also the RED mapping table in
[`observability.md`](observability.md#red-metrics-mapping).

## Operator contract (non-breaking)

1. **Default builds** — only `GET /metrics` (Prometheus text) and `GET /api/metrics`
   (JSON). No OTLP metrics client, no collector required.
2. **Optional feature** — `cargo build -p sl-daemon --features otel-metrics`
   compiles the OTLP metrics module. Without an endpoint env var it does **not**
   open sockets or alter scrape output.
3. **Endpoint env** — with the feature enabled, set `SL_OTLP_METRICS_ENDPOINT`
   (or `OTEL_EXPORTER_OTLP_ENDPOINT` as fallback) to the collector's OTLP/gRPC
   endpoint (for example, `http://localhost:4317`). SessionLedger env takes
   precedence when both are set.
4. **Legacy acknowledgment** — `SL_OTLP_METRICS=1` logs intent when no endpoint
   is configured. Prometheus `/metrics` stays unchanged.

```text
┌─────────────┐  always on          ┌──────────────────┐
│ sl-daemon   │────────────────────►│ Prometheus scrape│
│ GET /metrics│  HTTP RED text      │ (default path)   │
└─────────────┘                     └──────────────────┘
       │
       │  otel-metrics + SL_OTLP_METRICS_ENDPOINT
       ▼
┌──────────────────┐   OTLP/gRPC ───► collector
│ MetricExporter   │   periodic push
│ + up gauge       │
└──────────────────┘
```

## Export configuration

[`otlp-metrics.json`](otlp-metrics.json) pins the export knobs:

| Field                 | Default                    | Meaning                                  |
| --------------------- | -------------------------- | ---------------------------------------- |
| `prometheus_http`     | `/metrics`                 | Default RED scrape path (must remain)    |
| `otlp_metrics_export` | `otlp-grpc`                | Push transport when endpoint is set      |
| `cargo_feature`       | `otel-metrics`             | Compile-time OTLP metrics flag           |
| `endpoint_env`        | `SL_OTLP_METRICS_ENDPOINT` | Primary collector endpoint               |
| `ack_env`             | `SL_OTLP_METRICS`          | Legacy stub acknowledgment (no endpoint) |

## How to run

### Self-check (hermetic; CI default)

```powershell
pwsh ./scripts/otlp-metrics-check.ps1 -SelfCheck
```

Validates doc/JSON anchors, the `otel-metrics` Cargo feature, export-path
symbols in `otel_metrics.rs`, and that the Prometheus `/metrics` renderer remains
present.

### Feature-gated OTLP metrics export

```bash
cargo build -p sl-daemon --manifest-path crates/sl-daemon/Cargo.toml --features otel-metrics
SL_OTLP_METRICS_ENDPOINT=http://localhost:4317 \
  cargo run -p sl-daemon --manifest-path crates/sl-daemon/Cargo.toml \
  --features otel-metrics -- serve --watch ./sessions --out ./okf-out
```

## CI / scheduling

| Job                   | Workflow                                               | Blocking?    | Notes                                                                |
| --------------------- | ------------------------------------------------------ | ------------ | -------------------------------------------------------------------- |
| `otlp-metrics-export` | [`ops-load.yml`](../../.github/workflows/ops-load.yml) | **blocking** | SelfCheck + `cargo test -p sl-daemon otlp_metrics` + feature compile |

## Unpaid gaps (explicit)

1. **RED bridge** — process-local counters are not mirrored as OTLP instruments.
2. **USE gauges** — CPU/memory/FD gauges remain soft goals.
3. **Exemplars** — not claimed by this export path.

Prometheus `/metrics` remains the supported scrape path for labeled RED series.
