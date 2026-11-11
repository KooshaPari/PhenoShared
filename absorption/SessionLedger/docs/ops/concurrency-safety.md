# Concurrency safety (L7 evidence)

SessionLedger's Concurrency Safety lane starts with **deterministic race smokes**
plus a **loom-lite bounded-channel / cancel model**. This is score-1 evidence:
it proves merge/OKF outputs stay deterministic under threads and that the
daemon's watcher contract (bounded queue + cooperative cancel) conserves
messages without CI flakes.

A **soft nightly Miri smoke** exercises the same `race_model` subset under the
interpreter (UB / provenance). A **blocking Miri permutation** job gates PRs on
that same `race_model` subset via `cargo miri`. A **soft loom smoke** explores
a tiny cancel + capacity conservation model under `RUSTFLAGS='--cfg loom'`. A
**soft shuttle SelfCheck** documents the shuttle lane hermetically (no
`shuttle` crate) — see [`shuttle-soft.md`](shuttle-soft.md). A **blocking TSan
permutation** job gates PRs on the same pure-`std` `race_model` subset under
`-Zsanitizer=thread` (ubuntu x86_64, `rust-src` / `-Zbuild-std`). Full loom /
shuttle permutation checkers, `loom_model` under Miri, and full tokio broadcast
/ daemon SSE graph ports under TSan remain unpaid.
Workspace
`unsafe_code = forbid` still holds; these soft gates are early evidence toward
those checkers, not a claim of unsafe coverage.

## What runs in CI

| Artifact                                                                                       | Role                                                                                                                                                                                                                                                                             |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`tests/race_smoke.rs`](../../tests/race_smoke.rs)                                             | Threaded merge + OKF determinism across shuffled inputs                                                                                                                                                                                                                          |
| [`tests/race_model.rs`](../../tests/race_model.rs)                                             | Bounded `sync_channel` + cancel flag model of watcher `scan_once`                                                                                                                                                                                                                |
| [`tests/loom_model.rs`](../../tests/loom_model.rs)                                             | Loom permutation models: cancel/capacity, bounded `try_send`, broadcast epoch (single + multi-bump), tokio-shaped mpsc watcher→consumer, mpsc drain→broadcast, triple SSE fan-out, full watcher→mpsc→broadcast→SSE pipeline, daemon-graph cancel conservation (`cfg(loom)` only) |
| [`tests/loom_soft.rs`](../../tests/loom_soft.rs)                                               | Hermetic SelfCheck for soft loom docs/workflow anchors                                                                                                                                                                                                                           |
| [`tests/loom_permutation.rs`](../../tests/loom_permutation.rs)                                 | Hermetic SelfCheck for loom permutation docs/workflow anchors                                                                                                                                                                                                                    |
| [`tests/shuttle_soft.rs`](../../tests/shuttle_soft.rs)                                         | Hermetic SelfCheck for soft shuttle docs/workflow anchors                                                                                                                                                                                                                        |
| [`tests/shuttle_permutation.rs`](../../tests/shuttle_permutation.rs)                           | Hermetic SelfCheck for shuttle permutation docs/workflow anchors                                                                                                                                                                                                                 |
| [`tests/tsan_permutation.rs`](../../tests/tsan_permutation.rs)                                 | Hermetic SelfCheck for TSan permutation docs/workflow anchors                                                                                                                                                                                                                    |
| [`.github/workflows/race-smoke.yml`](../../.github/workflows/race-smoke.yml)                   | Both race tests, 3 OS × 3 repeats, `--test-threads=1`                                                                                                                                                                                                                            |
| [`.github/workflows/miri-smoke.yml`](../../.github/workflows/miri-smoke.yml)                   | Soft nightly / dispatch: `cargo miri test --test race_model` (`continue-on-error`)                                                                                                                                                                                               |
| [`.github/workflows/miri-permutation.yml`](../../.github/workflows/miri-permutation.yml)       | Blocking permutation SelfCheck + `cargo miri test --test race_model`                                                                                                                                                                                                             |
| [`.github/workflows/loom-smoke.yml`](../../.github/workflows/loom-smoke.yml)                   | Soft SelfCheck + `RUSTFLAGS='--cfg loom'` `loom_model` (`continue-on-error`)                                                                                                                                                                                                     |
| [`.github/workflows/loom-permutation.yml`](../../.github/workflows/loom-permutation.yml)       | Blocking permutation SelfCheck + split `loom_model` core/daemon suites under `RUSTFLAGS='--cfg loom'`                                                                                                                                                                            |
| [`.github/workflows/shuttle-soft.yml`](../../.github/workflows/shuttle-soft.yml)               | Soft hermetic shuttle SelfCheck only (`continue-on-error`)                                                                                                                                                                                                                       |
| [`.github/workflows/shuttle-permutation.yml`](../../.github/workflows/shuttle-permutation.yml) | Blocking permutation SelfCheck + `cargo test shuttle_permutation` (no shuttle crate)                                                                                                                                                                                             |
| [`.github/workflows/tsan-permutation.yml`](../../.github/workflows/tsan-permutation.yml)       | Blocking permutation SelfCheck + `cargo +nightly test --test race_model` under `-Zsanitizer=thread` (ubuntu x86_64)                                                                                                                                                              |

