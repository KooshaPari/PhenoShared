# pheno-tracing -- TOMBSTONED

This repository has been tombstoned as of 2026-09-11 per operator decision.
The canonical home for `pheno-tracing` is now
[PhenoObservability](https://github.com/KooshaPari/PhenoObservability)
as workspace member `crates/pheno-tracing`.

## What was here

`pheno-tracing` is the canonical port-driven distributed tracing substrate
for the pheno-* fleet (ADR-036). It provides:

- `TracePort` trait -- the fleet-wide contract for submitting spans
- `InMemoryAdapter` / `StdoutAdapter` -- test and debug backends
- `Sampler` trait + built-in samplers (Always, Never, ParentBased, RateLimit, TailBased)
- Forward-compat shim for `tracing` 0.1 -> 0.2

## What replaced it

The crate now lives at:
```
PhenoObservability/crates/pheno-tracing/
```

It is a workspace member of the PhenoObservability Cargo workspace.
All source, tests, and benchmarks have been migrated there.

### For consumers

Replace:
```toml
pheno-tracing = { git = "https://github.com/KooshaPari/pheno-tracing" }
```

With:
```toml
pheno-tracing = { git = "https://github.com/KooshaPari/PhenoObservability" }
```

Or if published to crates.io, use the version number directly.

### For PhenoVCS

PhenoVCS previously contained a copy at `crates/pheno-tracing`.
That copy should be replaced with a path or git dependency pointing to
PhenoObservability. See PhenoVCS workspace migration notes.

## Why tombstoned, not deleted

- The repo's git history has durable value for provenance.
- Per the `zz-no-archive-` convention: tombstoned repos require a
  personal walkthrough with the operator before deletion is permitted.
- PhenoVCS may still reference the old git URL during migration.

## License

Dual-licensed under MIT or Apache-2.0, at your option.
