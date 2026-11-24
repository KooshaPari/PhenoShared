# Continuous profiling agent stub (L45 evidence)

SessionLedger ships **on-demand** loopback CPU profiling when
`SL_ENABLE_PPROF=1` (Wave-27 [#232](https://github.com/KooshaPari/SessionLedger/pull/232)).
This document describes the **soft continuous-profiling agent stub**: operator
docs, a one-shot agent loop script, optional soft HTTP sample push, and
scheduled CI evidence that reuses [`pprof-smoke.ps1`](../../scripts/pprof-smoke.ps1)
without requiring Windows CPU sampling.

## What exists today

| Layer                    | Status     | Evidence                                                                                      |
| ------------------------ | ---------- | --------------------------------------------------------------------------------------------- |
| On-demand unix pprof     | **landed** | `GET /debug/pprof/profile` protobuf via `pprof-rs` when gated (#232)                          |
| Operator smoke           | **landed** | [`scripts/pprof-smoke.ps1`](../../scripts/pprof-smoke.ps1)                                    |
| Scheduled pprof smoke    | **landed** | `pprof-smoke` job in [`.github/workflows/ops-load.yml`](../../.github/workflows/ops-load.yml) |
| Continuous agent sidecar | **stub**   | [`scripts/continuous-profiling-agent.ps1`](../../scripts/continuous-profiling-agent.ps1)      |
| Soft HTTP profile push   | **soft**   | `push_backend: http_soft` + optional `SL_PROFILE_PUSH_URL`                                    |
| Pyroscope / OTLP push    | **unpaid** | Full profiling exporters / auth wiring                                                        |
| Windows CPU sampler      | **unpaid** | `501` platform stub — SIGPROF sampler is unix-only                                            |

See also the gated operator contract in
[`observability.md`](observability.md#local-pprof-style-profiling).

## Agent loop (intended)

The continuous agent is a **loopback sidecar** (or in-process task) that polls
the same surface operators use manually:

```text
┌─────────────┐   SL_ENABLE_PPROF=1    ┌──────────────────┐
│ sl-daemon   │◄──── loopback only ───►│ profiling agent  │
│ /debug/pprof│   GET profile?seconds=N │ (stub today)     │
└─────────────┘                        └────────┬─────────┘
                                                │
                     http_soft + URL ───────────┼──► optional soft HTTP POST
                                                │
                     unpaid ────────────────────┼──► Pyroscope / OTLP backend
                                                │
                     stub retains ──────────────┴──► local samples dir
```

1. **Discover** — attach to `http://127.0.0.1:<port>` (daemon must be loopback-bound).
2. **Sample** — `GET /debug/pprof/profile?seconds=N` on a fixed interval.
3. **Retain** — keep the last _N_ protobuf files locally (always).
4. **Push** — optional soft HTTP upload when `push_backend` is `http_soft` and
   `SL_PROFILE_PUSH_URL` is set; otherwise retain-only.

The stub script runs **one** poll cycle for CI/operator proof. A long-running
deployment would wrap the same steps in a `while` loop with backoff and disk
rotation.

## Stub configuration

[`continuous-profiling.json`](continuous-profiling.json) pins the agent knobs:

| Field                   | Default     | Meaning                                                           |
| ----------------------- | ----------- | ----------------------------------------------------------------- |
| `sample_seconds`        | `1`         | CPU window per `GET /debug/pprof/profile`                         |
| `poll_interval_seconds` | `30`        | Intended spacing between agent polls (documented; stub runs once) |
| `retain_samples`        | `3`         | Local rotation ceiling for retained `.pb` files                   |
| `push_backend`          | `http_soft` | `none` (no export) or `http_soft` (optional soft HTTP)            |

### Soft HTTP push (`http_soft`)

| Knob                  | Meaning                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------ |
| `SL_PROFILE_PUSH_URL` | Optional absolute URL. When unset, RunOnce retains samples and **skips** network.                |
| `-DryRun`             | Logs the intended POST (URL + byte length) without opening sockets.                              |
| Push failures         | Soft: warn and continue (local retain already succeeded); CI job uses `continue-on-error: true`. |

SelfCheck never reads `SL_PROFILE_PUSH_URL` for network I/O — it only proves
doc/config anchors hermetically.

## How to run

### Self-check (hermetic; CI default)

```powershell
pwsh ./scripts/continuous-profiling-agent.ps1 -SelfCheck
```

Validates the JSON schema, doc anchors (`http_soft`, `SL_PROFILE_PUSH_URL`,
`push_backend`, unpaid gaps, `pprof-smoke.ps1`), and that `pprof-smoke.ps1` is
present. No daemon and no network.

### One-shot agent cycle (unix)

Requires a built `sl-daemon`. On **Windows**, the script exits `0` with an
explicit skip — Windows pprof is not required for this evidence path.

```powershell
pwsh ./scripts/continuous-profiling-agent.ps1 -RunOnce -DaemonPath path/to/sl-daemon

# Soft HTTP (optional): set URL, or dry-run without network
$env:SL_PROFILE_PUSH_URL = "https://profiles.example.invalid/ingest"
pwsh ./scripts/continuous-profiling-agent.ps1 -RunOnce -DaemonPath path/to/sl-daemon -DryRun
```

On Linux/macOS the stub:

1. Starts a loopback daemon with `SL_ENABLE_PPROF=1`.
2. Fetches one CPU protobuf sample.
3. Writes it under a temp `samples/` directory and asserts non-empty bytes.
4. Optionally soft-POSTs the sample when `push_backend=http_soft` and
   `SL_PROFILE_PUSH_URL` is set (skipped under `-DryRun` or when URL unset).
5. Delegates contract checks to `pprof-smoke.ps1`.

### Attach to a running daemon

```powershell
SL_ENABLE_PPROF=1 sl serve --http-bind 127.0.0.1:8080
pwsh ./scripts/continuous-profiling-agent.ps1 -AttachOnly -BaseUrl http://127.0.0.1:8080
```

When the gate is off (`404`), attach mode exits `0` with `skip` — same as
`pprof-smoke.ps1 -AttachOnly`.

## CI / scheduling

| Job                          | Workflow                                               | Blocking?                            | Platform        |
| ---------------------------- | ------------------------------------------------------ | ------------------------------------ | --------------- |
| `pprof-smoke`                | [`ops-load.yml`](../../.github/workflows/ops-load.yml) | yes                                  | `ubuntu-latest` |
| `continuous-profiling-agent` | [`ops-load.yml`](../../.github/workflows/ops-load.yml) | **soft** (`continue-on-error: true`) | `ubuntu-latest` |

The soft `continuous-profiling-agent` job runs weekly (same cadence as other
`ops-load` smokes) plus `workflow_dispatch`. It exercises SelfCheck + the stub
agent loop without gating merges and without requiring `SL_PROFILE_PUSH_URL`.

## Unpaid gaps (explicit)

These remain **out of scope** for the soft stub; score stays partial until addressed:

1. **Pyroscope / OTLP profiling export** — no dedicated push client, auth, or backend wiring beyond optional soft HTTP POST.
2. **Long-running agent deployment** — no systemd/compose unit; operators run the script manually.
3. **Windows CPU sampler parity** — `pprof-rs` SIGPROF path is unix-only; Windows CI does not assert protobuf profiles.
4. **Production enablement** — `SL_ENABLE_PPROF` stays off by default; continuous profiling is local-only evidence unless operators opt into soft HTTP.

Until a full exporter lands, on-demand unix pprof (#232) plus this stub (local
retain + optional `http_soft`) document the boundary.
