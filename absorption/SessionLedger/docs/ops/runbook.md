# Runbook — local SessionLedger

How to run the daemon + viewer stack and verify liveness / readiness.

## Prerequisites

- Exact rustc from `rust-toolchain.toml` (see `docs/ops/rustc-toolchain-pin.md`; MSRV 1.85+)
- [`process-compose`](https://github.com/F1bonacc1/process-compose) on `PATH` (default runtime)
- Optional: Dioxus CLI for viewer bundling (`cargo install dioxus-cli`)
- Optional engines (Podman, WSL, Apple Container, PhenoCompose/nvms): see
  [`runtime-facade.md`](runtime-facade.md)

## Start (`make dev` / runtime facade)

**Default** local stack is still **process-compose** (zero hard deps beyond that
CLI). Prefer the runtime facade when you want engine selection via `SL_RUNTIME`:

```bash
./scripts/runtime-up.sh                 # Linux/macOS — process-compose by default
pwsh ./scripts/runtime-up.ps1           # Windows
# optional: SL_RUNTIME=podman|pheno|wsl|apple
```

From repo root with Make:

```bash
make build          # cargo build -p sl-daemon -p sl-viewer
make dev            # build, then process-compose up
```

`process-compose.yaml` starts:

| Process     | Command                           | Notes                                         |
| ----------- | --------------------------------- | --------------------------------------------- |
| `sl-daemon` | `cargo run -p sl-daemon -- serve` | `SL_PORT=8080`, `SL_DATA_DIR=./.sl-data`      |
| `sl-viewer` | `cargo run -p sl-viewer`          | waits until daemon **readiness** probe passes |

Tear down:

```bash
make dev-down
# or: process-compose down
```

Manual (without process-compose):

```bash
cargo run -p sl-daemon -- serve
cargo run -p sl-viewer
```

Engine matrix, PhenoCompose/nvms delegation, Podman/`Containerfile`, WSL, and
Apple Container: [`runtime-facade.md`](runtime-facade.md). ADR 0001 keeps this
CLI/HTTP-only (no tray companion).

## Health check

Two probes — do not conflate them. Full policy:
[`observability.md`](observability.md#healthz-vs-readyz).

| Probe          | Meaning                                        | Expect                          |
| -------------- | ---------------------------------------------- | ------------------------------- |
| `GET /healthz` | **Liveness** — process accepts HTTP            | `200`, body `ok`                |
| `GET /readyz`  | **Readiness** — `out_dir` exists and is usable | `200`, body `ready`; else `503` |

```bash
curl -s -o /dev/null -w "%{http_code} " http://127.0.0.1:8080/healthz
curl -s http://127.0.0.1:8080/healthz
# 200 ok

curl -s -o /dev/null -w "%{http_code} " http://127.0.0.1:8080/readyz
curl -s http://127.0.0.1:8080/readyz
# 200 ready  (requires SL_DATA_DIR / out_dir to exist)
# 503        if out_dir missing — daemon may still be "alive" on /healthz
```

Readiness probe in `process-compose.yaml` hits **`/readyz`** on port **8080**
(`initial_delay_seconds: 3`). Viewer start depends on that probe, not `/healthz`.

If `/healthz` is `ok` but `/readyz` is `503`: create/fix `SL_DATA_DIR` (default
`./.sl-data`); do not treat it as a crash loop by itself.

## Metrics

```bash
curl -s http://127.0.0.1:8080/api/metrics | jq .
```

Returns `total_bundles`, `total_tokens`, `avg_tokens`, `model_counts`,
`daily_counts` over JSON bundles in the data/out directory. See
[`observability.md`](observability.md) for RED mapping and SLO stubs.

## Headless load smoke

Start `sl-daemon` with a valid data directory, then run the PowerShell 7 load
smoke from another terminal. No viewer or GUI is required.

```powershell
New-Item -ItemType Directory -Force .sl-watch, .sl-data | Out-Null
cargo run --manifest-path crates/sl-daemon/Cargo.toml -- `
  serve --watch .sl-watch --out .sl-data
```

```powershell
pwsh ./scripts/load-smoke.ps1 `
  -BaseUrl http://127.0.0.1:8080 `
  -Requests 400 `
  -Concurrency 20 `
  -MinSuccessRate 99 `
  -MaxP95Ms 500
```

The request count is distributed evenly across probe routes by default
(`/healthz`, `/readyz`, `/api/metrics`, `/metrics`). Use `-RouteTier macro` for
product routes (`/api/bundles`, `/api/search`, `/api/stream`); see
[`load-macro-gate.md`](load-macro-gate.md). The script prints per-endpoint results and an
overall success rate and p95 latency. It exits non-zero if the success rate is
below `MinSuccessRate` or p95 exceeds `MaxP95Ms`, so the same command can be
used as a non-blocking nightly or pre-release smoke check. A `503` from
`/readyz` counts as a failure; ensure the directory passed to `--out` exists
before testing.

For a shorter operational chaos pass (readiness fault, metrics shape, kill +
recovery, mini load), run `scripts/ops-chaos-smoke.ps1` after building
`sl-daemon`. CI runs this on weekdays via
[`.github/workflows/ops-chaos-smoke.yml`](../../.github/workflows/ops-chaos-smoke.yml);
see [`observability.md`](observability.md) for the scheduled-evidence table.

## RSS / memory budget smoke (ingest)

For L8 Memory & Allocation evidence, run the RSS ceiling smoke against
`POST /api/ingest` (contract: [`memory-budget.md`](memory-budget.md)):

```powershell
pwsh ./scripts/rss-budget-check.ps1 -SelfCheck
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w23-c00-rss"
pwsh ./scripts/rss-budget-check.ps1
```

Default ceiling is **512 MiB** working-set / RSS after a small ingest burst.
The soft scheduled job lives in
[`.github/workflows/ops-load.yml`](../../.github/workflows/ops-load.yml).

## Allocation budget smoke (pipeline heap)

Cheap L8 companion to the RSS smoke — counting-allocator deltas over one
`process_session()` pass (contract: [`allocation-budget.md`](allocation-budget.md)):

```powershell
pwsh ./scripts/allocation-budget-check.ps1 -SelfCheck
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w27-c00-alloc"
pwsh ./scripts/allocation-budget-check.ps1
```

Default ceilings are **1 MiB** bytes allocated and **5 000** allocations for the
8-message fixture. Soft scheduled job: `allocation-budget` in
[`.github/workflows/ops-load.yml`](../../.github/workflows/ops-load.yml).

## Allocator profile smoke (optional `dhat`)

Optional L8 companion beyond the counting-allocator smoke — `dhat` heap statistics
over one `process_session()` pass (contract: [`alloc-profile.md`](alloc-profile.md)):

```powershell
pwsh ./scripts/alloc-profile-check.ps1 -SelfCheck
$env:CARGO_TARGET_DIR = Join-Path $PWD "target-w29-c00-dhat"
pwsh ./scripts/alloc-profile-check.ps1
```

Requires `--features alloc-profile` for the full measurement; default CI only runs
the hermetic wiring via `cargo test --test alloc_profile`. Soft scheduled job:
`alloc-profile` in [`.github/workflows/ops-load.yml`](../../.github/workflows/ops-load.yml).

## Optional jemalloc (`sl-daemon`, soft)

Unix-only optional `#[global_allocator]` behind `--features jemalloc` (contract:
[`jemalloc.md`](jemalloc.md)). Default and Windows builds stay on the system
allocator.

```powershell
pwsh ./scripts/jemalloc-check.ps1 -SelfCheck
# Unix soft CI / local:
# cargo build --manifest-path crates/sl-daemon/Cargo.toml --features jemalloc --locked
```

Soft scheduled job: `jemalloc` in
[`.github/workflows/ops-load.yml`](../../.github/workflows/ops-load.yml)
(`continue-on-error: true`).

## Audit retention and review

The durable audit sink is append-only JSONL (default) or SQLite under
`<data_dir>/audit/`. `sl-daemon` never prunes it; operators rotate by moving or
copying files while the process is stopped. Full policy:
[`local-trust-boundary.md`](local-trust-boundary.md#retention-and-rotation-policy).

```powershell
# Tail recent audit events from the compose data root
pwsh ./scripts/audit-review.ps1 -DataDir ./.sl-data -Tail 20

# Export a date-bounded bundle for compliance review (local files only)
pwsh ./scripts/audit-review.ps1 -DataDir ./.sl-data -Since "2026-07-01" `
  -Export ./review/audit-export.jsonl
```

Audit review does not use HTTP; keep `sl serve` on loopback and treat exported
bundles like security-sensitive local metadata.

### Game-day chaos evidence

Quarterly game-day uses the same short smoke harness with machine-readable
evidence (schema `sessionledger.gameday-evidence.v1`). Full calendar and
checklist: [`observability.md`](observability.md#game-day-cadence).

**CI (recommended):** GitHub **Actions → Ops Game Day Evidence → Run workflow**
— uploads `gameday-evidence.json` as an artifact.

**Local:**

```powershell
cargo build -p sl-daemon
$daemon = Join-Path (cargo metadata --format-version 1 --no-deps --manifest-path crates/sl-daemon/Cargo.toml | ConvertFrom-Json).target_directory "debug/sl-daemon"
pwsh ./scripts/ops-chaos-smoke.ps1 `
  -DaemonPath $daemon `
  -EvidencePath docs/ops/fixtures/gameday-evidence.json
```

Sample output shape: [`fixtures/gameday-evidence.sample.json`](fixtures/gameday-evidence.sample.json).
After the run, exercise PromQL from [`alerts.md`](alerts.md#promql-for-shipped-red-metrics)
against a scraped target and walk one row of the
[routing table](alerts.md#alert-routing-evidence).

## Common failures

| Symptom                              | Likely cause                     | Fix                                                                                                          |
| ------------------------------------ | -------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `process-compose: command not found` | CLI missing                      | Install process-compose; or `./scripts/runtime-up.sh` error text; or run crates manually                     |
| `SL_RUNTIME=pheno` fails immediately | `pheno-compose` / `nvms` missing | Install per [`runtime-facade.md`](runtime-facade.md); or unset `SL_RUNTIME` for process-compose              |
| `SL_RUNTIME=podman` / `apple` fails  | Engine or Containerfile missing  | Install podman / Apple `container`; confirm root or `crates/sl-daemon` Containerfile                         |
| Viewer never starts                  | Daemon not **ready**             | Confirm `/readyz` returns `ready`; `/healthz` alone is insufficient; check port 8080 free; raise probe delay |
| `/healthz` ok, `/readyz` 503         | Missing or non-dir `out_dir`     | Ensure `SL_DATA_DIR` exists; mkdir if needed; restart serve                                                  |
| `Address already in use`             | Stale daemon                     | Kill process on 8080; `make dev-down`                                                                        |
| Empty metrics / bundles              | Wrong data dir                   | Set `SL_DATA_DIR`; ensure `*.okf.json` / `*.json` under out dir                                              |
| `cargo` / MSRV errors                | Wrong toolchain                  | `rustup show`; use repo `rust-toolchain.toml`                                                                |
| Viewer build fails (webkit)          | Platform GTK deps                | Prefer `cargo test -p sl-daemon` isolation; see `crates/sl-daemon/README.md`                                 |
| Ingest 4xx                           | Invalid OKF payload              | Run `sl validate`; see `validation.rs` / FR-002                                                              |

## CI traceability

Requirements live in [`functional_requirements.md`](../functional_requirements.md),
claimable work maps them in [`PLAN.md`](../../PLAN.md), phased delivery and
organization controls live in [`WBS.md`](WBS.md), and audit acceptance gaps live
in [`GAP_QA_MATRIX.md`](GAP_QA_MATRIX.md). The machine-readable SSOT is
[`TRACEABILITY.json`](TRACEABILITY.json).

Agents changing an FR, PLAN task, WBS package, or cluster status must update the
affected in-document status and `TRACEABILITY.json` in the same change. Run:

```powershell
pwsh ./docs/ops/traceability_lint.ps1
```

The dedicated CI `traceability` job runs this command and fails when the schema
is missing, an FR is absent from JSON, FR catalog and JSON statuses disagree, or
any tracked status is outside `done|partial|todo|blocked|na`. Acceptance
evidence belongs in the linked tests and paths; record intentional gaps in the
matrix instead of silently dropping coverage.

### Coverage ratchet

The blocking CI job runs `cargo llvm-cov --all-features --fail-under-lines 85`,
which is the DESIGN line-coverage target. The latest successful `main` baseline
before the T-038 increment (commit `8733051`) was **98.00% lines**; the portable
default-feature baseline was **98.17% lines**. The gate remains at 85% because it
already matches the DESIGN target; future increments should add branch-relevant
tests and must not lower this floor. The per-module qgate remains non-blocking
until each module reaches 85%.

## Related

- [`runtime-facade.md`](runtime-facade.md) — `SL_RUNTIME` matrix, PhenoCompose/nvms, Podman/WSL/Apple Container
- [`observability.md`](observability.md) — SLO stubs, RED map, `/healthz` vs `/readyz`, game-day cadence, OTel/#65, [W3C ETL sidecar](observability.md#w3c-etl-sidecar)
- [`alerts.md`](alerts.md) — PromQL, routing evidence, rule promotion status
- [`WBS.md`](WBS.md) — phased project and organization work packages
- [`GAP_QA_MATRIX.md`](GAP_QA_MATRIX.md) — current audit and acceptance gaps
- [`TRACEABILITY.json`](TRACEABILITY.json) — machine-readable status SSOT
- [`../functional_requirements.md`](../functional_requirements.md) — FR-014
- [`../adr/0001-desktop-companion-scope.md`](../adr/0001-desktop-companion-scope.md) — no tray companion
- [`../../AGENTS.md`](../../AGENTS.md) — agent build/test norms
