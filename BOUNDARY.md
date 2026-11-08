# Boundary Lock: Observability (`observe` role)

**Status:** ACTIVE — canonical observability workspace for Phenotype polyrepo.

## Owns

- Rust tracing hexagonal core (`crates/tracingkit`, `crates/tracely-*`)
- Rust metrics (`crates/metrickit`, `rust/phenotype-metrics`)
- Rust logging / telemetry / health (`rust/phenotype-*`, `crates/logkit`, `crates/phenotype-observably-*`)
- Storage adapters for observability backends (`pheno-dragonfly`, `pheno-questdb`)
- Language-edge references (Go `tracing/`, TS `ports/`, profiling harness)
- **Wave A (from HexaKit):**
  - `crates/tracingkit` — Traceon absorption (**landed**, RFC 001)
  - `crates/metrickit` — Metron absorption (**landed**)
  - `rust/phenotype-health` (+ axum, cli) — health primitives (**landed**)
  - `rust/phenotype-logging` — structured logging (**landed**)
  - `rust/phenotype-telemetry` — telemetry facade (**landed**)
  - `rust/phenotype-sentry-config` — Sentry init (**pending**)

## Does NOT own

- Python observability facade → `phenotype-python-sdk/packages/observability-kit`
- Thin OTLP fleet init (today) → `phenotype-otel` (merge target)
- MCP observability servers → `PhenoMCPServers`
- LLM-specific observability → Agentora / python-sdk LLM edge
- Test mocks / compliance scanner → `TestingKit` (misplaced copies to decompose)
- Security aggregation → `Authvault`
- Cross-cutting errors/event-bus → `phenoShared` (not vendored long-term)
- Token accounting / LLM FinOps → `Tokn` (complementary — not observability)

## Relationship to consolidation plan

This repo is the **canonical SSOT** per the [observability consolidation plan](../phenotype-org-audits/consolidation/observability-consolidation-plan.md)
(merged #71). `tracely-core` and `tracely-sentinel` are the authoritative copies;
the standalone `<REDACTED>/Tracely` repo will be archived.

## Consumer guidance

- **Rust:** depend on workspace crates (git pin on `main` until crates.io publish).
- **Python:** install from [`phenotype-python-sdk`](https://github.com/KooshaPari/phenotype-python-sdk) `packages/observability-kit` — not this repo.
- **Do not** add new HexaKit path/git deps for Wave A rows — use PhenoObservability.

See [docs/disposition/wave-a-absorption.md](./docs/disposition/wave-a-absorption.md) for Wave A lane status.

**Block-C disposition:** [docs/boundary/DISPOSITION.md](./docs/boundary/DISPOSITION.md) — canonical observe boundary (Rust here; Python → SDK).
