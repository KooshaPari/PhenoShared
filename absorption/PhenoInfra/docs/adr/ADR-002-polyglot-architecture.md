# ADR-002 — Polyglot Architecture (Go + Rust FFI)

- **Status:** Accepted
- **Date:** 2026-06-23
- **Deciders:** Koosha Pari (solo-dev)
- **Repo:** `phenotype-infra` monorepo

## Context

The Compute/Infra layer needs to combine two pre-existing codebases with different language runtimes:

1. **nanovms** — a Go codebase providing 3-tier isolation (WASM/gVisor/Firecracker), CLI tooling, and a mature test suite. Go was chosen for nanovms because of its excellent syscall package, rapid prototyping, and built-in concurrency primitives for sandbox management.

2. **PhenoCompose** — a Rust codebase providing the FFI driver layer, config management, and integration with the broader Rust ecosystem (including phenotype-registry, phenotype-sdk, and otel/observability crates).

Directly translating either codebase into the other language would be wasteful and error-prone. The Go codebase has ~14 ADRs worth of engineering decisions tested over months of development. The Rust codebase has tight integration with the rest of the Phenotype ecosystem.

The challenge: how to combine Go and Rust in a single workspace such that:
- Developers can work in either language without friction
- Build system resolves the cross-language boundary automatically
- CI/CD can validate both runtimes
- The FFI boundary is thin, auditable, and testable

## Decision

Adopt a **polyglot monorepo architecture** with a thin C FFI boundary between Go and Rust:

### Workspace layout

```
phenotype-infra/
  crates/
    nanovms-core/       # Go source (3-tier isolation engine)
      cmd/              # CLI entry points
      internal/         # Core isolation logic
      tests/            # Go integration tests
      bindings/
        go-c-export/    # CGo export shim → libnvms_core.a
      build.rs          # Cargo build script (Go orchestration)
      Cargo.toml        # staticlib + rlib target
    nvms-ffi/           # Rust FFI bindings (unsafe extern "C")
    pheno-compose/      # Rust driver (safe wrappers, orchestration)
    pheno-config/       # Rust config management
  tools/
    byteport/           # Svelte infra tooling (unrelated runtime)
  docs/
    adr/                # Architecture decisions
```

### Go → C archive → Rust FFI chain

1. **Go side:** `nvms_core.go` (CGo) exports C-compatible functions (`nvms_start_sandbox`, `nvms_stop_sandbox`, etc.) compiled via `go build -buildmode=c-archive` into `libnvms_core.a`.

2. **Build.rs orchestration (3 modes):**
   - **Mode A** (pre-built): `libnvms_core.a` exists in `target/` → link directly via `cargo:rustc-link-lib=static=nvms_core`.
   - **Mode B** (Go toolchain available): `go build -buildmode=c-archive` executed at build time.
   - **Mode C** (no Go): emit warnings, Rust shim module provides fallback stubs.

3. **Rust side:** `crates/nvms-ffi/src/lib.rs` declares `extern "C"` function signatures and conditionally includes a shim module (`#[cfg(not(nvms_core_lib))]`) that provides no-op implementations when the real library is absent.

### Conditional compilation

- `nvms-ffi/build.rs` sets `cargo:rustc-cfg=nvms_core_lib` when the Go static archive is available.
- `nvms-ffi/src/lib.rs` uses `#[cfg(not(nvms_core_lib))]` to gate the shim module.
- This allows `cargo check`, `cargo test`, and IDE analysis to work without the Go toolchain.

## Consequences

**Positive**

- Both codebases evolve independently in their natural language.
- The C FFI boundary enforces a clean API surface — no accidental cross-language coupling.
- `cargo check` works without Go installed (shim fallback).
- Go integration tests continue to work as before (`go test ./...` in `crates/nanovms-core/`).
- Consistent build commands for CI (`cargo build --workspace` builds everything).

**Negative**

- Added build complexity: the cross-language link step can fail silently.
- Requires CGo setup on developer machines (Windows CGo requires MinGW or equivalent).
- Debugging across the FFI boundary is harder (need `dlv` + `lldb` simultaneously).
- The shim fallback creates a risk of "green CI but broken Go link" if shims grow out of sync.

**Neutral**

- Windows cross-compilation of the Go staticlib requires `xgo` or Docker.
- Local development on macOS/Linux with Go installed gives the full experience.
- The shim module is reviewed alongside every nvms-ffi change.

## Alternatives considered

1. **Pure Rust rewrite of nanovms.** Rejected: 14 ADRs of Go engineering would need re-validation; months of effort for zero functional gain.

2. **Pure Go with cgo Rust bindings.** Rejected: Go's FFI model (cgo) is slower and more cumbersome than Rust's `extern "C"`; the Rust ecosystem (telemetry, registry, SDK) would be harder to call from Go.

3. **gRPC/microservice boundary.** Rejected: the overhead of serialization + IPC for every sandbox operation would destroy performance; in-process FFI is 10-100x faster.

4. **WASM component model.** Rejected: too experimental; both runtimes support WASM but the glue layer would be immature.

5. **Unix domain socket IPC.** Rejected: same latency concern as gRPC; adds a state machine for socket lifecycle.

## Related

- ADR-001 — Hybrid Compute Mesh (7 nodes)
- `crates/nanovms-core/` — Go source with CGo exports
- `crates/nvms-ffi/` — Rust FFI bindings
- `crates/pheno-compose/` — Safe Rust wrappers
- `docs/specs/polyglot-ffi-spec.md` — FFI contract specification
- `Makefile` — `nvms-c-archive` target
