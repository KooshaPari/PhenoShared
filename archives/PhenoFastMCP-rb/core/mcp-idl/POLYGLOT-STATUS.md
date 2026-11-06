# MCP IDL polyglot scaffolding — status manifest

**Date:** 2026-09-09 PT
**Branch:** `docs/polyglot-status-manifest-20260909`
**Base SHA:** `6c7e28b9aeb6b68f79dca67deeca9125cfb3d870`
**Status:** Preserved scaffolding. No runtime use in current local consumers.

This document honestly classifies each artifact under `core/mcp-idl/` and
`tools/codegen.sh`, separating **intent** (what the README claims) from
**reality** (what is committed and what would actually compile today).

## TL;DR

| Path | Intended role | Committed content | Build-time behavior |
|---|---|---|---|
| `core/mcp-idl/README.md` | Overview | Real README | n/a (doc) |
| `core/mcp-idl/proto/` | Vendor `.proto` files (MCP IDL) | README only | `rust/build.rs` **fails** here |
| `core/mcp-idl/rust/` | Generated Rust crate | Cargo.toml + build.rs + lib.rs stub | `cargo build` errors out until `proto/` populated |
| `core/mcp-idl/go/` | Generated Go module | go.mod + doc.go stub | `go build` would succeed (empty stub) |
| `core/mcp-idl/more/` | Future runtimes (Zig/Mojo/TS) | README only | n/a (placeholder) |
| `tools/codegen.sh` | Run `protoc` codegen | Real script | Skips if `protoc` missing |

**Bottom line:** the Rust path is **intentionally broken** until `.proto`
files are vendored. The Go path is a stub. The `more/` directory is a
forward-looking placeholder. There are **no consumers** of this scaffold
in the local repos tree (verified in
`.handoff-evidence/2026-09-08T2151Z/PhenoFastMCP-consumer-import-scan.txt`).

## Detailed classification

### `core/mcp-idl/proto/` — placeholder

- **Committed files:** `README.md` (2 lines), `.gitkeep` (added by this PR).
- **Intended content:** vendored MCP `.proto` files from
  <https://github.com/modelcontextprotocol/specification>, retrieved via
  `git subtree pull` (instructions in the README).
- **Reality:** empty. The directory exists because `core/mcp-idl/README.md`
  and `rust/build.rs` both reference `proto/` paths.
- **Precondition for use:** at least one `.proto` file must be vendored
  before `cargo build` in `core/mcp-idl/rust/` succeeds.

### `core/mcp-idl/rust/` — scaffolded crate, build-time blocked

- **Committed files:** `Cargo.toml`, `build.rs`, `src/lib.rs`.
- **`Cargo.toml` declares:**
  - `name = "mcp-idl"` (the Rust crate name; this is the
    `core/mcp-idl/rust/` directory mapped to the `mcp-idl` crate)
  - `prost` codegen at build time
  - `prost-types`, `tonic` as runtime deps
- **`build.rs` behavior:**
  - Walks `proto/` for `.proto` files via
    `protox::compile([...], includes=["proto/"])`.
  - Calls `tonic_build::configure().compile_protos(...)` to generate
    Rust types and gRPC stubs.
  - **Hard-errors** if zero `.proto` files are found (the early return
    at the top of `build.rs` is intentional — it prevents shipping
    an empty crate).
- **`src/lib.rs`:** stub `pub fn version() -> &'static str` returning
  `"0.1.0"`. No real bindings yet.
- **Reality:** `cargo build` would currently emit:
  ```
  error: no protos found in `[proto/]`
  ```
  This is correct behavior — it forces the operator to vendor protos
  before claiming the Rust crate is "ready".
- **Precondition for build success:** vendored `.proto` files in
  `proto/`.

### `core/mcp-idl/go/` — module stub

- **Committed files:** `go.mod`, `mcp/doc.go`.
- **`go.mod` declares:** `module github.com/KooshaPari/PhenoFastMCP/core/mcp-idl/go/mcp`.
- **`mcp/doc.go`:** package-level doc comment only (`// Package mcp is
  the Go-side placeholder for generated MCP IDL bindings.`).
- **Reality:** empty Go module. `go build ./...` would succeed but
  produce nothing.
- **Precondition for real use:** codegen toolchain that emits Go
  protobuf bindings into `mcp/`.

### `core/mcp-idl/more/` — forward-looking placeholder

