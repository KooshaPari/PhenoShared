# Feedback-loop budgets (L30.10)

Measured (or explicitly labeled) wall-clock budgets for the fast inner loop.
These numbers guide local iteration; they are **advisory** for CI — do not fail
pull requests on wall-clock regressions unless a future gate documents a
generous threshold and opt-in enforcement.

## Fast-loop commands

`sl-daemon` is a separate Cargo workspace (excluded from the root workspace so
macOS can resolve without the viewer/webkit graph). Prefer the Makefile /
manifest-path forms:

| Intent                 | Command                                                                                         |
| ---------------------- | ----------------------------------------------------------------------------------------------- |
| Daemon typecheck       | `cargo check --manifest-path crates/sl-daemon/Cargo.toml`                                       |
| Daemon tests           | `cargo test --manifest-path crates/sl-daemon/Cargo.toml`                                        |
| CI-equivalent lint     | `make lint` (fmt `--check` + clippy for root workspace + daemon)                                |
| Optional faster runner | `cargo nextest run --manifest-path crates/sl-daemon/Cargo.toml` (see [nextest](#cargo-nextest)) |

`AGENTS.md` / `llms.txt` still mention `cargo test -p sl-daemon` as shorthand;
that only works if you `cd crates/sl-daemon` (or pass `--manifest-path`).

## Baseline table (warm incremental)

| Command                                                   | Budget (advisory) | Measured mean                                                                                                         | Host / date                                      | method                                                           |
| --------------------------------------------------------- | ----------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ | ---------------------------------------------------------------- |
| `cargo check --manifest-path crates/sl-daemon/Cargo.toml` | ≤ 15 s            | ~1.7–4.3 s                                                                                                            | Windows 10, cargo 1.96, warm target · 2026-07-14 | `cargo` / `Measure-Command` (hyperfine preferred when installed) |
| `cargo test --manifest-path crates/sl-daemon/Cargo.toml`  | ≤ 30 s            | ~4.7 s (138+ unit/integration tests after warm build)                                                                 | same                                             | `cargo` / `Measure-Command`                                      |
| `make lint`                                               | ≤ 180 s           | partial: daemon `clippy --all-targets` ~27 s + `fmt --check` ~10 s (full `make lint` also runs root-workspace clippy) | same                                             | `cargo` / `Measure-Command`                                      |

Notes:

- **Warm** means a prior successful compile of the same crate already filled
  `target/` (or a shared worktree target). Cold builds are intentionally
  excluded from the advisory budgets above.
- First `cargo test` after a clean target can exceed 2 minutes while compiling
  test binaries; that is expected and not a loop-speed regression.
- Budgets are generous relative to measured means so machine noise, AV, and
  shared CI runners do not trip false alarms if someone later wires a soft gate.

## Repeatable measurement procedure

Use this whenever refreshing the table. Prefer [hyperfine](https://github.com/sharkdp/hyperfine) when available; otherwise PowerShell `Measure-Command`.

### With hyperfine

```powershell
# From repo root, after one warm run of each command:
hyperfine --warmup 1 --runs 5 `
  "cargo check --manifest-path crates/sl-daemon/Cargo.toml"
hyperfine --warmup 1 --runs 3 `
  "cargo test --manifest-path crates/sl-daemon/Cargo.toml --quiet"
# lint is long; fewer runs are fine:
hyperfine --warmup 0 --runs 2 "make lint"
```

Record: host OS, `cargo --version`, whether `RUSTC_WRAPPER=sccache` was set,
warmup count, runs, mean ± σ, and commit SHA. Update the table cells and the
`Host / date` column.

### Without hyperfine

```powershell
pwsh -NoProfile -File scripts/feedback-budget-check.ps1 -Measure -ArtifactPath artifacts/feedback-budget.json
```

`-Measure` writes a JSON artifact with wall times. It does **not** fail on
budget overrun (advisory only). CI smoke uses the default mode (doc/script
presence only).

## cargo-nextest

Repo defaults live in [`.config/nextest.toml`](../../.config/nextest.toml).
The daemon workspace also has
[`crates/sl-daemon/.config/nextest.toml`](../../crates/sl-daemon/.config/nextest.toml)
so `cargo nextest` from that manifest picks up the same profile.

Install once: `cargo install cargo-nextest --locked`.

```powershell
cargo nextest run --manifest-path crates/sl-daemon/Cargo.toml
```

## Optional sccache

To speed repeated cold-ish rebuilds across worktrees:

```powershell
cargo install sccache --locked
$env:RUSTC_WRAPPER = "sccache"
# optional: $env:SCCACHE_DIR = "C:\Users\<you>\.cache\sccache"
```

Document whether sccache was enabled when publishing new measured means.
sccache is optional; CI already uses `Swatinem/rust-cache` for dependency
caching and does not require a local sccache daemon.

## CI policy

`scripts/feedback-budget-check.ps1` (no `-Measure`) only asserts that this doc
and the script itself exist — a non-flaky smoke for L30.10 evidence. Wall-clock
comparisons remain local/advisory until a future change documents an explicit
enforcement threshold.
