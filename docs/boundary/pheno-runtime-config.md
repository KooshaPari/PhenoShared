# Boundary: pheno-runtime-config

**Status**: ABSORBED (recorded 2026-07-17, registry v1.6.30)
**Source**: `KooshaPari/pheno-runtime-config`
**Target**: `KooshaPari/pheno` monorepo `crates/pheno-runtime-config/`

## Type

| Field  | Value |
| ------ | ----- |
| Kind   | Rust library (src-layout) |
| Edition | 2021  |
| MSRV   | 1.82   |

## Surface

- **`Reloadable<T>` trait** — pluggable hot-reload interface
- **`notify::*` file watcher** — kernel event–driven reload trigger
- **`SIGHUP` fallback** — Unix-only manual reload signal
- **`atomic swap`** — lock-free reader side via `arc-swap`

## What this crate is NOT

- Not a remote config fetcher (use `pheno-config`/`Configra`)
- Not a secret store (use `Authvault`)
- Not a process supervisor (use `pheno-observability` reloader)
- Not a CLI — `phench` CLI surfaces this crate through its
  `services/loader/runtime.py` boundary

## Failure modes

| Mode               | Behavior |
| ------------------ | -------- |
| File unreadable    | Log + retain previous good state |
| Parse error        | Log + retain previous good state |
| Schema drift       | Compile-time error (typed Reloadable<T>) |
| Watcher absent     | Falls back to SIGHUP-only |
| SIGHUP on Windows  | No-op (cfg-gated) |

## Consumers

- `pheno-observability` (reloader for log sinks)
- `PhenotypeRuntime` (per-process config)
- `phenoAI` (LLM router configs at runtime)
- All agileplus-* binaries with hot-reloadable state

## Migration / sunset

If `pheno-runtime-config` becomes a no-op (every consumer migrates to
observability-driven reconfiguration), this row becomes ARCHIVED with
`absorbed_into: observability-runtime/`. ADR-095 § "sunset path" governs
this decision.
