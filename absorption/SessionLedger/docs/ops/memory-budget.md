# Memory & allocation budget (L8 evidence)

SessionLedger's Memory & Allocation lane starts with a **generous RSS / working-set
smoke** on the `sl-daemon` ingest path (`POST /api/ingest`). This is score-1
evidence only: it catches gross regressions, not allocator-level waste.

A cheap counting-allocator companion lives in
[`allocation-budget.md`](allocation-budget.md) (`process_session` heap deltas via
`stats_alloc`). Optional feature-gated `dhat` heap smoke lives in
[`alloc-profile.md`](alloc-profile.md). Continuous jemalloc profiling and optional
`bytes::Bytes` / `Cow` zero-copy work remain follow-ups.

## Ceiling

| Knob                       | Value                                                                                                                     | Source                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Default ingest RSS ceiling | **512 MiB** (`536870912` bytes)                                                                                           | [`memory-budget.json`](memory-budget.json) `ingest_rss_ceiling_bytes`                 |
| Metric sampled             | Resident set / working set                                                                                                | Linux: `/proc/<pid>/status` `VmRSS`; Windows/other: PowerShell `Process.WorkingSet64` |
| Failure rule               | Exit non-zero only if peak RSS **exceeds** the ceiling, or if RSS sampling / daemon readiness / ingest unexpectedly fails | [`scripts/rss-budget-check.ps1`](../../scripts/rss-budget-check.ps1)                  |

The ceiling is intentionally loose for a short debug-build ingest burst. Tighten
it after allocator profiling lands — do not treat 512 MiB as a production SLA.

Override at runtime:

```powershell
pwsh ./scripts/rss-budget-check.ps1 -CeilingBytes 268435456   # 256 MiB
```

## How to run

### Self-check (no daemon; hermetic)

Proves the script parses parameters and loads a positive ceiling from config:

```powershell
pwsh ./scripts/rss-budget-check.ps1 -SelfCheck
```

### Full smoke (starts a local daemon)

Prefer a worktree-local Cargo target dir so parallel agents do not collide:

```powershell
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w23-c00-rss"
pwsh ./scripts/rss-budget-check.ps1
```

Or pass an already-built binary:

```powershell
pwsh ./scripts/rss-budget-check.ps1 -DaemonPath .\target-w23-c00-rss\debug\sl-daemon.exe -SkipBuild
```

### Attach to a running daemon

```powershell
# Terminal A
cargo run --manifest-path crates/sl-daemon/Cargo.toml -- `
  serve --watch .sl-watch --out .sl-data --http-bind 127.0.0.1:8080

# Terminal B
pwsh ./scripts/rss-budget-check.ps1 -AttachOnly -BaseUrl http://127.0.0.1:8080
```

Wall-clock once the binary exists: typically **well under two minutes** (ready
wait + small ingest burst + a few RSS samples).

## What the smoke does

1. Resolve ceiling from [`memory-budget.json`](memory-budget.json) (or `-CeilingBytes`).
2. Start `sl-daemon serve` on an ephemeral loopback port (unless `-AttachOnly`).
3. Wait for `/readyz` → `200`.
4. Sample RSS, then `POST /api/ingest` a small OKF JSON body several times.
5. Re-sample RSS; keep the peak.
6. Fail if peak > ceiling, or if sampling / readiness / ingest fails unexpectedly.

## Platform notes

| Platform          | RSS source                        | Notes                                                                             |
| ----------------- | --------------------------------- | --------------------------------------------------------------------------------- |
| Linux (pwsh 7+)   | `VmRSS` from `/proc/<pid>/status` | Preferred when `/proc` is available.                                              |
| Windows (pwsh 7+) | `Get-Process … WorkingSet64`      | Working set, not private bytes; still suitable for a generous regression ceiling. |
| macOS (pwsh 7+)   | `WorkingSet64`                    | No `/proc`; treat as best-effort working-set proxy.                               |

Requires **PowerShell 7+**. The smoke is hermetic: temp watch/out dirs under
`$RUNNER_TEMP` or the system temp path; no external network.

## CI / scheduling

Primary evidence is **manual or scheduled**, not a PR-blocking gate:

- Soft job in [`.github/workflows/ops-load.yml`](../../.github/workflows/ops-load.yml)
  (`rss-budget`, `continue-on-error: true`) on the same weekly / `workflow_dispatch`
  cadence as the load smoke.
- Local / PR proof without a daemon: `pwsh ./scripts/rss-budget-check.ps1 -SelfCheck`
  (also covered by `cargo test --test memory_budget`).

A hard CI fail on RSS would be noisy across debug vs release and OS differences;
keep this soft until allocator profiling tightens the budget.

## Limitations

- Measures **process RSS / working set**, not heap allocations or peak during a
  single request frame.
- Debug builds and cold caches inflate RSS; the ceiling accounts for that.
- Does not enable `dhat`, jemalloc, or production `#[global_allocator]` instrumentation
  (see [`allocation-budget.md`](allocation-budget.md) for the test-only counting smoke).
- Does not prove zero-copy (`Bytes` / `Cow`) on the ingest body path.
- Attach mode requires a discoverable `sl-daemon` process name on the host.
