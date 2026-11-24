# Absorption Manifest — PhenoObservability

## Source

- **Repository:** `KooshaPari/PhenoObservability` — **does not exist on GitHub** (`GET` → 404), despite the local
  clone having 2 194 commits and a `origin` URL pointing at that name
- **Local clone used:** `repos/PhenoObservability` (741 tracked files, `origin/main` @ 2026-09-11)
- **Secondary source:** `KooshaPari/PhenoTooling` `origin/main` @ `2feccc2f`, path `zz-PhenoObservability/`
- **Absorbed:** 2026-11-08

## Target

`docs/absorbed-from-PhenoObservability/` in this repo, paths relative to `zz-PhenoObservability/`. Archival: not a
workspace member, not built, not linted.

**140 source files** across `crates/` (metrickit, tracingkit, logkit, tracely-core, tracely-sentinel,
phenotype-observably-*, pheno-dragonfly, pheno-questdb, phenotype-llm, phenotype-mcp-server),
`rust/` (phenotype-health*, phenotype-telemetry, phenotype-sentry-config, phenotype-security-aggregator),
`vendor/`, `ports/`, `profiling/`, `archive/` and the Go sibling packages.

## Status

**Absorbed, because the previous plan was unsafe.** An earlier version of this audit recommended "absorb into
`KooshaPari/PhenoObservability`". That repo returns 404, so the recommendation pointed at a home that exists only as
a local clone. This directory is now the durable copy.

132 files were copied from the local clone after verifying `git hash-object` equals the blob on
`PhenoTooling origin/main`. 7 differ between the clone and PhenoTooling and were taken from PhenoTooling.
`pheno-otel/src/lib.rs` exists only in the local clone (213 lines) and was copied from there — it has no counterpart
on `PhenoTooling origin/main` at all.

## Last-Resort-Exceptions

7 files differ between the two local sources and the PhenoTooling revision was used:
`crates/logkit/src/adapters/sinks/mod.rs`, `crates/logkit/src/application/logger_builder.rs`,
`crates/phenotype-observably-macros/tests/consumer_instrumentation.rs`,
`crates/phenotype-observably-tracing/src/lib.rs`, `crates/tracely-core/src/lib.rs`,
`crates/tracely-sentinel/src/lib.rs`, `pheno-otel/src/lib.rs`.

`tracely-core` and `tracely-sentinel` are named in earlier audits as true candidates for loss — they are now covered
here, from the PhenoTooling revision.

## Restore-Command

```bash
# from PhenoTooling (archived; unarchive only temporarily, immediately before use)
git clone https://github.com/KooshaPari/zz-zz-agentcheck-PhenoTooling.git
git -C zz-zz-agentcheck-PhenoTooling checkout 2feccc2f5b12c77785dda7960f7c31d25baf4e54
cp -a zz-zz-agentcheck-PhenoTooling/zz-PhenoObservability/. docs/absorbed-from-PhenoObservability/
```