The model uses `try_send` (never blocks) and an `AtomicBool` cancel bit so
assertions are conservation / capacity based — no sleeps, no OS event timing.

Daemon unit coverage for the same contract lives in
`crates/sl-daemon/src/watcher.rs` (`scan_once_stops_when_cancelled_*`).

### Soft Miri smoke (nightly)

`miri-smoke.yml` is **non-blocking** (`continue-on-error: true`). It runs only
`tests/race_model.rs` (pure `std` concurrency) so the job does not pull
`rusqlite`/`zstd` FFI via `[target.'cfg(not(miri))'.dev-dependencies]`.
Schedule: nightly UTC; also `workflow_dispatch`. Failures surface as soft
signals — they do not gate merges. Blocking Miri permutation evidence lives in
`miri-permutation.yml` (see below).

### Miri permutation checkers

`miri-permutation.yml` is **blocking** on `pull_request` and `push` to `main`.
It:

1. Runs `scripts/miri-permutation-check.ps1 -SelfCheck` (docs/workflow/miri anchors).
2. Runs `cargo miri test --test race_model` with `MIRIFLAGS='-Zmiri-strict-provenance'`.

The job exercises the same pure-`std` `race_model` subset as soft
`miri-smoke.yml` — bounded `sync_channel` + cooperative cancel — without
pulling `rusqlite`/`zstd` FFI. `loom_model` under Miri and full tokio broadcast
/ daemon graph ports remain unpaid.

| Gate                                     | Status     | Evidence                                                   |
| ---------------------------------------- | ---------- | ---------------------------------------------------------- |
| Miri permutation SelfCheck               | **done**   | `scripts/miri-permutation-check.ps1 -SelfCheck`            |
| Miri permutation race_model CI           | **done**   | `.github/workflows/miri-permutation.yml` (blocking on PR)  |
| Soft Miri smoke (nightly)                | **done**   | `.github/workflows/miri-smoke.yml` (`continue-on-error`)   |
| loom_model under Miri                    | **unpaid** | Loom cfg graph + FFI still outside Miri permutation suite  |
| Full loom / shuttle permutation checkers | **unpaid** | Shuttle crate + live daemon ports still outside soft smoke |

Soft `miri-smoke.yml` remains `continue-on-error` for nightly signal; blocking
Miri permutation evidence lives in `miri-permutation.yml`.

### Soft loom smoke

`loom-smoke.yml` is **non-blocking** (`continue-on-error: true`). It:

1. Runs `scripts/loom-smoke-check.ps1 -SelfCheck` (docs/workflow/cfg anchors).
2. Runs `cargo test --test loom_model --release` with `RUSTFLAGS='--cfg loom'`.

Loom lives under `[target.'cfg(loom)'.dev-dependencies]` so ordinary
`cargo test` never builds it. `tests/loom_model.rs` keeps a `#[cfg(not(loom))]`
skip marker so the harness stays discoverable without special flags.

