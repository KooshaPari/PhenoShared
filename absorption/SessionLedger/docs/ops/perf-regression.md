# Pipeline Performance Regression Gate

SessionLedger **enforces** a blocking pipeline Criterion budget gate against the
checked-in baseline at [`perf-baseline.json`](perf-baseline.json).

The GitHub Actions workflow [`.github/workflows/bench-gate.yml`](../../.github/workflows/bench-gate.yml)
runs on every pull request and push to `main`. Both the mean-budget and p95-latency
jobs are **blocking**: neither sets `continue-on-error`. A mean or p95 budget
overrun fails the check.

## Thresholds (SSOT)

Policy lives in `docs/ops/perf-baseline.json`:

### Blocking mean budgets (`policy.enforced=true`)

| Field                 | Value   | Meaning                                      |
| --------------------- | ------- | -------------------------------------------- |
| `threshold_percent`   | **25%** | Max allowed slowdown vs checked-in `mean_ns` |
| `sample_size`         | 10      | Criterion samples per benchmark (CI-fast)    |
| `warm_up_seconds`     | 1.0     | Criterion warm-up                            |
| `measurement_seconds` | 2.0     | Criterion measurement window                 |

Per-benchmark absolute ceilings (`budget_mean_ns` = `mean_ns × (1 + threshold_percent/100)`):

| Benchmark                               | Baseline `mean_ns` | Enforced `budget_mean_ns` |
| --------------------------------------- | -----------------: | ------------------------: |
| `pipeline/distill_compile_200_messages` |      1,081,439.870 |             1,351,799.838 |
| `pipeline/okf_export_200_messages`      |          6,607.678 |                 8,259.598 |
| `pipeline/inject_render_200_messages`   |         13,362.599 |                16,703.249 |

### Enforced p95 latency budgets (`latency.enforced=true`)

| Field                                | Value                  | Meaning                                                 |
| ------------------------------------ | ---------------------- | ------------------------------------------------------- |
| `latency.threshold_percent`          | **25%**                | Max allowed slowdown vs checked-in `p95_ns`             |
| `latency.metric`                     | `criterion_sample_p95` | p95 of per-iteration times from Criterion `sample.json` |
| `latency.http_load_smoke.max_p95_ms` | **500**                | Aligns with `scripts/load-smoke.ps1 -MaxP95Ms`          |

Per-benchmark enforced ceilings (`budget_p95_ns` = `p95_ns × (1 + latency.threshold_percent/100)`):

| Benchmark                               | Baseline `p95_ns` | Enforced `budget_p95_ns` |
| --------------------------------------- | ----------------: | -----------------------: |
| `pipeline/distill_compile_200_messages` |     1,243,655.851 |            1,554,569.814 |
| `pipeline/okf_export_200_messages`      |         7,598.830 |                9,498.538 |
| `pipeline/inject_render_200_messages`   |        15,366.989 |               19,208.737 |

Provisional `p95_ns` values start at ≈ `mean_ns × 1.15` until refreshed with
`-UpdateBaseline`. p95 overruns **fail** the blocking pipeline perf gate when
`latency.enforced=true`. Recent `ubuntu-latest` bench-gate runs showed ~50–70%
headroom under these ceilings before promotion (Wave-30 C00).

Units for pipeline benches are Criterion estimates in **nanoseconds**. HTTP
load-smoke latency is in **milliseconds**.

## What The Gate Measures

Policy / doc smoke (no cargo bench):

```powershell
./scripts/bench-gate.ps1 -SelfCheck
./scripts/bench-gate.ps1 -SoftLatencyCheck   # C00 L6 latency baseline schema only
```

Full enforced gate (mean + p95 when Criterion samples exist):

```powershell
./scripts/bench-gate.ps1
```

The script executes:

```powershell
cargo bench --locked --bench pipeline -- --save-baseline current
```

For CI speed, `scripts/bench-gate.ps1` sets the Criterion sample size to 10 with
1 second of warm-up and 2 seconds of measurement per benchmark. That keeps the
gate suitable for pull requests while still exercising the existing Criterion
benchmark code. The measured operations are:

- `pipeline/distill_compile_200_messages`
- `pipeline/okf_export_200_messages`
- `pipeline/inject_render_200_messages`

## Failure Policy

The gate compares Criterion's saved `mean.point_estimate` values from the
`current` baseline to each checked-in `budget_mean_ns` ceiling. A benchmark
**fails CI** when:

```text
current_mean_ns > budget_mean_ns
```

Equivalently: when the run is more than `policy.threshold_percent` slower than
the checked-in `mean_ns`. Soft / advisory mode is not supported for means —
`policy.enforced` must remain `true`.

Enforced p95 latency (C00 L6):

```text
current_p95_ns > budget_p95_ns
```

With `latency.enforced=true`, that condition **fails CI** alongside mean
overruns. To demote back to warn-only (not recommended once enforced), set
`latency.enforced=false` in `perf-baseline.json` and remove
`continue-on-error` from the latency jobs if re-added.

On failure the script exits **1**, prints each overrun, writes
`artifacts/pipeline-perf-gate.json`, and appends a GitHub step summary when
`GITHUB_STEP_SUMMARY` is set.

A failure should be treated as a regression until proven otherwise. Re-run the
gate on a quiet machine before changing the baseline.

## Refreshing The Baseline

Refresh the baseline only when the pipeline intentionally becomes slower, the
benchmark workload changes, or repeated runs show that the existing baseline is
stale for the supported CI environment. Run `./scripts/eval-repro-check.ps1`
first so lockfile and fixture anchors still match [`eval-manifest.json`](eval-manifest.json).

Run:

```powershell
./scripts/bench-gate.ps1 -UpdateBaseline
```

Review the printed Criterion output, inspect the JSON diff in
`docs/ops/perf-baseline.json` (means, p95 latency, and derived budgets), and
commit the baseline update with the code or benchmark change that justified it.
Do not refresh the baseline just to hide an unexplained pull-request regression.

## Local task aliases

```text
just bench-gate              # full Criterion gate
just bench-gate-check        # SelfCheck (mean + latency schema)
just bench-gate-latency      # SoftLatencyCheck only
make bench-gate              # Makefile fallback → scripts/bench-gate.ps1
```
