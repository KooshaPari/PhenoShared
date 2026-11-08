# PhenoObservability — Architecture

**Last updated:** 2026-05-02

## Overview

13-crate Rust workspace providing end-to-end observability for the Phenotype ecosystem: distributed tracing (OpenTelemetry), structured logging (slog + JSON), metrics (Prometheus + QuestDB), alerting (sentinel), and LLM observability.

## Crate Dependency Graph

```
tracely-core                  ← core: tracing + logging primitives
  ├── phenotype-observably-tracing   ← OTel integration layer
  ├── phenotype-observably-logging   ← structured JSON logging output
  ├── phenotype-observably-macros    ← #[instrument] derive macros
  └── tracingkit                    ← high-level tracing utilities

phenotype-observably-sentinel  ← alerting engine
  └── tracely-sentinel          ← sentinel implementation

pheno-dragonfly               ← Dragonfly metrics backend
pheno-questdb                 ← QuestDB metrics storage
phenotype-llm                ← LLM request/response observability
phenotype-mcp-server         ← MCP protocol server for observability tools

helix-logging (deprecated)   → merged into tracely-core
helix-tracing (deprecated)   → merged into tracely-core
```

## Data Flow

```
Phenotype Service
  → phenotype-observably-macros (#[instrument])
  → phenotype-observably-tracing (OTel span creation)
  → tracely-core (BatchSpanProcessor)
  → OTLP/gRPC → Collector

Phenotype Service
  → phenotype-observably-logging (JSON stdout)
  → tracely-core (Drain)
  → File / stdout / vector

Metrics path:
  → pheno-dragonfly / pheno-questdb
  → Prometheus scrape or QuestDB query

Alert path:
  → phenotype-observably-sentinel
  → tracely-sentinel
  → PagerDuty / Slack / webhook
```

## OTel Integration

- W3C Trace Context propagation (traceparent / tracestate)
- OTLP/gRPC exporter to shared collector at `127.0.0.1:4317`
- BatchSpanProcessor: 512 batch, 5s timeout, 2048 queue
- Sampling: AlwaysSample (dev), ParentBased(TraceIDRatioBased(0.1)) planned for prod

## Python Bridge

`python/phenotype_observably/` provides Python bindings for the Rust crates via PyO3, enabling Python services to emit traces and logs into the same pipeline.