- **Committed files:** `README.md` (2 lines).
- **README intent:** "Future runtimes — Zig, Mojo, TypeScript."
- **Reality:** no code. Pure placeholder for follow-on batches.
- **No precondition** — directory exists only to reserve the namespace.

### `tools/codegen.sh` — codegen driver

- **Committed content:** real shell script.
- **Behavior:**
  - Locates `protoc` via `command -v protoc`; if absent, prints an
    informational message and **skips** without error (exit 0).
  - Otherwise, runs `protoc --proto_path=core/mcp-idl/proto
    --go_out=... --rust_out=...` and writes generated code under
    `core/mcp-idl/{rust,go,mcp}/`.
  - Self-test: after generation, runs `cargo check` in
    `core/mcp-idl/rust/` and `go build ./...` in `core/mcp-idl/go/`.
- **Reality:** script is correct as written. It will run a no-op
  (skip) on a host without `protoc`. It will fail on a host with
  `protoc` but an empty `proto/` directory (because `cargo check`
  will surface the `prost` "no protos" error).
- **Precondition for use:** `protoc` on `$PATH` **and** populated
  `proto/` directory.

## Consumer relationship

The consumer scan (see `PhenoFastMCP-consumer-import-scan.txt` in
`.handoff-evidence/2026-09-08T2151Z/`) confirmed:

- **No local repo** imports `core/mcp-idl/` Python, Rust, or Go paths.
- **The substrate Rust workspace** imports `PhenoFastMCP-rust`, which
  is a *different* repo (`Dicklesworthstone/fastmcp_rust`), not this
  fork's scaffold.
- **PhenoMCPServers** (the only direct consumer of this fork) only
  imports the Python wheel (`fastmcp-slim[client]`), never the
  polyglot scaffold.

The scaffold is therefore **dead code by current local consumer
fleet**. It exists as operator-side forward-looking infrastructure.

## Why preserve as-is

Three options were considered:

1. **Delete the scaffold.** Rejected — would invalidate the
   2026-09-01 fork-side commit `6c7e28b9 feat(polyglot): scaffold MCP
   IDL bindings (Rust + Go + more) (#17)` and remove documented
   future-state infrastructure that may be revisited in a later batch.

2. **Wire it up (vendor protos, run codegen, commit generated code).**
   Rejected — would pull in upstream `modelcontextprotocol/specification`
   (third-party content) and expand scope to the codegen toolchain.
   The fork's value proposition is *operator-controlled polyglot
   readiness*, not *operator-controlled polyglot completion*.

3. **Preserve as-is + document honestly.** **Chosen.** Adds the
   manifest this file represents, plus a `.gitkeep` in `proto/` so
   the directory's intent is explicit in `git ls-tree`. No code
   changes, no scope creep, no false claims of readiness.

## Change list (this PR)

| File | Change | Reason |
|---|---|---|
| `core/mcp-idl/POLYGLOT-STATUS.md` | new file (this document) | Honest manifest of scaffold state |
| `core/mcp-idl/proto/.gitkeep` | new file | Marks the empty directory's intent explicit |
| `core/mcp-idl/README.md`, `tools/codegen.sh`, `core/mcp-idl/rust/`, `core/mcp-idl/go/`, `core/mcp-idl/more/` | unchanged | Existing scaffolding preserved as-is |

## Build verification

The Python wheel (`uv build --wheel`) at the repo root is unaffected
by this PR — the scaffold lives under `core/mcp-idl/` and
`tools/codegen.sh`, neither of which is in the hatch `include` /
`only-include` wheel-build configuration.

```
$ uv build --wheel                       # exit=0
$ uv pip install --no-deps dist/fastmcp_slim-3.4.3.dev67+6c7e28b9-py3-none-any.whl
                                          # exit=0
$ python3 -c "import fastmcp"            # OK
```

## Out-of-scope (separate batches, separate decisions)

- Vendoring `.proto` files from `modelcontextprotocol/specification`
  (third-party content decision).
- Building `core/mcp-idl/{go,rust,more}/` to runnable artifacts
  (substantial new artifacts; PR scope decision required).
- Wiring `substrate/driver-mcp` to consume `core/mcp-idl/rust/`
  (separate governance + Cargo.toml update).

Refs:

- Fork-side commit `6c7e28b9` (`feat(polyglot): scaffold MCP IDL
  bindings (Rust + Go + more)`).
- Operator's fork-policy workflow (PR #5).
- `phenotype-registry/audits/absorption-justifications/PhenoMCPServers-2026-07-17.md`
  (consumer relationship).
