# cargo-deny private dependency routing

## Context

`PhenoObservability` has one external sibling Rust dependency in CI:

- `../pheno/crates/phenotype-errors`

The previous CI workflow also downloaded `<REDACTED>/phenotype-bus`, but the
active workspace now resolves event-bus types through `vendor/phenotype-event-bus`.
The `phenotype-event-bus` tarball was a stale integration-test fixture and is no
longer required for the current `cargo test --workspace --lib` and coverage
jobs.

## Required Secret

No private sibling read token is required for the default CI jobs.

## Why the dependency was not rerouted

Routing to `PhenoProc` is still not equivalent for the historical
`phenotype_event_bus_observability_e2e` integration fixture. `PhenoProc` currently has
a different `phenotype-event-bus` crate surface, while the archived
`phenotype-event-bus` fixture used the typed async pub/sub API.

## Validation

CI jobs that need Cargo dependency resolution check out:

- `PhenoObservability` at `./PhenoObservability`
- `pheno` at `./pheno`

This layout matches the active path dependencies and allows cargo-deny and the
Rust test jobs to resolve the workspace graph:

```bash
cargo deny check --manifest-path PhenoObservability/Cargo.toml
```