| Gate                                     | Status     | Evidence                                                                                                      |
| ---------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------- |
| Soft loom SelfCheck                      | **done**   | `scripts/loom-smoke-check.ps1 -SelfCheck` (+ `tests/loom_soft.rs`)                                            |
| Soft loom `loom_model` CI                | **done**   | `.github/workflows/loom-smoke.yml` (`continue-on-error`)                                                      |
| Soft shuttle SelfCheck                   | **done**   | `scripts/shuttle-soft-check.ps1 -SelfCheck` (+ `tests/shuttle_soft.rs`); [`shuttle-soft.md`](shuttle-soft.md) |
| Full loom / shuttle permutation checkers | **unpaid** | Tokio broadcast + live daemon graph still outside loom models                                                 |

Schedule: nightly UTC + `pull_request` + `workflow_dispatch`. Soft failures do
not gate merges.

### Loom permutation checkers

`loom-permutation.yml` is **blocking** on `pull_request`. It:

1. Runs `scripts/loom-permutation-check.ps1 -SelfCheck` (docs/workflow/cfg anchors).
2. Runs split `cargo test --test loom_model` core (`--skip daemon_`) and daemon (`daemon_`) suites with `RUSTFLAGS='--cfg loom'`.

`tests/loom_model.rs` expands the soft cancel/capacity smoke with loom-native
permutations for `race_model`'s bounded `try_send` (`bounded_try_send_respects_capacity`),
SSE broadcast epoch fan-out (`broadcast_epoch_fans_out_to_subscribers`,
`broadcast_epoch_monotonic_under_multi_bump`), the watcher bounded-queue → broadcast
pipeline (`watcher_pipeline_bounded_enqueue_under_cancel`,
`watcher_drain_bumps_sse_epoch_per_item`), cancel-guarded daemon-graph
conservation (`daemon_graph_pipeline_conserves_under_cancel`), and tokio-shaped
mpsc/broadcast/SSE graph ports (`daemon_mpsc_watcher_to_consumer_conserve`,
`daemon_mpsc_drain_triggers_broadcast_publish`, `daemon_broadcast_sse_triple_fanout`,
`daemon_graph_mpsc_broadcast_sse_pipeline`, `daemon_graph_shutdown_stops_mpsc_enqueue`).
These are conservation / capacity models — loom-shaped ports of the
`crates/sl-daemon` tokio `broadcast` / `mpsc` graph. Live tokio ports (real
`tokio::sync`) live in [`daemon-graph-hard.md`](daemon-graph-hard.md).

| Gate                                                           | Status     | Evidence                                                                                                                                                               |
| -------------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Loom permutation SelfCheck                                     | **done**   | `scripts/loom-permutation-check.ps1 -SelfCheck` (+ `tests/loom_permutation.rs`)                                                                                        |
| Loom permutation suite CI                                      | **done**   | `.github/workflows/loom-permutation.yml` (blocking on PR)                                                                                                              |
| Loom daemon-graph broadcast/SSE epoch permutations             | **done**   | `broadcast_epoch_*`, `watcher_drain_bumps_sse_epoch_per_item`, `daemon_graph_pipeline_conserves_under_cancel` in `tests/loom_model.rs`                                 |
| Loom tokio-shaped mpsc/broadcast/SSE daemon graph permutations | **done**   | `daemon_mpsc_*`, `daemon_broadcast_sse_triple_fanout`, `daemon_graph_mpsc_broadcast_sse_pipeline`, `daemon_graph_shutdown_stops_mpsc_enqueue` in `tests/loom_model.rs` |
| Live tokio mpsc/broadcast/SSE daemon graph ports               | **done**   | [`daemon-graph-hard.md`](daemon-graph-hard.md); `tests/daemon_graph_tokio.rs`; blocking `.github/workflows/daemon-graph-hard.yml`                                      |
| Full tokio broadcast / daemon graph under loom                 | **unpaid** | Process-level HTTP SSE soak under loom still outside loom permutation suite                                                                                            |
| Full loom / shuttle permutation checkers                       | **unpaid** | Shuttle crate still outside soft smoke                                                                                                                                 |

Soft `loom-smoke.yml` remains `continue-on-error` for nightly signal; blocking
permutation evidence lives in `loom-permutation.yml`.

### Soft shuttle

