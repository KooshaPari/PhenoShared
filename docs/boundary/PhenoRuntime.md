# Boundary — PhenoRuntime

> Phenotype runtime substrate. Boundary file created 2026-07-17
> during registry batch4 refresh. Distinct from `pheno-runtime-config`
> (already absorbed into `pheno` monorepo `crates/pheno-runtime-config/`).

## In Scope

- **Runtime substrate** — async executor, resource lifecycle, signal
  handling, graceful shutdown coordination.
- **Plugin host** — dynamic library loader for `pheno-cdylib-bridge`
  consumers and other FFI adapters.
- **Hot-reload** — `Reloadable<T>` pattern per ADR-095, file-watcher
  integration for config-driven restarts.
- **Process supervisor** — boot order, dependency-aware startup, crash
  restart policy.

## Out of Scope

| Not here | Lives in | Reason |
| -------- | -------- | ------ |
| Config schema | `phenotype-config` (batch4) | PhenoRuntime consumes, doesn't define |
| Memory/storage | `thegent-memory` | Storage is separate; runtime orchestrates |
| Orchestration | `thegent` / `Agentora` | Higher-level agents run on top of PhenoRuntime |
| Binary apps | `phenotype-apps` (Tracera absorbed 2026-06-25) | Apps are consumers of runtime |

## Boundary Crossings

| Crossing | Direction | Surface | Status |
| -------- | --------- | ------- | ------ |
| Apps → PhenoRuntime | consumer | library API | green |
| PhenoRuntime → thegent-memory | consumer | MemoryPort trait | green |
| PhenoRuntime → phenotype-config | consumer | `Reloadable<T>` | amber (config schema evolving) |

## Last Boundary Review

**Date:** 2026-07-17
**Reviewer:** registry batch4 audit (queue-refresh-batch4)
**Disposition-index row:** DSPI-NEW (`repo-PhenoRuntime`, fsm=queued)
**Decisions:**
- ABSORB target: `pheno` monorepo (placeholder — deep audit required
  first; current branch may carry WIP that needs reconciliation).

**Next review:** deep-audit before absorption
