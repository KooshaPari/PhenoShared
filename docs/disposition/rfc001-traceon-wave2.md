# RFC 001 — Traceon repoint status (Wave 2)

**Date:** 2026-06-17  
**RFC:** [phenotype-registry RFC 001](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rfc/001-traceon-observe-role.md)  
**Canonical crate:** `crates/tracingkit` (this repo)

## Source parity

HexaKit `Traceon/` and PhenoObservability `crates/tracingkit` share the same hexagonal layout:

| Layer | Paths |
|-------|-------|
| domain | `span`, `trace`, `tracer`, `context`, `errors` |
| application | `tracer_provider` |
| adapters | `exporters` |
| infrastructure | `error` |

All Rust source files from HexaKit Traceon are present in this workspace. HexaKit retains `Traceon/MIGRATED.md` redirect stub until workspace member removal.

## Consumer repoint

| Consumer | Action |
|----------|--------|
| PhenoObservability | **Done** — `tracingkit` is workspace member |
| phenotype-otel | Remains thin OTLP init; optional `tracingkit` dep |
| Pyron | Remove `Traceon/` workspace member when fleet lockstep PR lands |

## Dependency edge

```toml
# Example for external consumers (git pin until crates.io publish)
tracingkit = { git = "https://github.com/KooshaPari/PhenoObservability", branch = "main" }
```

## Non-goals (RFC 001)

- No Traceon domain logic in phenotype-otel.
- No new tracing code in HexaKit after genesis-only charter.