`shuttle-soft.yml` is **non-blocking** (`continue-on-error: true`). It runs only
`scripts/shuttle-soft-check.ps1 -SelfCheck` — docs/workflow/test anchors, **no**
`shuttle` crate on the Cargo graph. Blocking permutation evidence lives in
[`shuttle-permutation.yml`](../../.github/workflows/shuttle-permutation.yml);
details and cross-links live in [`shuttle-soft.md`](shuttle-soft.md).

### Shuttle permutation checkers

`shuttle-permutation.yml` is **blocking** on `pull_request`. It:

1. Runs `scripts/shuttle-permutation-check.ps1 -SelfCheck` (docs/workflow/cfg anchors).
2. Runs `cargo test shuttle_permutation --release` (hermetic wrapper; no shuttle crate).

`tests/race_model.rs` documents the unpaid permutation targets for a future
cfg-gated shuttle model: bounded `sync_channel` capacity conservation
(`bounded_capacity_is_respected_then_cancel_drains_exactly`) and concurrent
producer fan-in under cancel (`concurrent_producers_conserve_messages_under_cancel`).
These are conservation / capacity models — not a full port of
`crates/sl-daemon` tokio `broadcast` / `mpsc` graph.

| Gate                                              | Status     | Evidence                                                                              |
| ------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------- |
| Shuttle permutation SelfCheck                     | **done**   | `scripts/shuttle-permutation-check.ps1 -SelfCheck` (+ `tests/shuttle_permutation.rs`) |
| Shuttle permutation suite CI                      | **done**   | `.github/workflows/shuttle-permutation.yml` (blocking on PR)                          |
| Full tokio broadcast / daemon graph under shuttle | **unpaid** | Real `sl-daemon` watcher/SSE graph still outside shuttle permutation suite            |
| Full shuttle crate permutation                    | **unpaid** | `shuttle` crate + live daemon ports still outside hermetic permutation lane           |

Soft `shuttle-soft.yml` remains `continue-on-error` for nightly signal; blocking
permutation evidence lives in `shuttle-permutation.yml`.

### TSan permutation checkers

`tsan-permutation.yml` is **blocking** on `pull_request`. It:

1. Runs `scripts/tsan-permutation-check.ps1 -SelfCheck` (docs/workflow/path anchors).
2. Runs `cargo +nightly test --test race_model` with `RUSTFLAGS='-Zsanitizer=thread'`,
   `-Zbuild-std`, and `--target x86_64-unknown-linux-gnu` (requires `rust-src`).

The job exercises the same pure-`std` `race_model` subset as Miri permutation
— bounded `sync_channel` + cooperative cancel — without pulling `rusqlite`/`zstd`
FFI. Full tokio broadcast / daemon SSE graph ports under TSan remain unpaid.

| Gate                                           | Status     | Evidence                                                                        |
| ---------------------------------------------- | ---------- | ------------------------------------------------------------------------------- |
| TSan permutation SelfCheck                     | **done**   | `scripts/tsan-permutation-check.ps1 -SelfCheck` (+ `tests/tsan_permutation.rs`) |
| TSan permutation race_model CI                 | **done**   | `.github/workflows/tsan-permutation.yml` (blocking on PR; ubuntu x86_64)        |
| Full tokio broadcast / daemon graph under TSan | **unpaid** | Real `sl-daemon` watcher/SSE graph still outside TSan permutation suite         |
| Full daemon SSE graph ports under TSan         | **unpaid** | Live broadcast/SSE daemon ports still outside `race_model` TSan subset          |

## How to run locally

Prefer a worktree-local Cargo target dir so parallel agents do not collide:

```powershell
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w24-c00-loom"
cargo test --test race_smoke --test race_model --locked -- --test-threads=1
```

Repeat a few times when validating a concurrency change:

```powershell
1..3 | ForEach-Object {
  Write-Host "race model repeat $_/3"
  cargo test --test race_model --locked -- --test-threads=1
}
```

Miri (nightly + `miri` component; same subset as CI):

```powershell
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w28-c00-miri"
$env:MIRIFLAGS = "-Zmiri-strict-provenance"
rustup toolchain install nightly --component miri
cargo +nightly miri setup
cargo +nightly miri test --test race_model --locked -- --test-threads=1
```

