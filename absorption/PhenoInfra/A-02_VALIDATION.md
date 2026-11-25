# A-02 VALIDATION — Absorb nanovms core

**Date:** 2026-06-23
**Status:** ✅ PASS

## Checklist

| Item | Status |
|------|--------|
| `crates/nanovms-core/` directory created | ✅ |
| `cmd/` directory with nanovms + nvms main.go | ✅ |
| `internal/` with adapters, config, domain, ports | ✅ |
| `tests/` with BDD + Playwright | ✅ |
| `pkg/` with deploy, tier, config, runtime, etc. | ✅ |
| `docs/` with all 14 ADRs preserved | ✅ |
| `go.mod` + `go.sum` copied | ✅ |
| `Makefile` + `Taskfile.yml` copied | ✅ |
| `codecov.yml` copied | ✅ |
| `bindings/go-c-export/nvms_core.go` copied | ✅ |
| `build.rs` created (Go staticlib orchestrator) | ✅ |
| `Cargo.toml` created (staticlib + rlib) | ✅ |
| `src/lib.rs` entry point created | ✅ |
| Top-level `Makefile` with nvms-c-archive target | ✅ |
| Workspace `Cargo.toml` updated with nanovms-core member | ✅ |
| Git commit with message `A-02: absorb nanovms core` | ✅ |

## Git SHA
`f22d4e0` — A-02: absorb nanovms core into phenotype-infra/crates/nanovms-core
