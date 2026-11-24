# Allocation budget smoke (L8 evidence)

SessionLedger's Memory & Allocation lane already has a **generous RSS / working-set
smoke** on the daemon ingest path ([`memory-budget.md`](memory-budget.md), #196).
This document covers the **cheap counting-allocator companion**: a score-1 heap
allocation budget over one in-process `process_session()` pass.

It catches gross allocation regressions without enabling jemalloc, continuous
daemon `dhat`, or a production `#[global_allocator]`. Optional `dhat` heap
evidence lives in [`alloc-profile.md`](alloc-profile.md).

## Ceiling

| Knob                    | Value                                                                        | Source                                                                             |
| ----------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Workload                | 8-message Forge session → `process_session`                                  | [`allocation-budget.json`](allocation-budget.json) `workload`                      |
| Bytes allocated ceiling | **1 MiB** (`1048576`)                                                        | `bytes_allocated_ceiling`                                                          |
| Allocations ceiling     | **5 000**                                                                    | `allocations_ceiling`                                                              |
| Metric                  | `stats_alloc` `Region` delta (bytes + allocation count)                      | [`tests/allocation_budget.rs`](../../tests/allocation_budget.rs)                   |
| Failure rule            | Exit non-zero if either ceiling is exceeded, or if config / self-check fails | [`scripts/allocation-budget-check.ps1`](../../scripts/allocation-budget-check.ps1) |

Ceilings are intentionally loose for debug builds. Tighten after real allocator
profiling lands — do not treat these numbers as a production SLA.

Override at runtime (script only; the Rust test always reads the JSON SSOT):

```powershell
pwsh ./scripts/allocation-budget-check.ps1 -SelfCheck -BytesCeiling 4194304 -AllocationsCeiling 25000
```

## How to run

### Self-check (no compile; hermetic)

```powershell
pwsh ./scripts/allocation-budget-check.ps1 -SelfCheck
```

### Full smoke (counting-allocator integration test)

Prefer a worktree-local Cargo target dir so parallel agents do not collide:

```powershell
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w27-c00-alloc"
pwsh ./scripts/allocation-budget-check.ps1
```

Or invoke cargo directly:

```powershell
cargo test --test allocation_budget --locked -- --nocapture
```

Wall-clock once dependencies are cached: typically **well under one minute**.

## What the smoke does

1. Resolve ceilings from [`allocation-budget.json`](allocation-budget.json).
2. Install a **test-binary-only** `stats_alloc` global allocator (dev-dep; production
   crates stay on the System allocator and keep `unsafe_code = "forbid"`).
3. Warm `process_session` once, then measure a second pass inside a `Region`.
4. Fail if `bytes_allocated` or `allocations` exceed the documented ceilings.

## CI / scheduling

- **PR / push:** `cargo test` in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
  already exercises root-crate integration tests, including `allocation_budget`.
- **Scheduled soft job:** [`.github/workflows/ops-load.yml`](../../.github/workflows/ops-load.yml)
  (`allocation-budget`, `continue-on-error: true`) runs the script self-check +
  `cargo test --test allocation_budget` on the same weekly / `workflow_dispatch`
  cadence as the RSS budget smoke.
- Local / PR proof without measuring heap: `pwsh ./scripts/allocation-budget-check.ps1 -SelfCheck`
  (also covered by `cargo test --test allocation_budget`).

## Limitations

- Measures **instrumented heap deltas** for one library pipeline call, not daemon
  RSS and not peak during a single HTTP frame.
- Does not enable jemalloc, `dhat`, or continuous profiling in `sl-daemon`.
- Does not prove zero-copy (`Bytes` / `Cow`) on hot I/O paths.
- Debug builds and test harness noise can inflate counts; ceilings account for that.
- Companion RSS evidence remains in [`memory-budget.md`](memory-budget.md).
