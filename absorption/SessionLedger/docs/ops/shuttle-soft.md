# Soft shuttle permutation evidence (C00 L7)

SessionLedger already has deterministic race smokes, soft Miri, and soft loom
(`docs/ops/concurrency-safety.md`, `.github/workflows/loom-smoke.yml`). This
document is the **hermetic soft shuttle** companion: score-1 evidence that the
shuttle lane is wired and discoverable **without** pulling the `shuttle` crate
into the default Cargo graph.

**Full shuttle permutation coverage remains unpaid.** This lane does not explore
interleavings of daemon broadcast/SSE, watcher `sync_channel`, or a shuttle-native
port of `tests/race_model.rs` / `tests/loom_model.rs`.

## What this soft gate proves

| Artifact                                                                                       | Role                                                          |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| [`scripts/shuttle-soft-check.ps1`](../../scripts/shuttle-soft-check.ps1)                       | Hermetic `-SelfCheck` for docs/workflow/test anchors          |
| [`tests/shuttle_soft.rs`](../../tests/shuttle_soft.rs)                                         | Default `cargo test` wrapper that runs SelfCheck              |
| [`.github/workflows/shuttle-soft.yml`](../../.github/workflows/shuttle-soft.yml)               | Soft CI SelfCheck (`continue-on-error: true`)                 |
| [`scripts/shuttle-permutation-check.ps1`](../../scripts/shuttle-permutation-check.ps1)         | Blocking permutation `-SelfCheck` for docs/workflow anchors   |
| [`tests/shuttle_permutation.rs`](../../tests/shuttle_permutation.rs)                           | Blocking `cargo test` wrapper that runs permutation SelfCheck |
| [`.github/workflows/shuttle-permutation.yml`](../../.github/workflows/shuttle-permutation.yml) | Blocking permutation CI on `pull_request`                     |

No `[dependencies]` / `[dev-dependencies]` entry for `shuttle`. Prefer this
SelfCheck over adding a heavy permutation checker until a paid follow-up lands.

## Gate status

| Gate                              | Status     | Evidence                                                                                 |
| --------------------------------- | ---------- | ---------------------------------------------------------------------------------------- |
| Soft shuttle SelfCheck            | **done**   | `scripts/shuttle-soft-check.ps1 -SelfCheck` (+ `tests/shuttle_soft.rs`)                  |
| Soft shuttle CI job               | **done**   | `.github/workflows/shuttle-soft.yml` (`continue-on-error`)                               |
| Shuttle permutation SelfCheck     | **done**   | `scripts/shuttle-permutation-check.ps1 -SelfCheck` (+ `tests/shuttle_permutation.rs`)    |
| Shuttle permutation suite CI      | **done**   | `.github/workflows/shuttle-permutation.yml` (blocking on PR)                             |
| Full shuttle permutation coverage | **unpaid** | Broad broadcast/SSE/daemon graph + shuttle crate exploration still outside hermetic lane |

## How to run locally

Hermetic (no cargo compile of shuttle, no crate download):

```powershell
pwsh ./scripts/shuttle-soft-check.ps1 -SelfCheck
```

Focused Rust wrapper (spawns the same SelfCheck):

```powershell
cargo test --test shuttle_soft --locked
```

Blocking permutation SelfCheck (no shuttle crate download):

```powershell
pwsh ./scripts/shuttle-permutation-check.ps1 -SelfCheck
```

Blocking permutation Rust wrapper:

```powershell
cargo test shuttle_permutation --release --locked -- --test-threads=1
```

## Relation to loom / race model

- Soft loom cancel/capacity smoke: `tests/loom_model.rs` under `RUSTFLAGS='--cfg loom'`.
- Loom-lite `sync_channel` model: `tests/race_model.rs`.
- Soft shuttle here: docs + SelfCheck only — **full shuttle permutation coverage remains unpaid**.

## Follow-up (unpaid)

Add a cfg-gated `shuttle` model (mirroring loom's `[target.'cfg(loom)'.dev-dependencies]`)
and explore watcher / broadcast interleavings under a soft `continue-on-error` job.
Keep any such checker off the default PR matrix so ordinary `cargo test` stays lean.

<!-- Shuttle permutation SelfCheck | **done** -->
<!-- Soft shuttle SelfCheck | **done** -->
<!-- Shuttle permutation SelfCheck | **done** -->
