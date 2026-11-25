# Default-on platform allocators (C00 L8)

Status: **C00 L8** — `sl-daemon` default builds install a **platform
allocator**: `tikv-jemallocator` on Unix and `mimalloc` on Windows. Explicit
`--features jemalloc` soft/hard CI evidence remains in
[`jemalloc.md`](jemalloc.md).

Machine proof: `pwsh ./scripts/jemalloc-default-on-check.ps1 -SelfCheck`.

Policy manifest: [`jemalloc-default-on.json`](jemalloc-default-on.json).

Related: [`scripts/jemalloc-check.ps1`](../../scripts/jemalloc-check.ps1),
[`.github/workflows/jemalloc-hard.yml`](../../.github/workflows/jemalloc-hard.yml),
[`.github/workflows/jemalloc-default-on-hard.yml`](../../.github/workflows/jemalloc-default-on-hard.yml),
[`crates/sl-daemon/Cargo.toml`](../../crates/sl-daemon/Cargo.toml).

## Contract

| Platform | Allocator           | Feature                                             | Source                                          |
| -------- | ------------------- | --------------------------------------------------- | ----------------------------------------------- |
| Unix     | `tikv-jemallocator` | `platform-allocator` → `jemalloc` alias             | [`main.rs`](../../crates/sl-daemon/src/main.rs) |
| Windows  | `mimalloc`          | `platform-allocator` → `mimalloc-alloc` alias       | same                                            |
| Opt-out  | system allocator    | `--no-default-features --features system-allocator` | `Cargo.toml` `default`                          |

## How to run

### SelfCheck (hermetic; Windows-safe)

```powershell
pwsh ./scripts/jemalloc-default-on-check.ps1 -SelfCheck
```

### Default build (platform allocator)

```bash
cargo build --manifest-path crates/sl-daemon/Cargo.toml --locked
```

### System allocator (opt-out)

```bash
cargo build --manifest-path crates/sl-daemon/Cargo.toml --no-default-features --features system-allocator --locked
```

Hermetic wiring test: [`tests/jemalloc_default_on.rs`](../../tests/jemalloc_default_on.rs).

## CI / scheduling

| Gate                                     | Workflow                       | Mode         | Evidence                                   |
| ---------------------------------------- | ------------------------------ | ------------ | ------------------------------------------ |
| Soft/hard explicit `--features jemalloc` | `jemalloc-hard.yml`            | **blocking** | Retained Unix feature-build proof          |
| Default-on SelfCheck                     | `jemalloc-default-on-hard.yml` | **blocking** | Docs + Cargo/default-feature anchors       |
| Unix default build                       | `jemalloc-default-on-hard.yml` | **blocking** | `cargo build --locked` (jemalloc in graph) |
| Windows default build                    | `jemalloc-default-on-hard.yml` | **blocking** | `cargo build --locked` (mimalloc in graph) |

### Soft vs hard gates

| Gate                                                      | Status     | Evidence                           |
| --------------------------------------------------------- | ---------- | ---------------------------------- |
| Default-on `platform-allocator` feature                   | **done**   | `Cargo.toml` + `main.rs`           |
| Windows mimalloc parity                                   | **done**   | `mimalloc-alloc` on Windows        |
| Blocking jemalloc-default-on-hard CI workflow             | **done**   | PR SelfCheck + platform builds     |
| `tests/jemalloc_default_on.rs` cargo wrapper              | **done**   | Hermetic SelfCheck anchor smoke    |
| Continuous jemalloc profiling / production telemetry push | **unpaid** | Effort M; beyond allocator install |

## Done / unpaid

| Item                                             | Status     |
| ------------------------------------------------ | ---------- | --------------- |
| Policy SSOT + JSON manifest                      | **done**   |
| Unix default jemalloc                            | **done**   |
| Windows mimalloc parity                          | **done**   |
| Blocking jemalloc-default-on-hard CI workflow    | **done**   |
| `tests/jemalloc_default_on.rs` cargo wrapper     | **done**   |
| Continuous profiling push to production backends | **unpaid** | C00 L8 residual |

<!-- Windows mimalloc parity | **done** -->
<!-- Unix default jemalloc | **done** -->
<!-- Blocking jemalloc-default-on-hard CI workflow | **done** -->
<!-- Continuous profiling push to production backends | **unpaid** -->
