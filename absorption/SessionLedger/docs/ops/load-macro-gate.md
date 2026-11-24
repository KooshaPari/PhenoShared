# Load-macro gate (C08 L73 macro route tier)

Status: **C08 L73** — promotes product **macro** HTTP routes (`/api/bundles`,
`/api/search`, `/api/stream`) into a **blocking PR load-smoke gate** while
retaining the existing **probe** tier (`/healthz`, `/readyz`, `/api/metrics`,
`/metrics`) on the soft weekly `ops-load.yml` schedule.

Machine proof: `pwsh ./scripts/load-macro-gate-check.ps1 -SelfCheck`.

Policy manifest: [`load-macro-gate.json`](load-macro-gate.json).

Related: [`scripts/load-smoke.ps1`](../../scripts/load-smoke.ps1),
[`.github/workflows/load-macro-gate-hard.yml`](../../.github/workflows/load-macro-gate-hard.yml),
[`.github/workflows/ops-load.yml`](../../.github/workflows/ops-load.yml),
[`test-pyramid.md`](test-pyramid.md), [`runbook.md`](runbook.md).

## Route tiers

| Tier                | Routes                                               | CI mode                                |
| ------------------- | ---------------------------------------------------- | -------------------------------------- |
| **probe** (default) | `/healthz`, `/readyz`, `/api/metrics`, `/metrics`    | Soft weekly `ops-load.yml`             |
| **macro**           | `/api/bundles`, `/api/search?limit=1`, `/api/stream` | Blocking PR `load-macro-gate-hard.yml` |
| **all**             | probe + macro                                        | Manual / future expansion              |

Before the macro tier runs, the gate seeds one `POST /api/ingest` bundle so
`/api/bundles` and `/api/search` have data. `/api/stream` is probed **once**
with `HttpCompletionOption.ResponseHeadersRead` (SSE headers only; no body drain).

## SLO defaults (PR smoke)

| Knob             | Value      | Source                                                                |
| ---------------- | ---------- | --------------------------------------------------------------------- |
| Requests         | **60**     | `load-macro-gate.json` `pr_smoke.requests`                            |
| Concurrency      | **8**      | `pr_smoke.concurrency`                                                |
| Min success rate | **99%**    | `pr_smoke.min_success_rate_percent`                                   |
| Max p95          | **500 ms** | aligns with `perf-baseline.json` `latency.http_load_smoke.max_p95_ms` |

## How to run

### SelfCheck (hermetic; no daemon)

```powershell
pwsh ./scripts/load-macro-gate-check.ps1 -SelfCheck
```

### Macro route smoke (local; requires PowerShell 7)

```powershell
pwsh ./scripts/load-macro-gate-check.ps1 -RunSmoke
```

Or with a running daemon:

```powershell
pwsh ./scripts/load-smoke.ps1 -BaseUrl http://127.0.0.1:8080 -RouteTier macro
```

## CI / scheduling

| Gate                  | Workflow                                          | Mode                         | Evidence                                  |
| --------------------- | ------------------------------------------------- | ---------------------------- | ----------------------------------------- |
| Probe-tier load smoke | `ops-load.yml`                                    | **soft** (weekly + dispatch) | Existing health/metrics SLO               |
| Macro-tier SelfCheck  | `load-macro-gate-hard.yml`                        | **blocking**                 | Docs + workflow anchors                   |
| Macro-tier live smoke | `load-macro-gate-hard.yml` (`macro routes smoke`) | **blocking**                 | Daemon + ingest seed + `-RouteTier macro` |

### Soft vs hard gates

| Gate                                              | Status     | Evidence                                     |
| ------------------------------------------------- | ---------- | -------------------------------------------- |
| Soft probe-tier `ops-load.yml`                    | **done**   | Unchanged weekly schedule                    |
| Blocking load-macro-gate-hard CI workflow         | **done**   | `.github/workflows/load-macro-gate-hard.yml` |
| `tests/load_macro_gate.rs` cargo wrapper          | **done**   | Hermetic SelfCheck anchor smoke              |
| Full write/search/stream soak at production scale | **unpaid** | Effort M; beyond PR smoke breadth            |

## Done / unpaid

| Item                                           | Status                        |
| ---------------------------------------------- | ----------------------------- |
| Policy SSOT + JSON manifest                    | **done**                      |
| `load-smoke.ps1 -RouteTier macro`              | **done**                      |
| Blocking `load-macro-gate-hard.yml`            | **done**                      |
| `tests/load_macro_gate.rs` cargo wrapper       | **done**                      |
| Trend publication / stable-hardware baselines  | **unpaid** — C08 L73 residual |
| <!-- Blocking load-macro-gate-hard CI workflow | **done** -->                  |
