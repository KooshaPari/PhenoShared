# ADR-007: Monitoring & Observability Strategy

## Status

**Accepted** — 2026-05-25

## Author

KooshaPari

## Context

Distributed systems across the Phenotype org — simulation engines, web dashboards, message-bus consumers — need structured traces, metrics, and log correlation to diagnose failures quickly. We need an observability stack that works both in local development and production, integrates with the Rust and TypeScript codebases without invasive instrumentation changes, and can be operated within the org without a dedicated SRE team.

## Decision

We adopt **PhenoObservability**, the org-internal observability wrapper built on **Tracely** (distributed tracing) and **Sentinel** (alerting and SLO tracking).

PhenoObservability exposes a thin, opinionated API surface that wraps OpenTelemetry primitives. Services emit spans and metrics via the `phenotype-observe` crate (Rust) or `@phenotype/observe` package (TypeScript); PhenoObservability routes these to Tracely for trace storage and Sentinel for threshold-based alerting. Standardising on the internal wrapper means instrumentation is consistent across repos and the observability stack can be upgraded centrally without touching individual services.

## Consequences

### Positive
- Single instrumentation API across all Phenotype services
- Tracely and Sentinel are self-hostable; no mandatory SaaS telemetry vendor
- OpenTelemetry foundation means export targets can be swapped (Jaeger, Tempo, Datadog)
- Sentinel SLO definitions are code-reviewed alongside service changes

### Negative / Trade-offs
- PhenoObservability is an internal library; documentation and support are internal-only
- Teams must adopt the `phenotype-observe` SDK rather than raw OTEL — adds an abstraction layer
- Tracely sampling configuration needs tuning to avoid storage cost blowup at high event volumes

## References

- ADR-001 — Hexagonal Architecture (observability adapters are secondary ports)
- ADR-006 — Deployment (Vercel Analytics is a supplementary signal for web frontend)

---

*Decision Date: 2026-05-25*
*Next Review: 2027-05-25*
