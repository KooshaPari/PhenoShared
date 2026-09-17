# Observability (T22)

This repo adopts [`pheno-tracing`](https://github.com/KooshaPari/pheno-tracing)
(the canonical pheno-* tracing substrate, ADR-036) for distributed-trace
capture in the `iac/*` daemons (`oci-lottery`, `oci-post-acquire`,
`tailscale-keygen`).

## What ships

- A new workspace member crate `iac/observability` (crate name
  `phenotype-infra-observability`) that exposes `init_tracing(service_name)`
  — wires `tracing-subscriber` (fmt + EnvFilter) and a `pheno_tracing::TracePort`
  backed by the local `StdoutAdapter`. Returns the `TracePort` as
  `Arc<dyn TracePort>` so callers can submit spans through the substrate.
- `.env.example` with the planned `OTEL_EXPORTER_OTLP_ENDPOINT`.
- A unit test for the `TracePort` roundtrip (`tests/test_observability.rs`).
- A CI smoke workflow at `.github/workflows/observability-smoke.yml` that
  builds the workspace with the observability member and runs the test.

## What does NOT ship (yet)

The current `pheno-tracing` substrate (v0.1) ships a port-driven
`TracePort` with local adapters (`StdoutAdapter`, `InMemoryAdapter`).
Full OTLP wire-format export is **not** included here; it is tracked
as a follow-up that will land when the substrate adds an `OtlpAdapter`
(see ADR-036 follow-up section). Once the OTLP adapter lands, the
`OTEL_EXPORTER_OTLP_ENDPOINT` value from `.env.example` is the target.

## How to use

```rust
use phenotype_infra_observability::init_tracing;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let _port = init_tracing("oci-lottery");
    // ... rest of app ...
    Ok(())
}
```

Filter via `RUST_LOG=info,oci_lottery=debug`.

## CI

`.github/workflows/observability-smoke.yml` runs `cargo test -p
phenotype-infra-observability` on every push to the T22 branch and on PR.
The smoke test does NOT spin up an OTel collector (no OtlpAdapter yet);
once the substrate adds one, expand the workflow with a `docker run
otel/opentelemetry-collector` step.