Miri permutation SelfCheck (no miri download):

```powershell
pwsh ./scripts/miri-permutation-check.ps1 -SelfCheck
```

Blocking Miri permutation suite (same `race_model` subset as CI):

```powershell
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w37-c00-miri"
$env:MIRIFLAGS = "-Zmiri-strict-provenance"
cargo +nightly miri setup
cargo +nightly miri test --test race_model --locked -- --test-threads=1
```

Soft loom SelfCheck (no loom download):

```powershell
pwsh ./scripts/loom-smoke-check.ps1 -SelfCheck
```

Soft loom permutation smoke (pulls loom under `--cfg loom` only):

```powershell
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w31-c00-loom"
$env:RUSTFLAGS = "--cfg loom"
cargo test --test loom_model --release --locked -- --test-threads=1
```

Loom permutation SelfCheck (no loom download):

```powershell
pwsh ./scripts/loom-permutation-check.ps1 -SelfCheck
```

Blocking loom permutation suite (cfg-gated `loom_model`; CI splits core vs daemon graph):

```powershell
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w40-daemon-tokio"
$env:RUSTFLAGS = "--cfg loom"
cargo test --test loom_model --release --locked -- --test-threads=1 --skip daemon_
cargo test --test loom_model daemon_ --release --locked -- --test-threads=1
```

Soft shuttle SelfCheck (hermetic; no shuttle crate):

```powershell
pwsh ./scripts/shuttle-soft-check.ps1 -SelfCheck
```

Shuttle permutation SelfCheck (no shuttle crate download):

```powershell
pwsh ./scripts/shuttle-permutation-check.ps1 -SelfCheck
```

Blocking shuttle permutation suite (hermetic wrapper only):

```powershell
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w37-c00-shuttle"
cargo test shuttle_permutation --release --locked -- --test-threads=1
```

TSan permutation SelfCheck (no nightly TSan build):

```powershell
pwsh ./scripts/tsan-permutation-check.ps1 -SelfCheck
```

Blocking TSan permutation suite (Linux nightly + `rust-src` only):

```powershell
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w38-c00-tsan"
$env:RUSTFLAGS = "-Zsanitizer=thread"
rustup toolchain install nightly --component rust-src
rustup target add x86_64-unknown-linux-gnu
cargo +nightly test --test race_model -Zbuild-std --target x86_64-unknown-linux-gnu --locked -- --test-threads=1
```

Hermetic TSan permutation wrapper (default `cargo test`):

```powershell
cargo test tsan_permutation --release --locked -- --test-threads=1
```

## Loom / shuttle follow-up

Full loom / shuttle / TSan coverage of daemon broadcast/SSE and a loom-native
port of `race_model`'s `sync_channel` remain unpaid. Soft shuttle SelfCheck does
**not** pay that debt. Keep permutation jobs off the default PR matrix so ordinary
`cargo test` stays green without special flags.

<!-- Live tokio mpsc/broadcast/SSE daemon graph ports | **done** -->
<!-- Miri permutation SelfCheck | **done** -->
<!-- Loom permutation SelfCheck | **done** -->
<!-- Soft loom SelfCheck | **done** -->
<!-- Shuttle permutation SelfCheck | **done** -->
<!-- Shuttle permutation suite CI | **done** -->
<!-- TSan permutation SelfCheck | **done** -->
<!-- TSan permutation race_model CI | **done** -->
<!-- Loom permutation SelfCheck | **done** -->
<!-- Loom permutation suite CI | **done** -->
<!-- Full tokio broadcast / daemon graph under loom | **unpaid** -->
<!-- Full loom / shuttle permutation checkers | **unpaid** -->
<!-- Full tokio broadcast / daemon graph under shuttle | **unpaid** -->
<!-- Full shuttle crate permutation | **unpaid** -->
<!-- Loom daemon-graph broadcast/SSE epoch permutations | **done** -->
<!-- Loom tokio-shaped mpsc/broadcast/SSE daemon graph permutations | **done** -->
<!-- Miri permutation race_model CI | **done** -->
<!-- Full daemon SSE graph ports under TSan | **unpaid** -->
