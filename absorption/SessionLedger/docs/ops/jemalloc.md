# Optional jemalloc allocator (L8 evidence, soft + hard)

SessionLedger ships counting-allocator and optional `dhat` smokes for library
pipelines ([`allocation-budget.md`](allocation-budget.md),
[`alloc-profile.md`](alloc-profile.md)). This document covers the **explicit
`jemalloc` feature** path for `sl-daemon` and the soft/hard CI gates that
exercise `--features jemalloc` on Unix.

**Default production allocator policy** (Unix jemalloc + Windows mimalloc) lives
in [`jemalloc-default-on.md`](jemalloc-default-on.md).

Default explicit-feature builds remain **Windows-safe** for the `--features
jemalloc` path — the feature does not resolve on non-Unix targets.

## Contract

| Knob         | Value                                                               | Source                                                                                  |
| ------------ | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Feature      | `jemalloc` (off by default)                                         | [`crates/sl-daemon/Cargo.toml`](../../crates/sl-daemon/Cargo.toml)                      |
| Crate        | `tikv-jemallocator` (optional, `cfg(unix)`)                         | same                                                                                    |
| Install site | `#[global_allocator]` behind `cfg(all(feature = "jemalloc", unix))` | [`crates/sl-daemon/src/main.rs`](../../crates/sl-daemon/src/main.rs)                    |
| SelfCheck    | docs + Cargo feature + cfg anchors (no jemalloc compile)            | [`scripts/jemalloc-check.ps1`](../../scripts/jemalloc-check.ps1)                        |
| Soft CI      | Ubuntu build with `--features jemalloc`, `continue-on-error`        | [`.github/workflows/ops-load.yml`](../../.github/workflows/ops-load.yml) job `jemalloc` |
| Hard CI      | Ubuntu SelfCheck + `--features jemalloc` build, blocking PR gate    | [`.github/workflows/jemalloc-hard.yml`](../../.github/workflows/jemalloc-hard.yml)      |

## Soft vs hard gates

| Gate                                                          | Soft (scheduled)                                       | Hard (PR blocking)                                     |
| ------------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------ |
| SelfCheck (`jemalloc-check.ps1 -SelfCheck`)                   | `ops-load` job `jemalloc` (`continue-on-error: true`)  | `jemalloc-hard.yml` SelfCheck job                      |
| `cargo build --features jemalloc`                             | `ops-load` job (`continue-on-error: true`)             | `jemalloc-hard.yml` build job                          |
| Default / Windows builds unchanged (system allocator)         | **done**                                               | **done**                                               |
| Default-on Unix jemalloc / Windows mimalloc parity            | see [`jemalloc-default-on.md`](jemalloc-default-on.md) | see [`jemalloc-default-on.md`](jemalloc-default-on.md) |
| Continuous jemalloc profiling / production always-on jemalloc | **unpaid**                                             | **unpaid**                                             |
| Windows mimalloc parity                                       | **done**                                               | **done**                                               |

## How to run

### Self-check (hermetic; Windows-safe)

```powershell
pwsh ./scripts/jemalloc-check.ps1 -SelfCheck
```

### Enable jemalloc (Unix)

```bash
cargo build --manifest-path crates/sl-daemon/Cargo.toml --features jemalloc --locked
```

Or:

```bash
cargo run --manifest-path crates/sl-daemon/Cargo.toml --features jemalloc --locked -- serve --watch ./sessions --out ./okf-out
```

Hermetic wiring tests (no jemalloc compile on default graph); see
[`tests/jemalloc_soft.rs`](../../tests/jemalloc_soft.rs) and
[`tests/jemalloc_hard.rs`](../../tests/jemalloc_hard.rs):

```powershell
cargo test --test jemalloc_soft --locked
cargo test --test jemalloc_hard --locked
```

Or filter both wrappers:

```powershell
cargo test jemalloc --locked
```

## Gate status

| Gate                                                          | Status                                                        |
| ------------------------------------------------------------- | ------------------------------------------------------------- | -------------------------------------------------- |
| Soft jemalloc SelfCheck                                       | **done**                                                      |
| Default / Windows builds unchanged (system allocator)         | **done**                                                      |
| Soft Ubuntu `--features jemalloc` CI (`continue-on-error`)    | **done**                                                      |
| Blocking jemalloc-hard CI workflow                            | **done**                                                      |
| Default-on platform allocator policy                          | **done** — [`jemalloc-default-on.md`](jemalloc-default-on.md) |
| Continuous jemalloc profiling / production always-on jemalloc | **unpaid**                                                    |
| Windows mimalloc parity                                       | **done**                                                      | [`jemalloc-default-on.md`](jemalloc-default-on.md) |

## CI / scheduling

| Job                                               | Workflow                                                         | Blocking?                            | Notes                                                |
| ------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------ | ---------------------------------------------------- |
| `jemalloc`                                        | [`ops-load.yml`](../../.github/workflows/ops-load.yml)           | **soft** (`continue-on-error: true`) | Scheduled SelfCheck + `--features jemalloc` build    |
| `jemalloc-hard-selfcheck` / `jemalloc-hard-build` | [`jemalloc-hard.yml`](../../.github/workflows/jemalloc-hard.yml) | **blocking**                         | PR SelfCheck + `--features jemalloc` build on Ubuntu |

- **PR / push:** `cargo test --test jemalloc_soft` and `cargo test --test jemalloc_hard`
  exercise hermetic SelfCheck anchors (no jemalloc compile in the default test graph).
- **Scheduled soft job:** `jemalloc` in
  [`.github/workflows/ops-load.yml`](../../.github/workflows/ops-load.yml)
  (`continue-on-error: true`) runs SelfCheck + `cargo build --features jemalloc`
  on Ubuntu.
- **Blocking hard job:** [`jemalloc-hard.yml`](../../.github/workflows/jemalloc-hard.yml)
  runs the same SelfCheck + feature build on every PR without `continue-on-error`.

## Limitations

- Unix only for explicit `--features jemalloc` — Windows keeps mimalloc via
  [`jemalloc-default-on.md`](jemalloc-default-on.md) default policy.
- Soft + hard evidence for explicit feature builds — default-on policy is
  [`jemalloc-default-on.md`](jemalloc-default-on.md).
- Does not replace RSS / allocation-budget / dhat smokes; those remain separate
  L8 companions.
- Continuous profiling push backends and always-on production telemetry remain
  unpaid. Default-on allocator install is [`jemalloc-default-on.md`](jemalloc-default-on.md).
  <!-- Soft jemalloc SelfCheck | **done** -->
  <!-- Blocking jemalloc-hard CI workflow | **done** -->
  <!-- Windows mimalloc parity | **done** -->
