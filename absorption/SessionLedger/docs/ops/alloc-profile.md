# Allocator profiling smoke (L8 evidence, optional `dhat`)

SessionLedger already has a **counting-allocator companion** over one in-process
`process_session()` pass ([`allocation-budget.md`](allocation-budget.md), #231).
This document covers the **optional `dhat` heap-profiling smoke**: score-1 evidence
that records real allocator statistics beyond `stats_alloc` region deltas.

It is **feature-gated** (`alloc-profile`) and **never** installs a production
`#[global_allocator]`. Optional jemalloc for `sl-daemon` is a separate soft
feature ([`jemalloc.md`](jemalloc.md)) — off by default and not wired on Windows.

## Ceiling

| Knob                      | Value                                                                        | Source                                                                     |
| ------------------------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Workload                  | 8-message Forge session → `process_session`                                  | [`alloc-profile.json`](alloc-profile.json) `workload`                      |
| Peak heap bytes ceiling   | **4 MiB** (`4194304`)                                                        | `max_bytes_ceiling` (`dhat::HeapStats::max_bytes`)                         |
| Cumulative blocks ceiling | **25 000**                                                                   | `total_blocks_ceiling` (`dhat::HeapStats::total_blocks`)                   |
| Profiler                  | `dhat` heap profiler (dev-dep only)                                          | [`tests/alloc_profile_dhat.rs`](../../tests/alloc_profile_dhat.rs)         |
| Failure rule              | Exit non-zero if either ceiling is exceeded, or if config / self-check fails | [`scripts/alloc-profile-check.ps1`](../../scripts/alloc-profile-check.ps1) |

Ceilings are intentionally loose for debug builds. Do not treat these numbers as
a production SLA.

## How to run

### Self-check (no compile; hermetic)

```powershell
pwsh ./scripts/alloc-profile-check.ps1 -SelfCheck
```

### Full smoke (`dhat` integration test)

Requires the optional feature. Prefer a worktree-local Cargo target dir:

```powershell
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w29-c00-dhat"
pwsh ./scripts/alloc-profile-check.ps1
```

Or invoke cargo directly:

```powershell
cargo test --test alloc_profile_dhat --features alloc-profile --locked -- --nocapture
```

Hermetic config + script wiring (no `dhat` compile):

```powershell
cargo test --test alloc_profile --locked
```

Wall-clock once dependencies are cached: typically **well under two minutes**
(first `dhat` build may take longer).

## What the smoke does

1. Resolve ceilings from [`alloc-profile.json`](alloc-profile.json).
2. When `alloc-profile` is enabled, install a **test-binary-only** `dhat::Alloc`
   global allocator (dev-dep; main crate keeps `unsafe_code = "forbid"`).
3. Warm `process_session` once, start `dhat::Profiler::new_heap()`, run a second
   pass, then read `dhat::HeapStats`.
4. Fail if `max_bytes` or `total_blocks` exceed the documented ceilings.

## CI / scheduling

| Gate                               | Workflow                                     | Mode                                 | Evidence                                          |
| ---------------------------------- | -------------------------------------------- | ------------------------------------ | ------------------------------------------------- |
| Hermetic config + script SelfCheck | `ci.yml` (`cargo test --test alloc_profile`) | **blocking**                         | No `dhat` compile on default graph                |
| Soft scheduled dhat smoke          | `ops-load.yml` (`alloc-profile`)             | **soft** (`continue-on-error: true`) | Weekly / `workflow_dispatch` signal               |
| Blocking PR dhat smoke             | `alloc-profile-hard.yml`                     | **blocking**                         | `alloc-profile-check.ps1 -SelfCheck` + `-RunTest` |

### Soft vs hard gates

| Gate                                                      | Status     | Evidence                                                 |
| --------------------------------------------------------- | ---------- | -------------------------------------------------------- |
| Soft alloc-profile SelfCheck                              | **done**   | `ops-load.yml` `alloc-profile` job (`continue-on-error`) |
| Blocking alloc-profile-hard CI workflow                   | **done**   | `.github/workflows/alloc-profile-hard.yml`               |
| `tests/alloc_profile_hard.rs` cargo wrapper               | **done**   | Hermetic SelfCheck anchor smoke                          |
| Continuous dhat profiling / production always-on jemalloc | **unpaid** | See [`jemalloc.md`](jemalloc.md)                         |

- **PR / push:** `cargo test --test alloc_profile` in
  [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) exercises the
  hermetic config + script self-check (no `dhat` compile on the default graph).
- **Blocking PR gate:** [`.github/workflows/alloc-profile-hard.yml`](../../.github/workflows/alloc-profile-hard.yml)
  runs `alloc-profile-check.ps1 -SelfCheck` and `-RunTest` (dhat smoke) without
  `continue-on-error`.
- **Scheduled soft job:** [`.github/workflows/ops-load.yml`](../../.github/workflows/ops-load.yml)
  (`alloc-profile`, `continue-on-error: true`) runs the script self-check +
  `cargo test --test alloc_profile_dhat --features alloc-profile` on the same
  weekly / `workflow_dispatch` cadence as the allocation-budget smoke.
- Local proof without `dhat`: `pwsh ./scripts/alloc-profile-check.ps1 -SelfCheck`.

## Limitations

- Measures **one library pipeline call** under `dhat`, not daemon RSS and not
  peak during a single HTTP frame.
- Does not enable jemalloc, continuous profiling in `sl-daemon`, or production
  `#[global_allocator]` instrumentation.
- Optional feature — default `cargo test` / CI graphs stay lean.
- Debug builds and profiler overhead can inflate counts; ceilings account for that.
- Counting-allocator evidence remains in [`allocation-budget.md`](allocation-budget.md);
RSS evidence in [`memory-budget.md`](memory-budget.md).
<!-- Blocking alloc-profile-hard CI workflow | **done** -->
